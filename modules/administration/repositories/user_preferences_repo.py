import psycopg2.extras
from packages.database.connection import get_connection, release_connection


class UserPreferencesRepo:
    TABLE = '"Nova".t0106'

    def get_all(self, user_id: int) -> dict[str, str]:
        conn = get_connection()
        try:
            sql = f'SELECT pref_key, pref_value FROM {self.TABLE} WHERE user_id = %s'
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(sql, (user_id,))
                return {r['pref_key']: r['pref_value'] for r in cur.fetchall()}
        finally:
            release_connection(conn)

    def upsert(self, user_id: int, prefs: dict[str, str]) -> int:
        conn = get_connection()
        try:
            count = 0
            for key, value in prefs.items():
                sql = f'''
                    INSERT INTO {self.TABLE} (user_id, pref_key, pref_value)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (user_id, pref_key)
                    DO UPDATE SET pref_value = EXCLUDED.pref_value, updated_at = NOW()
                '''
                with conn.cursor() as cur:
                    cur.execute(sql, (user_id, key, str(value) if value is not None else None))
                count += 1
            conn.commit()
            return count
        except Exception:
            conn.rollback()
            raise
        finally:
            release_connection(conn)
