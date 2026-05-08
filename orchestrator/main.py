import logging
import os
from google.cloud import pubsub_v1, logging as cloud_logging
from src import config, handler, db

# Cloud Logging setup
cloud_logging.Client().setup_logging()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def callback(message: pubsub_v1.subscriber.message.Message):
    logger.info("Received message: %s", message.message_id)
    try:
        handler.handle_new_hire(message.data)
        message.ack()
        logger.info("Message %s processed and ACKed", message.message_id)
    except Exception:
        logger.exception("Error processing message %s, NACKing", message.message_id)
        message.nack()

def main():
    db.init_schema()

    subscriber = pubsub_v1.SubscriberClient()
    subscription_path = subscriber.subscription_path(
        config.PROJECT_ID,
        config.SUBSCRIPTION_ID,
    )

    logger.info("Listening on %s", subscription_path)
    streaming_pull_future = subscriber.subscribe(subscription_path, callback=callback)

    try:
        streaming_pull_future.result()
    except KeyboardInterrupt:
        streaming_pull_future.cancel()

if __name__ == "__main__":
    main()
