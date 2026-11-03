"""Admin tool. Usage: python manage_users.py add NAME | remove NAME | list"""
import getpass
import sys
from core import auth

cmd = sys.argv[1] if len(sys.argv) > 1 else ""
if cmd == "add" and len(sys.argv) == 3:
    pw = getpass.getpass("Password: ")
    if len(pw) < 8:
        sys.exit("Use at least 8 characters.")
    auth.add_user(sys.argv[2], pw)
    print("Saved.")
elif cmd == "remove" and len(sys.argv) == 3:
    auth.remove_user(sys.argv[2]); print("Removed.")
elif cmd == "list":
    print("\n".join(auth.list_users()) or "(no users)")
else:
    sys.exit(__doc__)
