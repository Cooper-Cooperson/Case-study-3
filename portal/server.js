const express = require("express");
const bodyParser = require("body-parser");
const cors = require("cors");
const { publishNewHire } = require("./src/pubsub");

const app = express();
app.use(cors());
app.use(bodyParser.json());
app.use(express.static("public"));

app.post("/submit", async (req, res) => {
  try {
    const { name, email, department, role } = req.body;

    await publishNewHire({
      name,
      email,
      department,
      role,
      status: "NEW"
    });

    res.json({ message: "New hire submitted successfully" });
  } catch (err) {
    console.error("Error submitting new hire:", err);
    res.status(500).json({ error: "Failed to submit new hire" });
  }
});

app.get("/users", async (req, res) => {
  try {
    const client = await pool.connect();
    const result = await client.query("SELECT id, name, email, department, role, status, created_at FROM users ORDER BY created_at DESC");
    client.release();

    res.render("users", { users: result.rows });
  } catch (err) {
    console.error("Error fetching users:", err);
    res.status(500).send("Error fetching users");
  }
});

app.listen(8080, () => {
  console.log("HR Portal running on port 8080");
});