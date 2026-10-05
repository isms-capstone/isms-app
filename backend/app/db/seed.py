"""Compatibility entry point for database seeding.

Use the same idempotent seeder as application startup.
"""
from app.db.session import SessionLocal
from app.db.init_db import init_db


def seed_data():
    db = SessionLocal()
    try:
        init_db(db)
        print("Seed data inserted/verified successfully.")
    finally:
        db.close()


if __name__ == "__main__":
    seed_data()
