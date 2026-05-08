import logging
from google.oauth2 import service_account
from googleapiclient.discovery import build
from . import config

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/admin.directory.user",
    "https://www.googleapis.com/auth/admin.directory.group",
]

def _get_directory_service():
    creds = service_account.Credentials.from_service_account_file(
        "/var/secrets/google/key.json",  
        scopes=SCOPES,
    )
    delegated = creds.with_subject(config.ADMIN_DELEGATED_USER)
    service = build("admin", "directory_v1", credentials=delegated, cache_discovery=False)
    return service

def create_cloud_identity_user(user: dict) -> str:
    """Create a user in Cloud Identity / Workspace. Returns user primary email."""
    service = _get_directory_service()

    body = {
        "primaryEmail": user["email"],
        "name": {
            "givenName": user["name"].split(" ")[0],
            "familyName": " ".join(user["name"].split(" ")[1:]) or user["name"],
        },
        "password": "TempPassw0rd!", # in praktijk genereer een wachtwoord en forceer een nieuwe.
        "changePasswordAtNextLogin": True,
    }

    logger.info("Creating Cloud Identity user: %s", user["email"])
    created = service.users().insert(body=body).execute()
    logger.info("Cloud Identity user created: %s", created["primaryEmail"])
    return created["primaryEmail"]

def add_user_to_groups(email: str):
    service = _get_directory_service()

    for group_email in config.DEFAULT_GROUPS:
        logger.info("Adding %s to group %s", email, group_email)
        try:
            service.members().insert(
                groupKey=group_email,
                body={"email": email, "role": "MEMBER"},
            ).execute()
            logger.info("Added %s to %s", email, group_email)
        except Exception as e:
            logger.exception("Failed to add %s to group %s", email, group_email)
