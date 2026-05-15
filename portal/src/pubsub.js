const { PubSub } = require("@google-cloud/pubsub");

const pubsub = new PubSub();
const topicName = "new-hire-events";

async function publishNewHire(data) {
  const buffer = Buffer.from(JSON.stringify(data));
  await pubsub.topic(topicName).publish(buffer);
  console.log("Published new hire event:", data.email);
}

async function publishUserDeleted(email) {
  const topic = pubsub.topic("user-deleted-events");

  const message = {
    email,
    timestamp: new Date().toISOString()
  };

  await topic.publishMessage({ json: message });
  console.log("Published user deleted event:", message);
}

module.exports = {
  publishNewHire,
  publishUserDeleted
};