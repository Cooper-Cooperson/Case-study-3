import logging
import os
from concurrent.futures import TimeoutError

from google.cloud import pubsub_v1

from src.handler import handle_new_hire, handle_user_deleted
from src import db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PROJECT_ID = os.getenv("PROJECT_ID")
NEW_HIRE_SUBSCRIPTION_ID = os.getenv("SUBSCRIPTION_ID")  # existing env
USER_DELETED_SUBSCRIPTION_ID = os.getenv("USER_DELETED_SUBSCRIPTION_ID")


def main():
    db.init_schema()

    subscriber = pubsub_v1.SubscriberClient()

    new_hire_path = subscriber.subscription_path(
        PROJECT_ID, NEW_HIRE_SUBSCRIPTION_ID
    )
    user_deleted_path = subscriber.subscription_path(
        PROJECT_ID, USER_DELETED_SUBSCRIPTION_ID
    )

    def new_hire_callback(message: pubsub_v1.subscriber.message.Message):
        logger.info("Received message on new hire subscription")
        try:
            handle_new_hire(message.data)
            message.ack()
        except Exception:
            logger.exception("Error processing new hire message")
            # let Pub/Sub retry
            message.nack()

    def user_deleted_callback(message: pubsub_v1.subscriber.message.Message):
        logger.info("Received message on user deleted subscription")
        try:
            handle_user_deleted(message.data)
            message.ack()
        except Exception:
            logger.exception("Error processing user deleted message")
            message.nack()

    new_hire_future = subscriber.subscribe(new_hire_path, callback=new_hire_callback)
    user_deleted_future = subscriber.subscribe(
        user_deleted_path, callback=user_deleted_callback
    )

    logger.info(
        "Listening on %s and %s",
        new_hire_path,
        user_deleted_path,
    )

    try:
        new_hire_future.result()
        user_deleted_future.result()
    except TimeoutError:
        new_hire_future.cancel()
        user_deleted_future.cancel()


if __name__ == "__main__":
    main()
