"""Tools for the researcher agent and the verifier agent.
Search = find pages (titles, URLs, snippets). Extract = read one page fully."""

import asyncio

from dotenv import load_dotenv
from langchain_core.tools import tool
from langchain_tavily import TavilyExtract, TavilySearch

from utils import EXCLUDED_DOMAINS, MAX_PAGE_CHARS, MAX_SNIPPET_CHARS, PAGES, READING, clean_url, get_domain, shorten

load_dotenv(override=True)   # TAVILY_API_KEY must be loaded before the Tavily clients are created

tavily_search = TavilySearch(max_results=5, exclude_domains=EXCLUDED_DOMAINS)   # no LinkedIn, YouTube, job sites...
tavily_extract = TavilyExtract()


def format_results(response):
    """Turn Tavily's search response into short text the LLM can read."""
    if not isinstance(response, dict) or not response.get("results"):
        return f"No results. {response}"

    lines = []
    for i, r in enumerate(response["results"], start=1):
        lines.append(
            f"{i}. {r.get('title', '')}\n"
            f"   URL: {r.get('url', '')}\n"
            f"   Snippet: {shorten(r.get('content', ''), MAX_SNIPPET_CHARS)}"
        )
    return "\n".join(lines)


# ---------------- Researcher tools ----------------

@tool
async def web_search(query: str) -> str:
    """Search the whole web. Returns titles, URLs and short snippets (NOT the full page).
    Use extract_page to read a page before using it as evidence."""
    print(f"\n*************Search: {query}*************")
    response = await tavily_search.ainvoke({"query": query})
    return format_results(response)


@tool
async def extract_page(url: str) -> str:
    """Read the full text of ONE web page (clean text). Use it on the best URLs from a search."""
    url = clean_url(url)

    # Already read by any agent? Then reuse it: no second Tavily call, no extra cost.
    if url in PAGES:
        print(f"\n*************Extract (already read): {url}*************")
        return f"PAGE (already read): {url}\n\n{PAGES[url]}"

    # The LLM sometimes asks for the same page several times AT ONCE.
    # Only the first call goes to Tavily; the others wait for that same call.
    if url not in READING:
        print(f"\n*************Extract: {url}*************")
        READING[url] = asyncio.ensure_future(tavily_extract.ainvoke({"urls": [url]}))
    response = await READING[url]

    results = response.get("results", []) if isinstance(response, dict) else []
    if not results:
        return f"Could not read {url}. Try another URL."

    text = shorten(results[0].get("raw_content", ""), MAX_PAGE_CHARS)
    PAGES[url] = text                                            # our code remembers: this page was really read
    PAGES[clean_url(results[0].get("url") or url)] = text        # Tavily may return the final URL after a redirect
    return f"PAGE: {url}\n\n{text}"


# ---------------- Verifier tools ----------------

@tool
async def official_search(query: str, domain: str) -> str:
    """Search ONLY inside one company's official website.
    domain example: "salesforce.com" (no https://, no www)."""
    if get_domain(domain) in ("", "none"):   # no official website: do not waste a Tavily call
        return "No official website for this finding. Mark it NOT CHECKED."

    print(f"\n*************Official search on {domain}: {query}*************")
    response = await tavily_search.ainvoke({"query": query, "include_domains": [domain]})
    return format_results(response)


researcher_tools = [web_search, extract_page]
verifier_tools = [official_search, extract_page]
