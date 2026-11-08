import os
import re

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