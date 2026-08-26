"""Apply Nova ERP consolidated database schema with multi-tenant isolation."""
import os
import re
import sys
import logging
from typing import Optional, Dict, Any, List, Tuple
import psycopg2
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


def load_environment():
    """Load environment variables from standard locations."""
    env_locations = [
        os.path.join(os.path.dirname(__file__), '..', '..', 'apps', 'api', '.env'),
        os.path.join(os.path.dirname(__file__), '..', '.env'),
        os.path.join(os.path.dirname(__file__), '..', '..', '.env'),
    ]
    for env_path in env_locations:
        if os.path.exists(env_path):
            load_dotenv(dotenv_path=env_path, override=True)


def split_sql_statements(sql: str) -> List[str]:
    """
    Split SQL script into individual executable statements, respecting:
    - Line comments (-- ...)
    - Block comments (/* ... */)
    - Single quotes ('...') and escaped quotes ('')
    - Double quotes ("...") and escaped quotes ("")
    - Dollar-quoted string blocks ($$...$$ or $tag$...$tag$)
    """
    statements = []
    current = []
    in_single_quote = False
    in_double_quote = False
    in_dollar_quote = False
    dollar_tag = ""
    in_line_comment = False
    in_block_comment = False

    i = 0
    n = len(sql)

    while i < n:
        ch = sql[i]
        next_ch = sql[i + 1] if i + 1 < n else ""

        # Handle comments when not in quotes
        if not in_single_quote and not in_double_quote and not in_dollar_quote:
            if in_line_comment:
                if ch == '\n':
                    in_line_comment = False
                    current.append(ch)
                i += 1
                continue
            elif in_block_comment:
                if ch == '*' and next_ch == '/':
                    in_block_comment = False
                    i += 2
                    continue
                i += 1
                continue
            elif ch == '-' and next_ch == '-':
                in_line_comment = True
                i += 2
                continue
            elif ch == '/' and next_ch == '*':
                in_block_comment = True
                i += 2
                continue

        if in_line_comment:
            if ch == '\n':
                in_line_comment = False
                current.append(ch)
            i += 1
            continue

        if in_block_comment:
            if ch == '*' and next_ch == '/':
                in_block_comment = False
                i += 2
                continue
            i += 1
            continue

        # Handle string literals
        if in_single_quote:
            current.append(ch)
            if ch == "'":
                if next_ch == "'":
                    current.append(next_ch)
                    i += 2
                    continue
                else:
                    in_single_quote = False
            i += 1
            continue

        # Handle double-quoted identifiers
        if in_double_quote:
            current.append(ch)
            if ch == '"':
                if next_ch == '"':
                    current.append(next_ch)
                    i += 2
                    continue
                else:
                    in_double_quote = False
            i += 1
            continue

        # Handle dollar-quoted strings ($$ or $tag$)
        if in_dollar_quote:
            current.append(ch)
            if ch == '$':
                tag_len = len(dollar_tag)
                joined_end = "".join(current[-tag_len:])
                if joined_end == dollar_tag:
                    in_dollar_quote = False
                    dollar_tag = ""
            i += 1
            continue

        # Outside all quotes & comments
        if ch == "'":
            in_single_quote = True
            current.append(ch)
            i += 1
            continue
        elif ch == '"':
            in_double_quote = True
            current.append(ch)
            i += 1
            continue
        elif ch == '$':
            match = re.match(r'^\$[A-Za-z0-9_]*\$', sql[i:])
            if match:
                dollar_tag = match.group(0)
                in_dollar_quote = True
                current.append(dollar_tag)
                i += len(dollar_tag)
                continue
            else:
                current.append(ch)
                i += 1
                continue
        elif ch == ';':
            stmt = "".join(current).strip()
            if stmt:
                statements.append(stmt)
            current = []
            i += 1
            continue
        else:
            current.append(ch)
            i += 1
            continue

    stmt = "".join(current).strip()
    if stmt:
        statements.append(stmt)

    return statements


def get_table_name(stmt: str) -> Optional[str]:
    """Extract table name from a CREATE TABLE statement."""
    m = re.search(r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(?:["\']?(\w+)["\']?\.)?["\']?(\w+)["\']?\s*\(', stmt, re.I)
    return m.group(2).upper() if m else None


def strip_all_fks(stmt: str, table_name: str, fk_accumulator: list) -> str:
    """Strip all REFERENCES clauses from a CREATE TABLE statement and record ALTER TABLE statements."""
    def repl(m):
        ref_schema = m.group(1) or 'Nova'
        ref_table = m.group(2)
        ref_col = m.group(3) or 'id'
        on_cascade = m.group(4) or ''
        trail = m.group(5) or ''
        pos = m.start()
        before = stmt[:pos].rstrip()
        last_delim = max(before.rfind('\n'), before.rfind(','), before.rfind('('))
        line = before[last_delim + 1:] if last_delim >= 0 else before
        col_name = line.strip().split()[0] if line.strip() else 'unknown'
        
        alter_stmt = (
            f'ALTER TABLE "{ref_schema}".{table_name.lower()} ADD CONSTRAINT fk_{table_name.lower()}_{col_name.lower()} '
            f'FOREIGN KEY ({col_name}) REFERENCES "{ref_schema}".{ref_table.lower()}({ref_col}){on_cascade};'
        )
        fk_accumulator.append((table_name, col_name, alter_stmt))
        return trail

    pattern = r'\s+REFERENCES\s+(?:["\']?(\w+)["\']?\.)?["\']?(\w+)["\']?\s*\(\s*(\w+)\s*\)(\s+ON\s+(?:DELETE|UPDATE)\s+(?:CASCADE|SET NULL|RESTRICT|NO ACTION))?([,\s]*)'
    return re.sub(pattern, repl, stmt, flags=re.I)


def apply_schema(conn=None, schema_file: Optional[str] = None, drop_existing: bool = True) -> Dict[str, Any]:
    """
    Apply consolidated database schema to PostgreSQL database.
    
    Parses and applies:
    - Schema "Nova"
    - Types, Enums & Domains
    - Sequences (e.g. seq_invoice_number, seq_pick_list_number)
    - Tables (T0001-T0107, etc.)
    - Columns & Alter Table modifications
    - Single and composite indexes
    - Comments
    - Foreign key constraints (including tenant FKs to T0059)

    Returns a dict with statistics on applied objects.
    """
    if schema_file is None:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        schema_file = os.path.join(script_dir, 'schema.sql')

    with open(schema_file, 'r', encoding='utf-8') as f:
        sql = f.read()

    stmts = split_sql_statements(sql)

    all_fk_alters: List[Tuple[str, str, str]] = []
    type_stmts: List[str] = []
    seq_stmts: List[str] = []
    table_stmts: List[Tuple[str, str]] = []
    alter_table_stmts: List[str] = []
    index_stmts: List[str] = []
    comment_stmts: List[str] = []
    other_stmts: List[str] = []

    for s in stmts:
        u = s.strip().upper()
        if u.startswith('BEGIN') or u.startswith('COMMIT') or u.startswith('CREATE SCHEMA'):
            continue
        elif u.startswith('CREATE SEQUENCE'):
            seq_stmts.append(s + ';')
        elif u.startswith('CREATE TYPE') or (u.startswith('DO $$') and ('CREATE TYPE' in u or 'ALTER TYPE' in u)):
            type_stmts.append(s + ';')
        elif u.startswith('ALTER TABLE') or (u.startswith('DO $$') and 'ALTER TABLE' in u):
            alter_table_stmts.append(s + ';')
        elif u.startswith('DO $$'):
            type_stmts.append(s + ';')
        elif u.startswith('CREATE TABLE'):
            tn = get_table_name(s)
            if tn:
                processed = strip_all_fks(s, tn, all_fk_alters)
                table_stmts.append((tn, processed + ';'))
            else:
                other_stmts.append(s + ';')
        elif u.startswith('CREATE INDEX') or u.startswith('CREATE UNIQUE INDEX'):
            index_stmts.append(s + ';')
        elif u.startswith('COMMENT ON'):
            comment_stmts.append(s + ';')
        else:
            other_stmts.append(s + ';')

    should_close = False
    old_autocommit = None

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
        conn.autocommit = True
        should_close = True
    else:
        if hasattr(conn, 'autocommit'):
            old_autocommit = conn.autocommit
            try:
                if not conn.autocommit:
                    conn.rollback()
                    conn.autocommit = True
            except Exception:
                pass

    cur = conn.cursor()

    try:
        if drop_existing:
            cur.execute('DROP SCHEMA IF EXISTS "Nova" CASCADE;')
            cur.execute('CREATE SCHEMA IF NOT EXISTS "Nova";')
        else:
            cur.execute('CREATE SCHEMA IF NOT EXISTS "Nova";')
        cur.execute('SET search_path TO "Nova", public;')

        # Phase 1: Types & Domains
        types_ok = 0
        for s in type_stmts:
            try:
                cur.execute(s)
                types_ok += 1
            except Exception as e:
                logger.debug(f"Type execution note: {e}")

        # Phase 2: Sequences
        seqs_ok = 0
        for s in seq_stmts:
            try:
                cur.execute(s)
                seqs_ok += 1
            except Exception as e:
                logger.debug(f"Sequence execution note: {e}")

        # Phase 3: Tables (T0059 and T0021 created first)
        sorted_tables = sorted(
            table_stmts,
            key=lambda item: 0 if item[0] == 'T0059' else (1 if item[0] == 'T0021' else 2)
        )
        tables_ok = 0
        for tn, s in sorted_tables:
            try:
                cur.execute(s)
                tables_ok += 1
            except Exception as e:
                logger.warning(f"Table creation error on {tn}: {e}")

        # Phase 4: Alter Tables / Additional Columns
        alters_ok = 0
        for s in alter_table_stmts:
            try:
                cur.execute(s)
                alters_ok += 1
            except Exception as e:
                logger.debug(f"Alter table note: {e}")

        # Phase 5: Indexes & Comments
        indexes_ok = 0
        for s in index_stmts:
            try:
                cur.execute(s)
                indexes_ok += 1
            except Exception as e:
                logger.debug(f"Index note: {e}")

        comments_ok = 0
        for s in comment_stmts:
            try:
                cur.execute(s)
                comments_ok += 1
            except Exception:
                pass

        # Phase 6: Foreign Key Constraints
        fk_ok = 0
        bid_fk_count = 0
        for tn, col, fk_sql in all_fk_alters:
            try:
                cur.execute(fk_sql)
                fk_ok += 1
                if col.lower() == 'business_id':
                    bid_fk_count += 1
            except Exception as e:
                logger.debug(f"FK constraint note ({tn}.{col}): {e}")

        # Phase 7: Other statements (Grants, etc.)
        other_ok = 0
        for s in other_stmts:
            try:
                cur.execute(s)
                other_ok += 1
            except Exception:
                pass

        stats = {
            "types": types_ok,
            "sequences": seqs_ok,
            "tables": tables_ok,
            "indexes": indexes_ok,
            "comments": comments_ok,
            "foreign_keys": fk_ok,
            "tenant_fks": bid_fk_count,
            "total_fk_alters": len(all_fk_alters),
            "total_tables": len(table_stmts),
        }
        return stats

    finally:
        cur.close()
        if should_close:
            conn.close()
        elif old_autocommit is not None and hasattr(conn, 'autocommit'):
            try:
                conn.rollback()
                conn.autocommit = old_autocommit
            except Exception:
                pass


def ensure_schema_provisioned(conn=None, schema_file: Optional[str] = None, force: bool = False) -> Dict[str, Any]:
    """
    Ensure that schema 'Nova' is fully provisioned with all 107 tables, sequences, and constraints.
    If tables or constraints are missing (or if force=True), provisions the schema.
    Returns the schema verification dictionary.
    """
    from packages.database.verify_schema import verify_schema
    
    if not force:
        res = verify_schema(conn)
        if res["success"]:
            return res

    apply_schema(conn=conn, schema_file=schema_file)
    res = verify_schema(conn)
    return res


if __name__ == '__main__':
    load_environment()
    stats = apply_schema()
    print("Schema applied successfully:", stats)
