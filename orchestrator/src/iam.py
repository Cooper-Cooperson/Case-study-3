import logging
from google.oauth2 import service_account
from googleapiclient.discovery import build
from . import config

logger = logging.getLogger(__name__)

IAM_SCOPES = [
    "https://www.googleapis.com/auth/cloud-platform",
]

def _get_crm_service():
    creds = service_account.Credentials.from_service_account_file(
        "/var/secrets/google/key.json",
        scopes=IAM_SCOPES,
    )
    service = build("cloudresourcemanager", "v1", credentials=creds, cache_discovery=False)
    return service

def assign_iam_roles(email: str):
    """Grant project-level IAM roles to the user."""
    service = _get_crm_service()
    project_id = config.PROJECT_ID

    policy = service.projects().getIamPolicy(
        resource=project_id,
        body={"options": {"requestedPolicyVersion": 3}},
    ).execute()

    bindings = policy.get("bindings", [])

    for role in config.DEFAULT_IAM_ROLES:
        logger.info("Ensuring IAM role %s for %s", role, email)
        member = f"user:{email}"

        binding = next((b for b in bindings if b["role"] == role), None)
        if not binding:
            binding = {"role": role, "members": []}
            bindings.append(binding)

        if member not in binding["members"]:
            binding["members"].append(member)

    policy["bindings"] = bindings

    updated = service.projects().setIamPolicy(
        resource=project_id,
        body={"policy": policy},
    ).execute()

    logger.info("Updated IAM policy for project %s", project_id)
    return updated
