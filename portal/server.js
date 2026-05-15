const express = require("express");
const path = require("path");
const bodyParser = require("body-parser");
const cors = require("cors");
const { Pool } = require("pg");
const { publishNewHire } = require("./src/pubsub");

const app = express();

app.set("view engine", "ejs");
app.set("views", path.join(__dirname, "views"));

app.use(cors());
app.use(bodyParser.json());
app.use(express.urlencoded({ extended: true }));
app.use(express.static("public"));

// DATABASE CONNECTION
const pool = new Pool({
  host: process.env.DB_HOST,
  port: process.env.DB_PORT,
  user: process.env.DB_USER,
  password: process.env.DB_PASSWORD,
  database: process.env.DB_NAME,
});


// Main page (New Hire Form)
app.get("/", (req, res) => {
  res.render("index");
});

// Submit new hire
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

// Users list
app.get("/users", async (req, res) => {
  try {
    const result = await pool.query(
      "SELECT * FROM users ORDER BY created_at DESC"
    );

    res.render("users", { users: result.rows });
  } catch (err) {
    console.error("Error fetching users:", err);
    res.status(500).send("Error fetching users");
  }
});

app.listen(8080, () => {
  console.log("HR Portal running on port 8080");
});

// Fire
app.post("/delete-user", async (req, res) => {
  try {
    const { email } = req.body;

    if (!email) {
      return res.status(400).json({ error: "Email is required" });
    }

    const result = await pool.query(
      "DELETE FROM users WHERE email = $1 RETURNING *",
      [email]
    );

    if (result.rowCount === 0) {
      return res.status(404).json({ error: "User not found" });
    }

    res.json({ message: "User deleted successfully", deleted: result.rows[0] });
  } catch (err) {
    console.error("Error deleting user:", err);
    res.status(500).json({ error: "Failed to delete user" });
  }
});

app.get("/delete", (req, res) => {
  res.render("delete");
});