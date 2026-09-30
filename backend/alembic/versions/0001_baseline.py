"""Baseline: lock down the app schema and add shared database helpers.

The ``app`` schema itself is created by ``alembic/env.py`` (Alembic's version
table lives in it). This migration:

* removes default access to the schema for PUBLIC and, on Supabase, for the
  ``anon`` / ``authenticated`` roles used by the public data API;
* adds ``app.set_updated_at()``, a trigger function future tables use to keep
  ``updated_at`` correct even when rows are edited outside the API
  (e.g. in the Supabase Table Editor).

Revision ID: 0001
Revises:
Create Date: 2026-09-30
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("REVOKE ALL ON SCHEMA app FROM PUBLIC")
    op.execute(
        """
        DO $$
        DECLARE
            role_name text;
        BEGIN
            FOREACH role_name IN ARRAY ARRAY['anon', 'authenticated'] LOOP
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = role_name) THEN
                    EXECUTE format('REVOKE ALL ON SCHEMA app FROM %I', role_name);
                END IF;
            END LOOP;
        END
        $$;
        """
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION app.set_updated_at()
        RETURNS trigger
        LANGUAGE plpgsql
        SET search_path = ''
        AS $$
        BEGIN
            NEW.updated_at = pg_catalog.now();
            RETURN NEW;
        END;
        $$;
        """
    )


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS app.set_updated_at()")
