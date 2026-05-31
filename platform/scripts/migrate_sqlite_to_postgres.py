#!/usr/bin/env python3
"""
SQLite to PostgreSQL Migration Script

This script migrates data from the existing SQLite database to PostgreSQL.
It preserves all test definitions, test runs, and related data.

Usage:
    python migrate_sqlite_to_postgres.py [--sqlite-path PATH] [--postgres-url URL]

Environment Variables:
    POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD
"""

import argparse
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import psycopg2
from psycopg2.extras import execute_values


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Migrate data from SQLite to PostgreSQL"
    )
    parser.add_argument(
        "--sqlite-path",
        default="claude_code_tests.db",
        help="Path to SQLite database file (default: claude_code_tests.db)"
    )
    parser.add_argument(
        "--postgres-host",
        default="localhost",
        help="PostgreSQL host (default: localhost)"
    )
    parser.add_argument(
        "--postgres-port",
        type=int,
        default=5432,
        help="PostgreSQL port (default: 5432)"
    )
    parser.add_argument(
        "--postgres-db",
        default="claude_code_tests",
        help="PostgreSQL database name (default: claude_code_tests)"
    )
    parser.add_argument(
        "--postgres-user",
        default="cc_test_user",
        help="PostgreSQL user (default: cc_test_user)"
    )
    parser.add_argument(
        "--postgres-password",
        help="PostgreSQL password (required or set POSTGRES_PASSWORD env var)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be migrated without actually migrating"
    )

    return parser.parse_args()


def get_postgres_password(args):
    """Get PostgreSQL password from args or environment."""
    if args.postgres_password:
        return args.postgres_password

    import os
    password = os.environ.get("POSTGRES_PASSWORD")
    if not password:
        print("Error: PostgreSQL password required via --postgres-password or POSTGRES_PASSWORD environment variable")
        sys.exit(1)

    return password


def connect_sqlite(db_path: str) -> sqlite3.Connection:
    """Connect to SQLite database."""
    if not Path(db_path).exists():
        print(f"Error: SQLite database not found at {db_path}")
        sys.exit(1)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def connect_postgres(args) -> psycopg2.extensions.connection:
    """Connect to PostgreSQL database."""
    password = get_postgres_password(args)

    try:
        conn = psycopg2.connect(
            host=args.postgres_host,
            port=args.postgres_port,
            database=args.postgres_db,
            user=args.postgres_user,
            password=password
        )
        conn.autocommit = False
        return conn
    except psycopg2.OperationalError as e:
        print(f"Error: Could not connect to PostgreSQL: {e}")
        sys.exit(1)


def migrate_test_definitions(
    sqlite_conn: sqlite3.Connection,
    postgres_conn: psycopg2.extensions.connection,
    dry_run: bool = False
) -> int:
    """Migrate test_definitions table."""
    print("\n=== Migrating test_definitions ===")

    sqlite_cur = sqlite_conn.cursor()
    postgres_cur = postgres_conn.cursor()

    # Check if SQLite has test_definitions table
    sqlite_cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='test_definitions'"
    )
    if not sqlite_cur.fetchone():
        print("No test_definitions table found in SQLite, skipping...")
        return 0

    sqlite_cur.execute("SELECT * FROM test_definitions")
    rows = sqlite_cur.fetchall()

    if not rows:
        print("No test definitions to migrate")
        return 0

    print(f"Found {len(rows)} test definitions")

    if dry_run:
        for row in rows:
            print(f"  - {row['test_id']}: {row['name']}")
        return len(rows)

    # Prepare data for insertion
    data = []
    for row in rows:
        data.append((
            row['name'],
            row['description'],
            row['test_id'],
            row.get('url'),
            row.get('environment') or '{}',
            row.get('tags') or '[]',
            row.get('created_by') or 'system',
            row.get('version') or 1,
            row.get('is_active', True)
        ))

    # Insert data
    insert_query = """
        INSERT INTO test_definitions (
            name, description, test_id, url, environment, tags,
            created_by, version, is_active
        ) VALUES %s
        ON CONFLICT (test_id) DO NOTHING
    """

    execute_values(postgres_cur, insert_query, data)
    postgres_conn.commit()

    print(f"Migrated {postgres_cur.rowcount} test definitions")
    return postgres_cur.rowcount


def migrate_test_steps(
    sqlite_conn: sqlite3.Connection,
    postgres_conn: psycopg2.extensions.connection,
    dry_run: bool = False
) -> int:
    """Migrate test_steps table."""
    print("\n=== Migrating test_steps ===")

    sqlite_cur = sqlite_conn.cursor()
    postgres_cur = postgres_conn.cursor()

    # Check if table exists
    sqlite_cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='test_steps'"
    )
    if not sqlite_cur.fetchone():
        print("No test_steps table found in SQLite, skipping...")
        return 0

    # First, get test_id to id mapping
    postgres_cur.execute("SELECT test_id, id FROM test_definitions")
    test_id_map = {row[0]: row[1] for row in postgres_cur.fetchall()}

    sqlite_cur.execute("SELECT * FROM test_steps")
    rows = sqlite_cur.fetchall()

    if not rows:
        print("No test steps to migrate")
        return 0

    print(f"Found {len(rows)} test steps")

    if dry_run:
        for row in rows[:5]:  # Show first 5
            print(f"  - Test {row['test_definition_id']}, step {row['step_number']}")
        return len(rows)

    # Prepare data
    data = []
    for row in rows:
        test_id = row.get('test_definition_id')
        definition_id = test_id_map.get(test_id)

        if not definition_id:
            print(f"Warning: No test definition found for test_id={test_id}, skipping step")
            continue

        data.append((
            definition_id,
            row['step_number'],
            row['description'],
            row['type'],
            row['params'],
            row.get('expected_result')
        ))

    # Insert data
    insert_query = """
        INSERT INTO test_steps (
            test_definition_id, step_number, description, type, params, expected_result
        ) VALUES %s
    """

    execute_values(postgres_cur, insert_query, data)
    postgres_conn.commit()

    print(f"Migrated {postgres_cur.rowcount} test steps")
    return postgres_cur.rowcount


def migrate_test_runs(
    sqlite_conn: sqlite3.Connection,
    postgres_conn: psycopg2.extensions.connection,
    dry_run: bool = False
) -> int:
    """Migrate test_runs table."""
    print("\n=== Migrating test_runs ===")

    sqlite_cur = sqlite_conn.cursor()
    postgres_cur = postgres_conn.cursor()

    # Check if table exists
    sqlite_cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='test_runs'"
    )
    if not sqlite_cur.fetchone():
        print("No test_runs table found in SQLite, skipping...")
        return 0

    # Get test_id to id mapping
    postgres_cur.execute("SELECT test_id, id FROM test_definitions")
    test_id_map = {row[0]: row[1] for row in postgres_cur.fetchall()}

    sqlite_cur.execute("SELECT * FROM test_runs")
    rows = sqlite_cur.fetchall()

    if not rows:
        print("No test runs to migrate")
        return 0

    print(f"Found {len(rows)} test runs")

    if dry_run:
        for row in rows[:5]:  # Show first 5
            print(f"  - Run {row['run_id']}: {row['status']}")
        return len(rows)

    # Prepare data
    data = []
    for row in rows:
        test_id = row.get('test_definition_id')
        definition_id = test_id_map.get(test_id) if test_id else None

        data.append((
            row['run_id'],
            definition_id,
            row['start_time'],
            row.get('end_time'),
            row.get('total_tests') or 0,
            row.get('passed') or 0,
            row.get('failed') or 0,
            row.get('skipped') or 0,
            row.get('total_duration') or 0,
            row.get('status') or 'pending',
            row.get('environment'),
            row.get('triggered_by')
        ))

    # Insert data
    insert_query = """
        INSERT INTO test_runs (
            run_id, test_definition_id, start_time, end_time,
            total_tests, passed, failed, skipped, total_duration,
            status, environment, triggered_by
        ) VALUES %s
        ON CONFLICT (run_id) DO NOTHING
    """

    execute_values(postgres_cur, insert_query, data)
    postgres_conn.commit()

    print(f"Migrated {postgres_cur.rowcount} test runs")
    return postgres_cur.rowcount


def migrate_test_cases(
    sqlite_conn: sqlite3.Connection,
    postgres_conn: psycopg2.extensions.connection,
    dry_run: bool = False
) -> int:
    """Migrate test_cases table."""
    print("\n=== Migrating test_cases ===")

    sqlite_cur = sqlite_conn.cursor()
    postgres_cur = postgres_conn.cursor()

    # Check if table exists
    sqlite_cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='test_cases'"
    )
    if not sqlite_cur.fetchone():
        print("No test_cases table found in SQLite, skipping...")
        return 0

    # Get run_id and test_id mappings
    postgres_cur.execute("SELECT run_id, id FROM test_runs")
    run_id_map = {row[0]: row[1] for row in postgres_cur.fetchall()}

    postgres_cur.execute("SELECT test_id, id FROM test_definitions")
    test_id_map = {row[0]: row[1] for row in postgres_cur.fetchall()}

    sqlite_cur.execute("SELECT * FROM test_cases")
    rows = sqlite_cur.fetchall()

    if not rows:
        print("No test cases to migrate")
        return 0

    print(f"Found {len(rows)} test cases")

    if dry_run:
        for row in rows[:5]:  # Show first 5
            print(f"  - Case {row['test_id']}: {row['status']}")
        return len(rows)

    # Prepare data
    data = []
    for row in rows:
        run_id = row.get('run_id')
        test_id = row.get('test_definition_id')

        run_internal_id = run_id_map.get(run_id) if run_id else None
        definition_id = test_id_map.get(test_id) if test_id else None

        if not run_internal_id:
            print(f"Warning: No test run found for run_id={run_id}, skipping case")
            continue

        data.append((
            run_internal_id,
            definition_id,
            row['test_id'],
            row.get('description'),
            row['status'],
            row['duration'],
            row['start_time'],
            row['end_time'],
            row.get('error_message'),
            row.get('screenshot_path')
        ))

    # Insert data
    insert_query = """
        INSERT INTO test_cases (
            run_id, test_definition_id, test_id, description, status,
            duration, start_time, end_time, error_message, screenshot_path
        ) VALUES %s
    """

    execute_values(postgres_cur, insert_query, data)
    postgres_conn.commit()

    print(f"Migrated {postgres_cur.rowcount} test cases")
    return postgres_cur.rowcount


def main():
    """Main migration function."""
    args = parse_args()

    print("=" * 60)
    print("SQLite to PostgreSQL Migration")
    print("=" * 60)

    # Connect to databases
    print(f"\nConnecting to SQLite: {args.sqlite_path}")
    sqlite_conn = connect_sqlite(args.sqlite_path)

    if not args.dry_run:
        print(f"Connecting to PostgreSQL: {args.postgres_host}:{args.postgres_port}/{args.postgres_db}")
        postgres_conn = connect_postgres(args)
    else:
        print("DRY RUN MODE - No data will be migrated")
        postgres_conn = None

    try:
        # Migrate data
        total = 0
        total += migrate_test_definitions(sqlite_conn, postgres_conn, args.dry_run)
        total += migrate_test_steps(sqlite_conn, postgres_conn, args.dry_run)
        total += migrate_test_runs(sqlite_conn, postgres_conn, args.dry_run)
        total += migrate_test_cases(sqlite_conn, postgres_conn, args.dry_run)

        print("\n" + "=" * 60)
        print(f"Migration complete! Total records: {total}")
        print("=" * 60)

        if args.dry_run:
            print("\nThis was a dry run. Re-run without --dry-run to actually migrate data.")

    except Exception as e:
        print(f"\nError during migration: {e}")
        if postgres_conn:
            postgres_conn.rollback()
        sys.exit(1)

    finally:
        sqlite_conn.close()
        if postgres_conn:
            postgres_conn.close()


if __name__ == "__main__":
    main()
