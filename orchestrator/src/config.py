import os

PROJECT_ID = os.environ["PROJECT_ID"]

# Pub/Sub
SUBSCRIPTION_ID = os.environ.get("SUBSCRIPTION_ID", "new-hire-orchestrator-sub")

# Cloud SQL Postgres
DB_HOST = os.environ["DB_HOST"]   
DB_PORT = int(os.environ.get("DB_PORT", "5432"))
DB_NAME = os.environ["DB_NAME"]       
DB_USER = os.environ["DB_USER"]
DB_PASSWORD = os.environ["DB_PASSWORD"]                   

# IAM / Groups
PROJECT_NUMBER = os.environ["PROJECT_NUMBER"]              
DEFAULT_IAM_ROLES = os.environ.get(
    "DEFAULT_IAM_ROLES",
    "roles/viewer"
).split(",")

DEFAULT_GROUPS = os.environ.get(
    "DEFAULT_GROUPS",
    "it-onboarding@example.com"
).split(",")