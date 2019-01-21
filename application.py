import os

from flask import (
    Flask,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
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
def get_search_results(search_term):
    """Get books from database based on a search term.

    Return all books that contain search_term in their ISBN, author name
    or title, regardless of letter case.
    """
    results = db.execute(
        """
        SELECT * FROM books WHERE
            lower(isbn) LIKE :search_term
            OR lower(author) LIKE :search_term
            OR lower(title) LIKE :search_term
        """,
        {"search_term": f"%{search_term.lower()}%"},
    ).fetchall()

    return results


def username_already_in_use(username):
    """Return whether username is already in use."""
    username_in_database = db.execute(
        "SELECT username FROM users where username=:username",
        {"username": username},
    ).fetchone()
    if username_in_database:
        return True

    return False


def email_already_in_use(email):
    """Return whether email is already in use."""
    email_in_database = db.execute(
        "SELECT email FROM users where email=:email", {"email": email}
    ).fetchone()
    if email_in_database:
        return True

    return False


def valid_registration(username, email, password):
    """Return whether the username, email, and password are valid.

    Namely, it returns True if all of the parameters are non-empty, and
    if neither the username or email have already been registered
    before.
    """
    # Ensure all parameters are non-empty strings
    if len(username) * len(email) * len(password) == 0:
        return False

    if username_already_in_use(username) or email_already_in_use(email):
        return False

    return True


def register_user(username, email, password):
    """Register a new user into the database."""
    db.execute(
        "INSERT INTO users (username, email, password)"
        "VALUES (:username, :email, :password)",
        {"username": username, "email": email, "password": password},
    )
    db.commit()


# Routes
@app.route("/")
def index():
    """Index / search page."""
    search_term = request.args.get("q")
    results = None
    if search_term:
        results = get_search_results(search_term)
        for result in results:
            print(type(result))

    return render_template("index.html", results=results)


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register page."""
    if request.method == "POST":
        username, email, password = (
            str(request.form["username"]),
            str(request.form["email"]),
            str(request.form["password"]),
        )
        if valid_registration(username, email, password):
            register_user(username, email, password)
            flash("Successfully registered! You may now log in.", "success")
            return redirect(url_for("login"))
        else:
            if username_already_in_use(username):
                flash(
                    "Username already in use, please pick another.", "danger"
                )
            if email_already_in_use(email):
                flash("Email already in use, please pick another.", "danger")

            return redirect(url_for("register"))

    return render_template("register.html")


@app.route("/login")
def login():
    """Login page."""
    return render_template("login.html")
