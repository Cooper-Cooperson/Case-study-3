import json
import logging
from . import db
from .identity import simulate_cloud_identity_user, simulate_add_to_groups
from .iam import simulate_assign_iam_roles

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

    # Simulate Cloud Identity user creation
    try:
        primary_email = simulate_cloud_identity_user(user)
    except Exception:
        logger.exception("Simulated Cloud Identity creation failed")
        raise

    # Simulate IAM roles
    try:
        simulate_assign_iam_roles(primary_email)
    except Exception:
        logger.exception("Simulated IAM role assignment failed")
        raise

    # Simulate group membership
    try:
        simulate_add_to_groups(primary_email)
    except Exception:
        logger.exception("Simulated group assignment failed")

    logger.info("[ORCH] Finished simulated provisioning for: %s", primary_email)