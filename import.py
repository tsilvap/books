"""Import book data from books.csv into a PostgreSQL database."""
import csv
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))


def main():
    # Create table
    db.execute(
        """
        CREATE TABLE books (
            isbn    VARCHAR(10) PRIMARY KEY,
            title   VARCHAR(100) NOT NULL,
            author  VARCHAR(100) NOT NULL,
            year    INT NOT NULL
        );
        """
    )

    # Read books from books.csv and enter them into the database
    with open("books.csv") as f:
        reader = csv.reader(f)
        next(reader)  # Skip the headers
        for row in reader:
            isbn, title, author, year = row
            db.execute(
                "INSERT INTO books (isbn, title, author, year)"
                "VALUES (:isbn, :title, :author, :year)",
                {"isbn": isbn, "title": title, "author": author, "year": year},
            )
            print(f"Insert {isbn} {title} by {author} ({year}) into books.")

    # Commit commands
    db.commit()


if __name__ == "__main__":
    main()
