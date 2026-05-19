import logging
import json
from google.cloud import pubsub_v1, logging as cloud_logging
from src import config, handler, db
from src.handler import handle_new_hire, handle_user_deleted

# Cloud Logging setup
cloud_logging.Client().setup_logging()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def callback(message):
    try:
        data = message.data.decode("utf-8")
        payload = json.loads(data)

        if "role" in payload:  # new hire event
            handle_new_hire(message.data)
        else:  # deletion event
            handle_user_deleted(message.data)

        message.ack()
    except Exception as e:
        logger.exception("Error processing message")
        message.nack()

def main():
    db.init_schema()

    subscriber = pubsub_v1.SubscriberClient()

    sub_new_hire = subscriber.subscription_path(
        config.PROJECT_ID, config.SUBSCRIPTION_ID
    )

    sub_user_deleted = subscriber.subscription_path(
        config.PROJECT_ID, "user-deleted-orchestrator-sub"
    )

    logger.info(f"Listening on: {sub_new_hire}")
    logger.info(f"Listening on: {sub_user_deleted}")

    subscriber.subscribe(sub_new_hire, callback=callback)
    subscriber.subscribe(sub_user_deleted, callback=callback)

    # Keep process alive
    import time
    while True:
        time.sleep(60)
if __name__ == "__main__":
    main()