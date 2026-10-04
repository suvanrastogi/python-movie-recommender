import json
import sqlite3
from utils import hash_password,verify_password
# ---------------------------------------------------------------------------
# Database connection
# ---------------------------------------------------------------------------
connection = sqlite3.connect("search_movie.db")
cursor = connection.cursor()
connection.execute("PRAGMA foreign_keys = ON")

# ---------------------------------------------------------------------------
# Table definitions
# ---------------------------------------------------------------------------
CREATE_SEARCHED_MOVIES_TABLE = """CREATE TABLE IF NOT EXISTS
searched_movies (
    searched_string TEXT NOT NULL UNIQUE,
    response_json TEXT NOT NULL
)
"""

CREATE_SIMILAR_MOVIES_TABLE = """CREATE TABLE IF NOT EXISTS
similar_movies (
    movie_id INTEGER UNIQUE PRIMARY KEY,
    response_json TEXT NOT NULL
)
"""

CREATE_RECOMMENDED_MOVIES_TABLE = """CREATE TABLE IF NOT EXISTS
recommended_movies (
    source_movie_id INTEGER PRIMARY KEY,
    response_json TEXT NOT NULL
)
"""

CREATE_USERS_TABLE = """CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    user_name TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL
)
"""

CREATE_USER_MOVIE_PREFERENCES_TABLE = """CREATE TABLE IF NOT EXISTS user_movie_preferences (
    user_id INTEGER NOT NULL,
    movie_id INTEGER NOT NULL,
    preference TEXT NOT NULL CHECK (preference IN ('liked', 'disliked')),
    PRIMARY KEY (user_id, movie_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
)
"""

# ---------------------------------------------------------------------------
# Create tables
# ---------------------------------------------------------------------------
cursor.execute(CREATE_SEARCHED_MOVIES_TABLE)
cursor.execute(CREATE_SIMILAR_MOVIES_TABLE)
cursor.execute(CREATE_RECOMMENDED_MOVIES_TABLE)
cursor.execute(CREATE_USERS_TABLE)
cursor.execute(CREATE_USER_MOVIE_PREFERENCES_TABLE)
connection.commit()

# ---------------------------------------------------------------------------
# User accounts and movie preferences
# ---------------------------------------------------------------------------
SAVE_USER_MOVIE_PREFERENCE_QUERY = """INSERT INTO user_movie_preferences
    (user_id, movie_id, preference)
VALUES (?, ?, ?)
ON CONFLICT(user_id, movie_id)
DO UPDATE SET preference = excluded.preference
"""

def save_user_movie_preference(user_id, movie_id, preference):
    cursor.execute(
        SAVE_USER_MOVIE_PREFERENCE_QUERY,
        (user_id, movie_id, preference),
    )
    connection.commit()


def fetch_user_movie_preference(user_id, movie_id):
    cursor.execute(
        "SELECT preference FROM user_movie_preferences "
        "WHERE user_id = ? AND movie_id = ?",
        (user_id, movie_id),
    )
    row = cursor.fetchone()
    return row[0] if row else None

def create_user_to_db(user_name, password):
    password_hash = hash_password(password)
    cursor.execute(
        "INSERT INTO users (user_name, password_hash) VALUES (?, ?) "
        "ON CONFLICT(user_name) DO NOTHING",
        (user_name, password_hash),
    )
    if cursor.rowcount == 0:
        return None

    user_id = cursor.lastrowid
    connection.commit()
    return user_id

def authenticate_user_credentials(user_name, password):
    cursor.execute(
        "SELECT user_id, password_hash FROM users WHERE user_name = ?",
        (user_name,),
    )
    user_row = cursor.fetchone()
    if user_row is None:
        return None

    try:
        password_matches = verify_password(password, user_row[1])
    except (TypeError, ValueError):
        return None

    return user_row[0] if password_matches else None
    
# ---------------------------------------------------------------------------
# Search-result cache
# ---------------------------------------------------------------------------
SAVE_SEARCH_QUERY = """
    INSERT INTO searched_movies (searched_string, response_json)
    VALUES (?, ?)
    ON CONFLICT(searched_string)
    DO UPDATE SET response_json = excluded.response_json
"""
FETCH_SEARCH_CACHE_QUERY = """
SELECT response_json FROM searched_movies WHERE searched_string = ?
"""

def save_movies_to_db(search_term, response):
    cursor.execute(
        SAVE_SEARCH_QUERY,
        (search_term, json.dumps(response))
    )
    connection.commit()


def fetch_movies_from_db(name):
    print("fetching from db:")
    cursor.execute(FETCH_SEARCH_CACHE_QUERY, (name,))
    try:
        movie = cursor.fetchone()
        if movie:
            print("movie fetched")
            return movie
        else:
            print("no movies found in db")
            return 0
    except sqlite3.Error as error:
        print(f"facing error while fetching: {error}")


# ---------------------------------------------------------------------------
# Similar-movie cache
# ---------------------------------------------------------------------------
FETCH_SIMILAR_MOVIES_QUERY = """SELECT response_json FROM similar_movies WHERE movie_id = ?
"""

def fetch_similar_movies_db(movie_id):
    print("fetching similar movies")
    cursor.execute(FETCH_SIMILAR_MOVIES_QUERY, (movie_id,))
    try:
        cached_row = cursor.fetchone()
        if cached_row:
            print("similar movie fetched")
            return cached_row
        else:
            print("no similar movies found in db")
            return 0
    except sqlite3.Error as error:
        print(f"facing error while fetching: {error}")

SAVE_SIMILAR_MOVIES_QUERY = """INSERT INTO similar_movies(movie_id, response_json)
VALUES(?,?)
ON CONFLICT(movie_id)
DO UPDATE SET response_json = excluded.response_json
"""

def save_similar_movies_db(movie_id, response_json):
    cursor.execute(SAVE_SIMILAR_MOVIES_QUERY, (movie_id, response_json))
    connection.commit()


# ---------------------------------------------------------------------------
# Personalized recommendation cache
# ---------------------------------------------------------------------------
FETCH_LIKED_MOVIE_IDS_QUERY = """SELECT movie_id
FROM user_movie_preferences
WHERE user_id = ? AND preference = ?
"""

FETCH_RECOMMENDATIONS_CACHE_QUERY = """SELECT response_json
FROM recommended_movies
WHERE source_movie_id = ?
"""

SAVE_RECOMMENDATIONS_CACHE_QUERY = """INSERT INTO recommended_movies
    (source_movie_id, response_json)
VALUES (?, ?)
ON CONFLICT(source_movie_id)
DO UPDATE SET response_json = excluded.response_json
"""


def fetch_liked_movie_ids(user_id):
    cursor.execute(FETCH_LIKED_MOVIE_IDS_QUERY, (user_id, "liked"))
    return [row[0] for row in cursor.fetchall()]


def fetch_recommendations_from_db(source_movie_id):
    cursor.execute(FETCH_RECOMMENDATIONS_CACHE_QUERY, (source_movie_id,))
    row = cursor.fetchone()
    return row[0] if row else None


def save_recommendations_to_db(source_movie_id, response):
    cursor.execute(
        SAVE_RECOMMENDATIONS_CACHE_QUERY,
        (source_movie_id, json.dumps(response)),
    )
    connection.commit()
    