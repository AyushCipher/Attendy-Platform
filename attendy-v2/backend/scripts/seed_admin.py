"""Create the first admin user.

Interactive:      python -m scripts.seed_admin
Non-interactive:  python -m scripts.seed_admin --email a@b.com --name "Admin" --password secret
"""
import argparse
import asyncio
import getpass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select  # noqa: E402

from app.core.security import hash_password  # noqa: E402
from app.db.base import async_session_factory  # noqa: E402
from app.db.models.admin import Admin  # noqa: E402


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--email")
    parser.add_argument("--name")
    parser.add_argument("--password")
    args = parser.parse_args()

    email = args.email or input("Admin email: ").strip()
    full_name = args.name or input("Full name: ").strip()
    password = args.password or getpass.getpass("Password: ")

    async with async_session_factory() as db:
        existing = await db.scalar(select(Admin).where(Admin.email == email))
        if existing:
            print(f"Admin with email {email} already exists.")
            return

        admin = Admin(email=email, full_name=full_name, password_hash=hash_password(password))
        db.add(admin)
        await db.commit()
        print(f"Created admin {email}.")


if __name__ == "__main__":
    asyncio.run(main())
