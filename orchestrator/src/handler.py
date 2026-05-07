import json
import logging
from .iam import create_user_in_db_and_identity, assign_roles

logger = logging.getLogger(__name__)

def handle_new_hire(message_data: bytes):
    payload = json.loads(message_data.decode("utf-8"))
    logger.info(f"[ORCH] Received new hire event: {payload}")

    user = {
        "id": payload.get("id"),
        "name": payload.get("name"),
        "email": payload.get("email"),
        "department": payload.get("department"),
        "role": payload.get("role"),
    }

    create_user_in_db_and_identity(user)
    assign_roles(user)

    logger.info(f"[ORCH] Finished processing new hire: {user['email']}")