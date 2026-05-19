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
        "status": payload.get("status") or "PENDING",
    }

    try:
        user_id = db.insert_user(user)
        logger.info("[ORCH] User stored/updated in DB with id=%s", user_id)
    except Exception:
        logger.exception("Failed to insert user into DB")
        # we log and re-raise so Pub/Sub can retry if needed
        raise


def handle_user_deleted(message_data: bytes):
    payload = json.loads(message_data.decode("utf-8"))
    email = payload.get("email")

    logger.info("[ORCH] Received user deleted event: %s", email)

    try:
        deleted = db.delete_user_by_email(email)
        logger.info("[ORCH] Deleted %s user(s) from DB for email=%s", deleted, email)
    except Exception:
        logger.exception("Failed to delete user from DB")
        raise
