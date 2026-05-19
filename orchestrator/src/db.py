import os
import logging
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2 import sql, errors

logger = logging.getLogger(__name__)

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")


def get_db_connection():
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
    )
    return conn


def init_schema():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            department TEXT,
            role TEXT,
            status TEXT,
            created_at TIMESTAMP DEFAULT NOW()
        );
        """
    )
    conn.commit()
    cur.close()
    conn.close()
    logger.info("Ensured users table exists")


def insert_user(user: dict) -> int | None:
    """
    Upsert by email:
    - if email does not exist: insert and return id
    - if email exists: update fields and return existing id
    """
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    logger.info("Inserting user into Postgres: %s", user.get("email"))

    try:
        cur.execute(
            """
            INSERT INTO users (name, email, department, role, status)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (email)
            DO UPDATE SET
                name = EXCLUDED.name,
                department = EXCLUDED.department,
                role = EXCLUDED.role,
                status = EXCLUDED.status
            RETURNING id;
            """,
            (
                user.get("name"),
                user.get("email"),
                user.get("department"),
                user.get("role"),
                user.get("status"),
            ),
        )
        row = cur.fetchone()
        conn.commit()
        return row["id"]
    finally:
        cur.close()
        conn.close()


def delete_user_by_email(email: str) -> int:
    """
    Delete user by email. Returns number of rows deleted.
    """
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM users WHERE email = %s", (email,))
    deleted = cur.rowcount
    conn.commit()
    cur.close()
    conn.close()
    return deleted
