import json
import logging
from . import db, identity, iam

logger = logging.getLogger(__name__)

def handle_new_hire(message_data: bytes):
    payload = json.loads(message_data.decode("utf-8"))
    logger.info("[ORCH] Received new hire event: %s", payload)

    user = {
        "id": payload.get("id"),
        "name": payload.get("name"),
        "email": payload.get("email"),
        "department": payload.get("department"),
        "role": payload.get("role"),
        "status": "PENDING",
    }

    try:
        db.insert_user(user)
    except Exception:
        logger.exception("Failed to insert user into DB")
        raise

    #Create Cloud Identity user
    try:
        primary_email = identity.create_cloud_identity_user(user)
    except Exception:
        logger.exception("Failed to create Cloud Identity user")
        raise

    #Assign IAM roles
    try:
        iam.assign_iam_roles(primary_email)
    except Exception:
        logger.exception("Failed to assign IAM roles")
        raise

    #Add to groups
    try:
        identity.add_user_to_groups(primary_email)
    except Exception:
        logger.exception("Failed to add user to groups")
        # non-fatal: we log but don't fail the whole flow

    logger.info("[ORCH] Finished provisioning new hire: %s", primary_email)
