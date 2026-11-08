
import subprocess
from hitl import approve_command
from langchain_core.tools import tool
from langchain_tavily import TavilySearch
from utils import BLOCKED_MESSAGE, is_blocked
from utils import ensure_browser, get_interactive_elements

tavily = TavilySearch(max_results = 2)

#google search
@tool
def google_search(query: str):
    """This tool is used to do the google search"""
    print("\n*************Google Search*************")

    result = tavily.invoke(query)
    return result

#run_terminal
@tool
def run_terminal(command: str) -> str:
    """Execute a shell command on Ubuntu and return its output."""
    # Safety check 1: never even ask the user about a blocked command.
    if is_blocked(command):
        return BLOCKED_MESSAGE.format(command=command)


    approved_command = approve_command(command)

    if not approved_command:
        return "The user rejected this command, so it was not run."

    # Safety check 2: the user may have edited it into a blocked command.
    # Say the user made the edit, otherwise the LLM gets confused and answers from old messages.
    if is_blocked(approved_command):
        return (
            f"Your command `{command}` was NOT run, because the user edited it into `{approved_command}`. "
            + BLOCKED_MESSAGE.format(command=approved_command)
        )

    # If the user edited the command, tell the LLM clearly
    note = ""
    if approved_command != command:
        note = (
            f"NOTE: The user edited your command from `{command}` to `{approved_command}`. "
            f"The output below is from `{approved_command}`. Do not run `{command}` again.\n\n"
        )
    command = approved_command

    print(f"\n*************Terminal: {command}*************")

    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30,
        )

        return (
            note +
            f"COMMAND RUN: {command}\n"
            f"STDOUT:\n{result.stdout}\n"
            f"STDERR:\n{result.stderr}\n"
            f"EXIT CODE: {result.returncode}"
        )

    except subprocess.TimeoutExpired:
        return "Error: Command timed out after 30 seconds."


# Browser Tools

@tool
async def browser_open(url: str) -> str:
    """Open a URL in the browser."""
    page = None
    try:
        page = await ensure_browser()

        # 'google.com' -> 'https://google.com'
        if "://" not in url:
            url = "https://" + url

        await page.goto(url, wait_until="domcontentloaded")

        return f"Opened: {page.url}\nTitle: {await page.title()}"

    except Exception as e:
        # A failed load leaves Chrome's error page busy, so close the tab.
        # ensure_browser() will open a fresh one next time.
        if page is not None:
            await page.close()
        return f"Error opening {url}: {e}"


@tool
async def browser_get_elements() -> str:
    """Get the clickable/typeable elements (links, buttons, inputs) on the current webpage, with their IDs.
    This does NOT show the page's text (like prices or descriptions). Use browser_read for that.
    Call this again after any click or page change, because the element IDs can change."""
    try:
        await ensure_browser()

        # Only the first 150 elements, so big pages don't flood the model
        elements = (await get_interactive_elements().all())[:150]

        result = []

        for i, element in enumerate(elements, start=1):
            tag = (await element.evaluate("(el) => el.tagName")).lower()
            text = (await element.inner_text()).strip()
            placeholder = await element.get_attribute("placeholder")
            aria_label = await element.get_attribute("aria-label")

            description = text or placeholder or aria_label or "(no label)"
            description = description.replace("\n", " ")[:80]

            result.append(f"[{i}] {tag}: {description}")

        return "\n".join(result) if result else "No interactive elements found."

    except Exception as e:
        return f"Error getting elements: {e}"


@tool
async def browser_click(element_id: int) -> str:
    """Click an interactive element by its ID."""
    try:
        page = await ensure_browser()

        elements = await get_interactive_elements().all()

        if not 1 <= element_id <= len(elements):
            return f"Invalid element ID: {element_id}"

        await elements[element_id - 1].click()
        await page.wait_for_load_state("domcontentloaded")

        # Tell the agent where it is now, so it knows if the page changed
        return f"Clicked element {element_id}\nNow on: {page.url}\nTitle: {await page.title()}"

    except Exception as e:
        return f"Error clicking element {element_id}: {e}"


@tool
async def browser_type(element_id: int, text: str) -> str:
    """Type text into an input or textarea."""
    try:
        await ensure_browser()

        elements = await get_interactive_elements().all()

        if not 1 <= element_id <= len(elements):
            return f"Invalid element ID: {element_id}"

        await elements[element_id - 1].fill(text)

        return f"Typed text into element {element_id}"

    except Exception as e:
        return f"Error typing into element {element_id}: {e}"


@tool
async def browser_press(element_id: int, key: str) -> str:
    """Press a keyboard key on an interactive element."""
    try:
        page = await ensure_browser()

        elements = await get_interactive_elements().all()

        if not 1 <= element_id <= len(elements):
            return f"Invalid element ID: {element_id}"

        await elements[element_id - 1].press(key)
        await page.wait_for_load_state("domcontentloaded")

        return f"Pressed {key} on element {element_id}\nNow on: {page.url}\nTitle: {await page.title()}"

    except Exception as e:
        return f"Error pressing {key} on element {element_id}: {e}"


@tool
async def browser_read() -> str:
    """Read the visible text of the current webpage (titles, prices, articles, results).
    Use this to find the information needed to answer the user."""
    try:
        page = await ensure_browser()

        text = await page.locator("body").inner_text()

        return text[:10000]

    except Exception as e:
        return f"Error reading page: {e}"

# Tools list
tools = [
    google_search,
    run_terminal,
    browser_open,
    browser_get_elements,
    browser_click,
    browser_type,
    browser_press,
    browser_read,
]

