const { PubSub } = require("@google-cloud/pubsub");

const pubsub = new PubSub();
const topicName = "new-hire-events";

async function publishNewHire(data) {
  const buffer = Buffer.from(JSON.stringify(data));
  await pubsub.topic(topicName).publish(buffer);
  console.log("Published new hire event:", data.email);
}

module.exports = { publishNewHire };