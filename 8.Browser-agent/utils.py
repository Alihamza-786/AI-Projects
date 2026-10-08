import os
import re
from playwright.async_api import async_playwright

# Programs the agent is never allowed to run: admin rights, deleting, or shutting down.
BLOCKED_COMMANDS = {
    "sudo", "su",                                   # admin / root rights
    "rm", "rmdir", "shred", "unlink",               # deleting files
    "dd", "mkfs", "fdisk",                          # wiping disks
    "shutdown", "reboot", "poweroff", "halt",       # turning the machine off
}

BLOCKED_MESSAGE = (
    "BLOCKED: `{command}` was not run. Commands that need admin rights (sudo) or delete files "
    "are not allowed. Do not try again or look for a workaround. Tell the user to run it "
    "themselves in their own terminal if they really want to."
)

def is_blocked(command):
    """True if any program in the command is blocked, e.g. 'sudo apt update' or 'cd x && rm -rf y'."""
    # Split on spaces and shell symbols so 'ls; rm a.txt' gives ['ls', 'rm', 'a.txt']
    for word in re.split(r"[\s;&|()`]+", command):
        program = os.path.basename(word)   # '/bin/rm' -> 'rm'
        program = program.split(".")[0]    # 'mkfs.ext4' -> 'mkfs'
        if program in BLOCKED_COMMANDS:
            return True
    return False




# Browser Agent Helper Functions
playwright = None
browser = None
page = None


async def ensure_browser():
    """Start the browser once and reuse it. Returns the current page."""
    global playwright, browser, page

    # Start the browser only if it is not running
    if browser is None or not browser.is_connected():
        playwright = await async_playwright().start()
        # channel="chrome" uses the installed Google Chrome instead of Playwright's own Chromium
        browser = await playwright.chromium.launch(headless=False, channel="chrome")
        page = None

    # Open a new tab if there is no page or the user closed it
    if page is None or page.is_closed():
        page = await browser.new_page()

    return page


def get_interactive_elements():
    return page.locator(
        "input:visible, button:visible, textarea:visible, "
        "select:visible, a:visible"
    )