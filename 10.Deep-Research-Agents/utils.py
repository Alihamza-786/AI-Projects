"""Our code remembers every page the agents REALLY read.
Later we compare the agents' citations and verdicts with this memory, so we never trust them blindly."""

import re
from urllib.parse import urlparse

MAX_PAGE_CHARS = 4000     # text we give the LLM from one page (keeps the prompt small)
MAX_SNIPPET_CHARS = 300   # text per search result

# Social media and job sites are never evidence. Search skips them, and the verdict check rejects them.
EXCLUDED_DOMAINS = ["linkedin.com", "youtube.com", "facebook.com", "x.com", "reddit.com", "builtin.com", "indeed.com"]

PAGES = {}                # url -> page text, for every page extract_page really read during this question
READING = {}              # url -> Tavily call running right now, so parallel calls for the same page share it
FINDINGS = []             # every researcher reply, exactly as written. Our code gives these to the verifier.


def reset_sources():
    """Start a new question with an empty memory."""
    PAGES.clear()
    READING.clear()
    FINDINGS.clear()


def clean_url(url):
    """Make URLs comparable: no trailing slash or punctuation."""
    return url.strip().rstrip(".,;:)]>*'\"").rstrip("/")


def get_domain(url_or_domain):
    """'https://www.cloud.google.com/x' -> 'cloud.google.com', 'www.Google.com' -> 'google.com'"""
    text = url_or_domain.strip().lower()
    host = urlparse(text).hostname if "://" in text else text.split("/")[0]
    return (host or "").removeprefix("www.")


def on_domain(host, domain):
    """True if host is the domain itself or one of its subdomains (cloud.google.com is on google.com)."""
    return host == domain or host.endswith("." + domain)


def shorten(text, max_chars):
    text = (text or "").strip()
    if len(text) > max_chars:
        return text[:max_chars] + " ...(cut)"
    return text


def find_urls(text):
    """Find every http(s) URL in a piece of text."""
    return {clean_url(u) for u in re.findall(r"https?://[^\s)\]>|\"']+", text or "")}


def check_citations(reply):
    """Compare the URLs in an agent's reply with the pages it really read.
    Returns a short report that we append to the reply."""
    not_read = sorted(find_urls(reply) - PAGES.keys())

    report = "CITATION CHECK (done by our code, not by the LLM):\n"
    report += f"Pages actually read so far: {len(PAGES)}\n"
    if not_read:
        report += "⚠ NOT READ (possible hallucination, do not use these as evidence):\n"
        report += "\n".join(f"- {u}" for u in not_read)
    else:
        report += "All cited URLs were really read. ✓"
    return report


def verdict_problem(domain, url):
    """Why a VERIFIED verdict is not allowed, or None if it is fine."""
    url = clean_url(url)
    domain = get_domain(domain)
    host = get_domain(url)

    if domain in ("", "none"):
        return "no official website was named"
    if url not in PAGES:
        return "the official page was never read"
    if any(on_domain(host, bad) for bad in EXCLUDED_DOMAINS):
        return f"{host} is a social media or job site, not an official source"
    if not on_domain(host, domain):
        return f"{host} is not the official website ({domain})"
    return None


def official_domains():
    """About -> official domain, as the RESEARCHERS wrote it in their findings.
    The verifier may not change it (for example to a blog's domain) to make a claim pass."""
    known = {}
    for block in "\n\n".join(FINDINGS).split("Finding:"):
        about = re.search(r"About:\s*(.+)", block)
        site = re.search(r"Official website:\s*(.+)", block)
        if about and site and get_domain(site.group(1)) not in ("", "none"):
            known[about.group(1).strip().lower()] = get_domain(site.group(1))
    return known


def check_verdicts(reply):
    """Check every VERIFIED line of the verifier:
    About | official domain | short claim | VERIFIED | official URL | reason
    LLMs sometimes skip a column, so we do not trust positions: we look for the VERIFIED cell,
    take the domain from the 2nd cell and the first URL after VERIFIED.
    A verdict that fails the check is changed to NOT VERIFIED.
    Returns (corrected reply, report)."""
    lines, changes = [], []
    totals = {"VERIFIED": 0, "NOT VERIFIED": 0, "NOT CHECKED": 0}
    known_domains = official_domains()

    for line in reply.splitlines():
        parts = [p.strip() for p in line.strip().strip("|").split("|")]
        cells = [p.strip("* ").upper() for p in parts]

        if "VERIFIED" in cells and len(parts) >= 3:
            at = cells.index("VERIFIED")
            domain = parts[1] if at > 1 else "none"
            domain = known_domains.get(parts[0].lower(), domain)   # the researcher's domain wins
            url = next((p for p in parts[at + 1:] if p.startswith("http")), "")
            problem = verdict_problem(domain, url)
            if problem:
                parts[at] = "NOT VERIFIED"
                cells[at] = "NOT VERIFIED"
                line = " | ".join(parts)
                changes.append(f"- {shorten(parts[0], 80)}: changed to NOT VERIFIED, because {problem}")

        for status in totals:
            totals[status] += status in cells
        lines.append(line)

    report = "VERDICT CHECK (done by our code, not by the LLM):\n"
    report += "\n".join(changes) + "\n" if changes else "All VERIFIED verdicts passed the check. ✓\n"
    report += (
        f"TOTALS: {totals['VERIFIED']} VERIFIED, {totals['NOT VERIFIED']} NOT VERIFIED, "
        f"{totals['NOT CHECKED']} NOT CHECKED. Only VERIFIED findings may get ✅."
    )
    return "\n".join(lines), report
