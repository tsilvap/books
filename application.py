import os

import requests
from flask import (
    Flask,
    flash,
    jsonify,
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


def submit_review(username, isbn, review):
    """Submit a review under username."""
    if len(review) > 10000:
        return

    db.execute(
        "INSERT INTO reviews (username, isbn, review, date) "
        "VALUES (:username, :isbn, :review, :date)",
        {"username": username, "isbn": isbn, "review": review, "date": "now"},
    )
    db.commit()


def update_review(username, isbn, review):
    """Update a review under username."""
    if len(review) > 10000:
        return

    db.execute(
        "UPDATE reviews SET review=:review, date=:date "
        "WHERE username=:username AND isbn=:isbn",
        {"username": username, "isbn": isbn, "review": review, "date": "now"},
    )
    db.commit()


def get_book_by_isbn(isbn):
    """Return books row from database corresponding to a given ISBN."""
    result = db.execute(
        "SELECT * FROM books WHERE lower(isbn)=:isbn", {"isbn": isbn.lower()}
    ).fetchone()

    return result


def get_goodreads_data(isbn):
    """Return number of ratings and average rating from Goodreads."""
    res = requests.get(
        "https://www.goodreads.com/book/review_counts.json",
        params={"key": os.getenv("API_KEY"), "isbns": isbn},
    )
    book = res.json()["books"][0]

    return book["ratings_count"], book["average_rating"], book["reviews_count"]


def stars_from_rating(rating):
    """Return number of full and half stars corresponding to rating."""
    rating = float(rating)  # Convert string to float

    full_stars = int(rating)
    half_stars = 0

    fractional_part = rating - int(rating)
    if 0 <= fractional_part < 0.25:
        half_stars = 0
    elif 0.25 <= fractional_part < 0.75:
        half_stars = 1
    else:
        full_stars += 1

    return full_stars, half_stars


def user_has_reviewed(username, isbn):
    """Return whether user has already reviewed the book."""
    has_reviewed = db.execute(
        "SELECT * FROM reviews WHERE username=:username AND isbn=:isbn",
        {"username": username, "isbn": isbn},
    ).fetchone()

    return True if has_reviewed else False


def get_user_review(username, isbn):
    """Return user review of a book."""
    review = db.execute(
        "SELECT * FROM reviews WHERE username=:username AND isbn=:isbn",
        {"username": username, "isbn": isbn},
    ).fetchone()

    return review


def get_user_reviews(isbn):
    """Get user reviews for a given book."""
    reviews = db.execute(
        "SELECT * FROM reviews WHERE isbn=:isbn", {"isbn": isbn}
    ).fetchall()

    return reviews


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
        "INSERT INTO users (username, email, password) "
        "VALUES (:username, :email, :password)",
        {"username": username, "email": email, "password": password},
    )
    db.commit()


def valid_credentials(username_or_email, password):
    """Return whether a user/email and password combination is valid."""
    if "@" in username_or_email:  # email
        user = db.execute(
            "SELECT * FROM users WHERE email=:email AND password=:password",
            {"email": username_or_email, "password": password},
        ).fetchone()
    else:  # username
        user = db.execute(
            "SELECT * FROM users "
            "WHERE username=:username AND password=:password",
            {"username": username_or_email, "password": password},
        ).fetchone()

    return True if user else False


def get_username(email):
    """Return username for a registered email."""
    username = db.execute(
        "SELECT username FROM users WHERE email=:email", {"email": email}
    ).fetchone()[0]

    return username


# Routes
@app.route("/")
def index():
    """Index / search page."""
    search_term = request.args.get("q")
    results = None
    if search_term:
        results = get_search_results(search_term)

    return render_template("index.html", results=results)


@app.route("/book/<string:isbn>", methods=["GET", "POST"])
def book(isbn):
    """Book / review page."""
    if request.method == "POST":
        username = session["username"]
        if username:
            if not user_has_reviewed(username, isbn):
                submit_review(username, isbn, request.form["review"])
            else:
                update_review(username, isbn, request.form["review"])

        return redirect(url_for("book", isbn=isbn))

    book = get_book_by_isbn(isbn)
    if book is None:
        return render_template("not_found.html"), 404

    # Get Goodreads data
    ratings_count, average_rating = get_goodreads_data(book["isbn"])[0:2]
    full_stars, half_stars = stars_from_rating(average_rating)

    # Get user reviews
    user_reviews = get_user_reviews(isbn)

    # Determine if user has already reviewed the book
    has_reviewed = None
    user_review = None
    username = session["username"]
    if username:
        has_reviewed = user_has_reviewed(username, isbn)
        if has_reviewed:
            user_review = get_user_review(username, isbn)

    return render_template(
        "book.html",
        book=book,
        ratings_count=ratings_count,
        full_stars=full_stars,
        half_stars=half_stars,
        has_reviewed=has_reviewed,
        user_review=user_review,
        user_reviews=user_reviews,
    )


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

        if username_already_in_use(username):
            flash("Username already in use, please pick another.", "danger")

        if email_already_in_use(email):
            flash("Email already in use, please pick another.", "danger")

        return redirect(url_for("register"))

    else:
        return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Login page."""
    if request.method == "POST":
        username_or_email, password = (
            str(request.form["user-or-email"]),
            str(request.form["password"]),
        )

        if valid_credentials(username_or_email, password):
            username = ""
            if "@" in username_or_email:  # email
                username = get_username(username_or_email)
            else:
                username = username_or_email

            session["username"] = username
            return redirect(url_for("index"))

        flash("Invalid username/email and password combination.", "danger")
        return redirect(url_for("login"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    """Log out."""
    session["username"] = ""
    return redirect(url_for("index"))


@app.route("/api/<string:isbn>")
def api(isbn):
    """Books JSON API."""
    book = get_book_by_isbn(isbn)
    if book is None:
        return render_template("not_found.html"), 404

    average_rating, review_count = get_goodreads_data(book["isbn"])[1:]
    response = {
        "title": book["title"],
        "author": book["author"],
        "year": book["year"],
        "isbn": book["isbn"],
        "review_count": review_count,
        "average_score": float(average_rating),
    }

    return jsonify(response)
