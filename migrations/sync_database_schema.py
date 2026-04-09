"""
Comprehensive database schema sync migration.

Inspects the live MySQL database against all defined SQLAlchemy models and:
  - Creates any missing tables via create_all()
  - Adds any missing columns via ALTER TABLE
  - Sets sensible defaults on existing rows for newly added columns
  - Skips columns / tables that already exist (idempotent)

Usage:
    python migrations/sync_database_schema.py

Exit codes:
    0 — completed (with or without warnings)
    1 — fatal error prevented the migration from finishing
"""

import sys
import os

# Ensure the project root is on the path so all imports resolve correctly.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask
from sqlalchemy import inspect, text
from configDB.config import db, Config

# ── Import every model so SQLAlchemy's metadata is fully populated ────────────
from busnisess_layer.models import (
    Clinics,
    Section,
    Doctor,
    Process,
    Patient,
    Visit,
    Procedure,
    Percentages,
    Payments,
    Invoice,
    Bills,
    Reception,
    Featurs,
    Featursplans,
    Plan,
    ConsultationTime,
)


# ─────────────────────────────────────────────────────────────────────────────
# Column definitions
#
# Each entry is a tuple:
#   (table_name, column_name, column_definition, default_update_sql_or_None)
#
# The optional fourth element is a raw SQL UPDATE statement that sets a
# sensible default for *existing* rows after the column is added.
# ─────────────────────────────────────────────────────────────────────────────

COLUMNS_TO_ADD = [

    # ── doctor ────────────────────────────────────────────────────────────────
    (
        "doctor", "average_consultation_time",
        "FLOAT DEFAULT 0",
        "UPDATE doctor SET average_consultation_time = 0 WHERE average_consultation_time IS NULL",
    ),
    (
        "doctor", "total_consultation_seconds",
        "INT DEFAULT 0",
        "UPDATE doctor SET total_consultation_seconds = 0 WHERE total_consultation_seconds IS NULL",
    ),
    (
        "doctor", "consultation_count",
        "INT DEFAULT 0",
        "UPDATE doctor SET consultation_count = 0 WHERE consultation_count IS NULL",
    ),
    (
        "doctor", "last_button_click_timestamp",
        "DATETIME NULL",
        None,
    ),
    (
        "doctor", "last_update_time",
        "DATETIME NULL",
        None,
    ),

    # ── patient ───────────────────────────────────────────────────────────────
    (
        "patient", "normalized_name",
        "VARCHAR(255) NULL",
        None,
    ),
    (
        "patient", "clinics_visited",
        "TEXT NULL",
        None,
    ),
    (
        "patient", "process_id",
        "INT NULL",
        None,
    ),
    (
        "patient", "date_visit",
        "DATE NULL",
        None,
    ),

    # ── visit ─────────────────────────────────────────────────────────────────
    (
        "visit", "normalized_name",
        "VARCHAR(255) NULL",
        None,
    ),
    (
        "visit", "date_visit",
        "DATE NULL",
        None,
    ),
    (
        "visit", "visit_status",
        "VARCHAR(50) DEFAULT 'مؤكد'",
        "UPDATE visit SET visit_status = 'مؤكد' WHERE visit_status IS NULL",
    ),
    (
        "visit", "process_id",
        "INT NULL",
        None,
    ),
    (
        "visit", "percentage",
        "INT DEFAULT 0",
        "UPDATE visit SET percentage = 0 WHERE percentage IS NULL",
    ),
    (
        "visit", "queue_position",
        "INT NULL",
        None,
    ),
    (
        "visit", "actual_start_time",
        "DATETIME NULL",
        None,
    ),
    (
        "visit", "actual_end_time",
        "DATETIME NULL",
        None,
    ),
    (
        "visit", "queue_status",
        "VARCHAR(50) DEFAULT 'waiting'",
        "UPDATE visit SET queue_status = 'waiting' WHERE queue_status IS NULL",
    ),

    # ── procedure ─────────────────────────────────────────────────────────────
    (
        "procedure", "discount",
        "INT DEFAULT 0",
        "UPDATE `procedure` SET discount = 0 WHERE discount IS NULL",
    ),
    (
        "procedure", "final_cost",
        "INT NULL",
        None,
    ),
    (
        "procedure", "status",
        "VARCHAR(50) DEFAULT 'pending'",
        "UPDATE `procedure` SET status = 'pending' WHERE status IS NULL",
    ),

    # ── invoice ───────────────────────────────────────────────────────────────
    (
        "invoice", "discount",
        "INT DEFAULT 0",
        "UPDATE invoice SET discount = 0 WHERE discount IS NULL",
    ),
    (
        "invoice", "paid_amount",
        "INT NULL",
        None,
    ),
    (
        "invoice", "status",
        "VARCHAR(50) DEFAULT 'غير مدفوع'",
        "UPDATE invoice SET status = 'غير مدفوع' WHERE status IS NULL",
    ),

    # ── payments ──────────────────────────────────────────────────────────────
    (
        "payments", "method",
        "VARCHAR(50) DEFAULT 'كاش'",
        "UPDATE payments SET method = 'كاش' WHERE method IS NULL",
    ),
    (
        "payments", "remaining_amount",
        "INT NOT NULL DEFAULT 0",
        "UPDATE payments SET remaining_amount = 0 WHERE remaining_amount IS NULL",
    ),

    # ── bills ─────────────────────────────────────────────────────────────────
    (
        "bills", "bill_section",
        "VARCHAR(50) NULL",
        None,
    ),
    (
        "bills", "description",
        "VARCHAR(400) NULL",
        None,
    ),

    # ── clinics ───────────────────────────────────────────────────────────────
    (
        "clinics", "plan_id",
        "INT NULL",
        None,
    ),

    # ── consultation_time ─────────────────────────────────────────────────────
    (
        "consultationtime", "previous_visit_id",
        "INT NULL",
        None,
    ),
    (
        "consultationtime", "current_visit_id",
        "INT NULL",
        None,
    ),
    (
        "consultationtime", "date_recorded",
        "DATE NOT NULL DEFAULT (CURDATE())",
        None,
    ),
]


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _existing_columns(inspector, table_name: str) -> set:
    """Return the set of column names that currently exist in *table_name*."""
    try:
        return {col["name"].lower() for col in inspector.get_columns(table_name)}
    except Exception:
        return set()


def _existing_tables(inspector) -> set:
    """Return the set of table names that currently exist in the database."""
    return {t.lower() for t in inspector.get_table_names()}


def _quote_table(table_name: str) -> str:
    """Wrap a table name in back-ticks (needed for reserved words like 'procedure')."""
    return f"`{table_name}`"


# ─────────────────────────────────────────────────────────────────────────────
# App factory (mirrors the pattern used in existing migrations)
# ─────────────────────────────────────────────────────────────────────────────

def create_app() -> Flask:
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = Config.SQLALCHEMY_DATABASE_URI
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    db.init_app(app)
    return app


# ─────────────────────────────────────────────────────────────────────────────
# Main migration logic
# ─────────────────────────────────────────────────────────────────────────────

def sync_schema() -> bool:
    """
    Synchronise the live database schema with the SQLAlchemy model definitions.

    Returns True if the migration finished without fatal errors, False otherwise.
    """
    app = create_app()
    overall_success = True

    with app.app_context():

        # ── Step 1: create any missing tables ─────────────────────────────────
        print("\n" + "=" * 60)
        print("STEP 1 — Creating missing tables")
        print("=" * 60)
        try:
            db.create_all()
            print("✅ db.create_all() completed — all model tables now exist.")
        except Exception as exc:
            print(f"❌ db.create_all() failed: {exc}")
            overall_success = False
            # Continue anyway; individual ALTER TABLE statements may still work.

        # ── Step 2: add missing columns ───────────────────────────────────────
        print("\n" + "=" * 60)
        print("STEP 2 — Adding missing columns")
        print("=" * 60)

        inspector = inspect(db.engine)
        existing_tables = _existing_tables(inspector)

        # Group columns by table so we only fetch the column list once per table.
        from collections import defaultdict
        columns_by_table: dict = defaultdict(list)
        for entry in COLUMNS_TO_ADD:
            columns_by_table[entry[0]].append(entry)

        for table_name, entries in columns_by_table.items():
            print(f"\n  Table: {table_name}")

            if table_name.lower() not in existing_tables:
                print(f"    ⚠️  Table '{table_name}' does not exist — skipping column additions.")
                continue

            existing_cols = _existing_columns(inspector, table_name)

            for entry in entries:
                _, col_name, col_def, update_sql = entry
                col_lower = col_name.lower()

                if col_lower in existing_cols:
                    print(f"    ℹ️  Column '{col_name}' already exists — skipping.")
                    continue

                alter_sql = (
                    f"ALTER TABLE {_quote_table(table_name)} "
                    f"ADD COLUMN `{col_name}` {col_def}"
                )

                try:
                    db.session.execute(text(alter_sql))
                    db.session.commit()
                    print(f"    ✅ Added column '{col_name}'.")
                except Exception as exc:
                    db.session.rollback()
                    err = str(exc).lower()
                    if "duplicate column name" in err or "already exists" in err:
                        print(f"    ℹ️  Column '{col_name}' already exists (caught on execute) — skipping.")
                    else:
                        print(f"    ❌ Error adding column '{col_name}': {exc}")
                        overall_success = False
                    continue

                # Apply the default-value UPDATE for existing rows (if provided).
                if update_sql:
                    try:
                        db.session.execute(text(update_sql))
                        db.session.commit()
                        print(f"       ↳ Default values set for existing rows.")
                    except Exception as exc:
                        db.session.rollback()
                        print(f"       ⚠️  Could not set default values for '{col_name}': {exc}")
                        # Non-fatal — the column was added successfully.

        # ── Step 3: summary ───────────────────────────────────────────────────
        print("\n" + "=" * 60)
        if overall_success:
            print("✅ Migration completed successfully!")
        else:
            print("⚠️  Migration completed with some errors — review output above.")
        print("=" * 60 + "\n")

        return overall_success


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    success = sync_schema()
    sys.exit(0 if success else 1)
