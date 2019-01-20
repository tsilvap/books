import os

from flask import Flask, render_template, request, session
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

app = Flask(__name__)

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

# Helper functions
def valid_registration(username, email):
    """Return whether the username or the email are not already in the database."""
    if (
        db.execute(
            "SELECT * FROM users WHERE username=:username OR email=:email",
            {"username": username, "email": email},
        ).fetchone()
        is not None
    ):
        return False

    return True


def register_user(username, email, password):
    """Register a new user into the database."""
    db.execute(
        "INSERT INTO users (username, email, password) VALUES (:username, :email, :password)",
        {"username": username, "email": email, "password": password},
    )
    db.commit()


# Routes
@app.route("/")
def index():
    """Index page."""
    return render_template("index.html.j2")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register page."""
    if request.method == "POST":
        username, email, password = (
            request.form["username"],
            request.form["email"],
            request.form["password"],
        )
        if valid_registration(username, email):
            register_user(username, email, password)
            return render_template("register.html.j2")
        else:
            pass  # FIXME: Implement this.

    return render_template("register.html.j2")


@app.route("/login")
def login():
    """Login page."""
    return render_template("login.html.j2")
