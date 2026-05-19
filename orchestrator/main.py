import os
import logging
from google.cloud import pubsub_v1
from concurrent.futures import TimeoutError

from src.handler import handle_new_hire, handle_user_deleted
from src import db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PROJECT_ID = os.getenv("PROJECT_ID")
NEW_HIRE_SUBSCRIPTION_ID = os.getenv("SUBSCRIPTION_ID")
USER_DELETED_SUBSCRIPTION_ID = os.getenv("USER_DELETED_SUBSCRIPTION_ID")


def main():
    # Ensure DB schema exists
    db.init_schema()

    subscriber = pubsub_v1.SubscriberClient()

    new_hire_path = subscriber.subscription_path(
        PROJECT_ID, NEW_HIRE_SUBSCRIPTION_ID
    )
    user_deleted_path = subscriber.subscription_path(
        PROJECT_ID, USER_DELETED_SUBSCRIPTION_ID
    )

    def new_hire_callback(message):
        logger.info("Received NEW HIRE message")
        try:
            handle_new_hire(message.data)
            message.ack()
        except Exception:
            logger.exception("Error processing NEW HIRE message")
            message.nack()

    def user_deleted_callback(message):
        logger.info("Received USER DELETED message")
        try:
            handle_user_deleted(message.data)
            message.ack()
        except Exception:
            logger.exception("Error processing USER DELETED message")
            message.nack()

    subscriber.subscribe(new_hire_path, callback=new_hire_callback)
    subscriber.subscribe(user_deleted_path, callback=user_deleted_callback)

    logger.info("Listening on Pub/Sub subscriptions:")
    logger.info(f" - New Hire: {new_hire_path}")
    logger.info(f" - User Deleted: {user_deleted_path}")

    try:
        while True:
            pass
    except KeyboardInterrupt:
        logger.info("Shutting down orchestrator…")


if __name__ == "__main__":
    main()