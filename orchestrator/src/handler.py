import json
import logging
from . import db

logger = logging.getLogger(__name__)

def handle_new_hire(message_data: bytes):
    payload = json.loads(message_data.decode("utf-8"))
    logger.info("[ORCH] Received new hire event: %s", payload)

    user = {
        "name": payload.get("name"),
        "email": payload.get("email"),
        "department": payload.get("department"),
        "role": payload.get("role"),
        "status": "PENDING",
    }

 # Persist in DB
    try:
        user_id = db.insert_user(user)
        logger.info("[ORCH] User stored in DB with id=%s", user_id)
    except Exception:
        logger.exception("Failed to insert user into DB")
        raise
    
def handle_user_deleted(message_data: bytes):
    payload = json.loads(message_data.decode("utf-8"))
    email = payload.get("email")

    logger.info(f"[ORCH] Received user deleted event: {email}")

    conn = db.get_connection()
    cur = conn.cursor()
    try:
        with conn, conn.cursor() as cur:
            cur.execute("DELETE FROM users WHERE email = %s", (email,))
        logger.info(f"[ORCH] Deleted user from DB: {email}")
    finally:
        conn.commit()
        cur.close()
        conn.close()

    logger.info(f"[ORCH] Deleted user from DB: {email}")