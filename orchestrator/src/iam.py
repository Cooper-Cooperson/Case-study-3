import logging

logger = logging.getLogger(__name__)

def create_user_in_db_and_identity(user):
    # TODO: integrate with Cloud SQL / Cloud Identity
    logger.info(f"[IAM] Creating user: {user['email']} in DB and Identity")

def assign_roles(user):
    # TODO: integrate with Cloud IAM / groups
    logger.info(f"[IAM] Assigning roles for {user['email']} - role: {user['role']}")