import requests
import json
import sqlite3
from getpass import getpass
from database import (
    authenticate_user_credentials,
    create_user_to_db,
    fetch_movies_from_db,
    fetch_user_movie_preference,
    save_movies_to_db,
    save_user_movie_preference
)
from recommender import (
    display_movies,
    fetch_from_tmdb,
    fetch_recommendations_for_movie,
    fetch_recommendations_for_user,
    fetch_similar_movies,
)


auth_action = input("Choose login or register: ").strip().lower()
if auth_action not in {"login", "register"}:
    print("Please enter 'login' or 'register'.")
    raise SystemExit(1)

user_name = input("Username: ").strip()
password = getpass("Password: ")

if not user_name or not password:
    print("Username and password cannot be empty.")
    raise SystemExit(1)

if auth_action == "register":
    user_id = create_user_to_db(user_name, password)
    if user_id is None:
        print("That username is already registered. Choose login instead.")
        raise SystemExit(1)
    print(f"Account created. Welcome, {user_name}!")
else:
    user_id = authenticate_user_credentials(user_name, password)
    if user_id is None:
        print("Invalid username or password.")
        raise SystemExit(1)
    print(f"Login successful. Welcome, {user_name}!")

user_recommendations = fetch_recommendations_for_user(user_id)
if user_recommendations:
    display_movies(user_recommendations, "YOUR RECOMMENDATIONS")
else:
    print("No cached recommendations yet. Like movies to build your suggestions.")

movie_title = input("Enter a movie title: ").strip()

if not movie_title:
    print("Movie title cannot be empty.")
    raise SystemExit(1)

#fetch from db first , then tmdb
db_response_user_search=fetch_movies_from_db(movie_title)

if db_response_user_search:
    # fetch_movies_from_db returns a one-item tuple containing the JSON text.
    response = json.loads(db_response_user_search[0])
else:
    print("no movies found in db, continuing to fetch from tmdb")
    response = fetch_from_tmdb("search/movie", {"query": movie_title})
    try:
        save_movies_to_db(movie_title, response)
    except sqlite3.Error as error:
        print(f"Could not save the search to the database: {error}")

results = response.get("results", [])

# Keep well-rated movies this user has not previously disliked.
filtered_results = [
    movie for movie in results
    if movie.get("vote_average", 0) >= 5
    and fetch_user_movie_preference(user_id, movie.get("id")) != "disliked"
]

if not filtered_results:
    print("No undisliked movies found with a rating of at least 5.")
    raise SystemExit(0)

display_movies(filtered_results, "MOVIE SEARCH RESULTS")

#ask user to select a specific numbered movie that is represented to him. 
selected_movie = None
while selected_movie is None:
    selected_id = input("Please select a movie ID: ").strip()
    selected_movie = next(
        (movie for movie in filtered_results if str(movie.get("id")) == selected_id),
        None,
    )
    if selected_movie is None:
        print("That ID is not among the movies displayed. Please try again.")

selected_movie_id = selected_movie["id"]
movie_feedback = input("Did you like this movie? (yes/no): ").strip().lower()
while movie_feedback not in {"yes", "y", "no", "n"}:
    movie_feedback = input("Please answer yes or no: ").strip().lower()

if movie_feedback in {"yes", "y"}:
    save_user_movie_preference(user_id, selected_movie_id, "liked")
    print("Fetching similar movies...")
    try:
        similar_response = fetch_similar_movies(selected_movie_id)
    except requests.exceptions.RequestException as error:
        print(f"TMDB request failed: {error}")
    else:
        similar_movies = similar_response.get("results", [])
        visible_similar_movies = [
            movie for movie in similar_movies
            if fetch_user_movie_preference(user_id, movie.get("id")) is None
        ]

        if not similar_movies:
            print("No similar movies found.")
        elif not visible_similar_movies:
            print("All similar movies were filtered because you already rated them.")
        else:
            display_movies(visible_similar_movies, "SIMILAR MOVIES")

    print("Caching recommendations for your next login...")
    try:
        fetch_recommendations_for_movie(selected_movie_id)
    except (requests.exceptions.RequestException, sqlite3.Error) as error:
        print(f"Could not cache recommendations: {error}")
else:
    save_user_movie_preference(user_id, selected_movie_id, "disliked")
    print("Preference saved. This movie will be filtered from your future search results.")