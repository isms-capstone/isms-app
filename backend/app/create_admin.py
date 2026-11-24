"""Compatibility entry point: create the initial Admin through the regular seeder.

Run migrations first (python -m alembic upgrade head). Outside local use, set
ISMS_ADMIN_PASSWORD. Existing accounts are never modified.
"""
from app.db.seed import seed_data

if __name__ == "__main__":
    seed_data()
