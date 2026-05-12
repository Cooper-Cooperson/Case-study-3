import logging

logger = logging.getLogger(__name__)

def simulate_assign_iam_roles(email: str):
    logger.info("[SIM] Pretending to assign IAM roles to %s", email)