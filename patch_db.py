with open("app/core/database.py", "rb") as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if b"from ..modules.personalities.models import Personality" in line:
        spaces = line[:len(line) - len(line.lstrip())]
        new_line = spaces + b"from ..modules.connectors.google.models import GmailMessage, GmailSyncState\n"
        lines.insert(i + 1, new_line)
        break

with open("app/core/database.py", "wb") as f:
    f.writelines(lines)
