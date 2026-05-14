const { Pool } = require("pg");

const pool = new Pool({
  host: process.env.DB_HOST,
  port: process.env.DB_PORT,
  user: process.env.DB_USER,
  password: process.env.DB_PASSWORD,
  database: process.env.DB_NAME,
});

const express = require("express");
const path = require("path");
const { Pool } = require("pg");

const app = express();

// Enable EJS templates
app.set("view engine", "ejs");
app.set("views", path.join(__dirname, "views"));

const bodyParser = require("body-parser");
const cors = require("cors");
const { publishNewHire } = require("./src/pubsub");

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
    const result = await pool.query("SELECT * FROM users ORDER BY created_at DESC");
    res.render("users", { users: result.rows });
  } catch (err) {
    console.error("Error fetching users:", err);
    res.status(500).send("Error fetching users");
  }
});

app.listen(8080, () => {
  console.log("HR Portal running on port 8080");
});