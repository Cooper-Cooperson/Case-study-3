import logging
import psycopg2
from psycopg2.extras import RealDictCursor
from . import config

logger = logging.getLogger(__name__)

def get_connection():
    conn = psycopg2.connect(
        host=config.DB_HOST,
        port=config.DB_PORT,
        dbname=config.DB_NAME,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        cursor_factory=RealDictCursor,
    )
    return conn

def init_schema():
    """Create users table if it doesn't exist."""
    ddl = """
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        name VARCHAR(255) NOT NULL,
        email VARCHAR(255) NOT NULL UNIQUE,
        department VARCHAR(255),
        role VARCHAR(255),
        status VARCHAR(32) NOT NULL,
        created_at TIMESTAMPTZ DEFAULT NOW()
    );
    """
    conn = get_connection()
    try:
        with conn, conn.cursor() as cur:
            cur.execute(ddl)
        logger.info("Ensured users table exists")
    finally:
        conn.close()

def insert_user(user: dict):
    logger.info("Inserting user into Postgres: %s", user["email"])
    sql = """
    INSERT INTO users (name, email, department, role, status)
    VALUES (%s, %s, %s, %s, %s)
    RETURNING id;
    """
    conn = get_connection()
    try:
        with conn, conn.cursor() as cur:
            cur.execute(
                sql,
                (
                    user["name"],
                    user["email"],
                    user.get("department"),
                    user.get("role"),
                    user.get("status", "NEW"),
                ),
            )  
        new_id = cur.fetchone()["id"]
        logger.info("User inserted with ID %s", new_id)
        logger.info("User persisted in DB: %s", user["email"])
        return new_id
    finally:
        conn.close()