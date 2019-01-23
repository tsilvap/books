# Books

To test this application locally, you need to set a few environment variables.
For Unix systems, the following commands suffice:

```
$ export FLASK_APP=application.py
$ export FLASK_ENV=development
```

You also need to wire up a PostgreSQL database with
`export DATABASE_URL=<your_database_url>`, and your own Goodreads API key with
`export API_KEY=<your_api_key>`.

Finally, you need to create a few tables and populate your database with the
books data. To do this, first run `python3 import.py` to populate the database,
and create the users and reviews table in your database, i.e. run
`psql $DATABASE_URL` in your shell and run the following SQL commands:

```
CREATE TABLE users (
    username VARCHAR(32) PRIMARY KEY,
    email VARCHAR(128) UNIQUE NOT NULL,
    password VARCHAR(1024)
);

CREATE TABLE reviews (
    username VARCHAR(32) REFERENCES users NOT NULL,
    isbn VARCHAR(10) REFERENCES books NOT NULL,
    review VARCHAR(10000) NOT NULL,
    date TIMESTAMP NOT NULL
);
```

Now, you can run the application with `flask run`.
