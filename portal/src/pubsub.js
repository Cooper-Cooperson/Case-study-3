const { PubSub } = require("@google-cloud/pubsub");
const pubsub = new PubSub();

const NEW_HIRE_TOPIC = "new-hire-events";
const USER_DELETED_TOPIC = "user-deleted-events";

async function publishNewHire(data) {
  const buffer = Buffer.from(JSON.stringify(data));
  await pubsub.topic(NEW_HIRE_TOPIC).publish(buffer);
  console.log("Published new hire event:", data.email);
}

async function publishUserDeleted(email) {
  const payload = {
    email,
    timestamp: new Date().toISOString(),
  };

  await pubsub.topic(USER_DELETED_TOPIC).publishMessage({
    data: Buffer.from(JSON.stringify(payload)),
  });

  console.log("Published user deleted event:", payload);
}

module.exports = {
  publishNewHire,
  publishUserDeleted
};