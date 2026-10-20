"""List users, or reset one user's password.

Run from the backend folder, with the virtual environment active:
  python -m app.reset_password              shows every username (no passwords)
  python -m app.reset_password USERNAME     asks for a new password and saves it

Passwords are stored as hashes, so an old password can never be shown, only replaced.
"""
import getpass
import sys

from sqlalchemy import select

from .db import SessionLocal
from .models import User
from .security import hash_password, password_ok_length

MIN_LENGTH = 10


def main() -> int:
    db = SessionLocal()
    users = db.scalars(select(User).order_by(User.id)).all()
    if len(sys.argv) == 1:
        if not users:
            print("No users yet. Run: python -m app.seed")
            return 1
        print(f"{'username':<20} {'role':<11} venue_id")
        for u in users:
            print(f"{u.username:<20} {u.role:<11} {u.venue_id if u.venue_id is not None else '-'}")
        print("\nTo reset one: python -m app.reset_password USERNAME")
        return 0
    if len(sys.argv) != 2:
        print("Usage: python -m app.reset_password [USERNAME]")
        return 2

    username = sys.argv[1].strip().lower()
    user = next((u for u in users if u.username == username), None)
    if user is None:
        print(f"No user called '{username}'. Run it with no name to see the list.")
        return 1
    pw = getpass.getpass(f"New password for {username} (at least {MIN_LENGTH} characters): ")
    if len(pw) < MIN_LENGTH or not password_ok_length(pw):
        print(f"Too short, or longer than 72 bytes. Use {MIN_LENGTH} or more characters. Nothing changed.")
        return 1
    if getpass.getpass("Type it again: ") != pw:
        print("The two passwords did not match. Nothing changed.")
        return 1
    user.password_hash = hash_password(pw)
    db.commit()
    print(f"Password reset for {username}. You can log in with it now.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
