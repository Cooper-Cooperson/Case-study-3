import logging
import os
from google.cloud import pubsub_v1
from src.handler import handle_new_hire

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PROJECT_ID = os.environ.get("PROJECT_ID")
SUBSCRIPTION_ID = os.environ.get("SUBSCRIPTION_ID", "new-hire-orchestrator-sub")

def callback(message: pubsub_v1.subscriber.message.Message):
    try:
        handle_new_hire(message.data)
        message.ack()
    except Exception as e:
        logger.exception("Error processing message, NACKing")
        message.nack()

def main():
    if not PROJECT_ID:
        raise RuntimeError("PROJECT_ID env var is required")

    subscriber = pubsub_v1.SubscriberClient()
    subscription_path = subscriber.subscription_path(PROJECT_ID, SUBSCRIPTION_ID)

    logger.info(f"[ORCH] Listening on {subscription_path}")
    streaming_pull_future = subscriber.subscribe(subscription_path, callback=callback)

    try:
        streaming_pull_future.result()
    except KeyboardInterrupt:
        streaming_pull_future.cancel()

if __name__ == "__main__":
    main()