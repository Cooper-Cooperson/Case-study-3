import logging

logger = logging.getLogger(__name__)

def simulate_cloud_identity_user(user: dict) -> str:
    logger.info("[SIM] Pretending to create Cloud Identity user: %s", user["email"])
    return user["email"]

def simulate_add_to_groups(email: str):
    logger.info("[SIM] Pretending to add %s to default groups", email)