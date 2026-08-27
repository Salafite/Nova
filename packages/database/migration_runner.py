"""Automated SQL migration runner for Nova ERP database."""
import os
import sys
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List, Set, Tuple
import psycopg2
from dotenv import load_dotenv

from packages.database.apply_schema import split_sql_statements, load_environment

logger = logging.getLogger(__name__)

TRACKING_TABLE = '"Nova"._migrations'


def get_default_migrations_dir() -> Path:
    """Resolve the default migrations directory."""
    root = Path(__file__).resolve().parent.parent.parent
    return root / 'database' / 'migrations'


def ensure_tracking_table(cur):
    """Ensure the schema and migration tracking table exist."""
    cur.execute('CREATE SCHEMA IF NOT EXISTS "Nova";')
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS {TRACKING_TABLE} (
            seq         INT  PRIMARY KEY,
            filename    TEXT NOT NULL,
            applied_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
            sql_hash    BIGINT
        );
    """)


def get_applied_migrations(cur) -> Set[str]:
    """Retrieve set of filenames for migrations already applied."""
    ensure_tracking_table(cur)
    cur.execute(f"SELECT filename FROM {TRACKING_TABLE} ORDER BY seq")
    return {row[0] for row in cur.fetchall()}


def mark_migration_applied(cur, seq: int, filename: str, sql_content: str):
    """Record a migration as applied in the tracking table."""
    cur.execute(
        f"INSERT INTO {TRACKING_TABLE} (seq, filename, sql_hash) VALUES (%s, %s, %s) "
        f"ON CONFLICT (seq) DO UPDATE SET filename = EXCLUDED.filename, applied_at = EXCLUDED.applied_at, sql_hash = EXCLUDED.sql_hash",
        (seq, filename, hash(sql_content))
    )


def run_migrations(
    conn=None,
    migrations_dir: Optional[Path] = None,
    stop_on_error: bool = True
) -> Dict[str, Any]:
    """
    Run all pending migrations in the migrations directory in sequential order.

    Returns a dict with execution statistics and details.
    """
    target_dir = Path(migrations_dir) if migrations_dir else get_default_migrations_dir()
    if not target_dir.exists():
        raise FileNotFoundError(f"Migrations directory not found: {target_dir}")

    should_close = False
    if conn is None:
        load_environment()
        db_host = os.getenv('DB_HOST', 'localhost')
        if db_host == 'localhost' and os.name == 'nt':
            db_host = '127.0.0.1'
        db_port = int(os.getenv('DB_PORT', '5432'))
        db_name = os.getenv('DB_NAME', 'nova_erp')
        db_user = os.getenv('DB_USER', 'nova')
        db_pass = os.getenv('DB_PASSWORD', 'nova_secret')
        db_ssl = os.getenv('DB_SSLMODE', 'prefer')

        conn = psycopg2.connect(
            host=db_host,
            port=db_port,
            dbname=db_name,
            user=db_user,
            password=db_pass,
            sslmode=db_ssl,
        )
        conn.autocommit = False
        should_close = True

    cur = conn.cursor()
    applied_files: List[str] = []
    skipped_files: List[str] = []
    failed_files: List[Tuple[str, str]] = []

    try:
        ensure_tracking_table(cur)
        conn.commit()

        applied_set = get_applied_migrations(cur)
        sql_files = sorted(target_dir.glob('*.sql'))

        for idx, fpath in enumerate(sql_files, 1):
            fname = fpath.name
            if fname in applied_set:
                skipped_files.append(fname)
                continue

            sql_content = fpath.read_text(encoding='utf-8')
            stmts = split_sql_statements(sql_content)

            try:
                for stmt in stmts:
                    clean = stmt.strip()
                    if clean:
                        cur.execute(clean)
                mark_migration_applied(cur, idx, fname, sql_content)
                conn.commit()
                applied_files.append(fname)
                logger.info(f"Migration applied successfully: {fname}")
            except Exception as e:
                conn.rollback()
                failed_files.append((fname, str(e)))
                logger.error(f"Migration failed on {fname}: {e}")
                if stop_on_error:
                    break

        return {
            "success": len(failed_files) == 0,
            "total_files": len(sql_files),
            "applied_count": len(applied_files),
            "skipped_count": len(skipped_files),
            "failed_count": len(failed_files),
            "applied_files": applied_files,
            "skipped_files": skipped_files,
            "failed_files": failed_files,
        }

    finally:
        cur.close()
        if should_close:
            conn.close()


def get_migration_status(conn=None, migrations_dir: Optional[Path] = None) -> Dict[str, Any]:
    """
    Get the status of migrations: applied vs pending.
    """
    target_dir = Path(migrations_dir) if migrations_dir else get_default_migrations_dir()
    sql_files = sorted(target_dir.glob('*.sql'))

    should_close = False
    if conn is None:
        load_environment()
        db_host = os.getenv('DB_HOST', 'localhost')
        if db_host == 'localhost' and os.name == 'nt':
            db_host = '127.0.0.1'
        db_port = int(os.getenv('DB_PORT', '5432'))
        db_name = os.getenv('DB_NAME', 'nova_erp')
        db_user = os.getenv('DB_USER', 'nova')
        db_pass = os.getenv('DB_PASSWORD', 'nova_secret')
        db_ssl = os.getenv('DB_SSLMODE', 'prefer')

        conn = psycopg2.connect(
            host=db_host,
            port=db_port,
            dbname=db_name,
            user=db_user,
            password=db_pass,
            sslmode=db_ssl,
        )
        should_close = True

    cur = conn.cursor()
    try:
        applied_set = get_applied_migrations(cur)
        all_names = [f.name for f in sql_files]
        applied = [name for name in all_names if name in applied_set]
        pending = [name for name in all_names if name not in applied_set]

        return {
            "total": len(all_names),
            "applied_count": len(applied),
            "pending_count": len(pending),
            "applied": applied,
            "pending": pending,
        }
    finally:
        cur.close()
        if should_close:
            conn.close()


if __name__ == '__main__':
    load_environment()
    results = run_migrations()
    print("Migration execution summary:")
    print(f" Applied: {results['applied_count']}")
    print(f" Skipped: {results['skipped_count']}")
    print(f" Failed:  {results['failed_count']}")
    if results['failed_files']:
        for fn, err in results['failed_files']:
            print(f"  * {fn}: {err}")
    sys.exit(0 if results['success'] else 1)
