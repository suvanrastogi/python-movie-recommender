import os
import requests
from dotenv import load_dotenv
import textwrap
import json
from database import (
    fetch_liked_movie_ids,
    fetch_recommendations_from_db,
    fetch_similar_movies_db,
    fetch_user_movie_preference,
    save_recommendations_to_db,
    save_similar_movies_db,
)

load_dotenv()

def fetch_from_tmdb(endpoint, params=None):
    api_key = os.getenv("API_KEY")

    if not api_key:
        raise ValueError("API_KEY is missing. Check your .env file.")

    url = f"https://api.themoviedb.org/3/{endpoint}"
    request_params = {"api_key": api_key}

    if params:
        request_params.update(params)

    response = requests.get(
        url,
        params=request_params,
        timeout=(5, 20),
    )
    response.raise_for_status()
    return response.json()
def fetch_recommendations_for_movie(movie_id):
    cached_response_json = fetch_recommendations_from_db(movie_id)
    if cached_response_json is not None:
        return json.loads(cached_response_json)

    recommendation_response = fetch_from_tmdb(
        f"movie/{movie_id}/recommendations"
    )
    save_recommendations_to_db(movie_id, recommendation_response)
    return recommendation_response


def fetch_recommendations_for_user(user_id):
    recommendations_by_id = {}

    for source_movie_id in fetch_liked_movie_ids(user_id):
        cached_response_json = fetch_recommendations_from_db(source_movie_id)
        if cached_response_json is None:
            continue

        recommendation_response = json.loads(cached_response_json)

        for movie in recommendation_response.get("results", []):
            recommended_movie_id = movie.get("id")
            if recommended_movie_id is None:
                continue

            preference = fetch_user_movie_preference(user_id, recommended_movie_id)
            if preference is None:
                recommendations_by_id[recommended_movie_id] = movie

    return list(recommendations_by_id.values())

def fetch_similar_movies(movie_id):
    cached_row = fetch_similar_movies_db(movie_id)
    if cached_row:
        return json.loads(cached_row[0])

    similar_response = fetch_from_tmdb(f"movie/{movie_id}/similar")
    save_similar_movies_db(movie_id, json.dumps(similar_response))
    return similar_response

def display_movies(movies, heading):
    print("\n" + "=" * 68)
    print(f"🎬 {heading}")
    print("=" * 68)

    for index, movie in enumerate(movies, start=1):
        title = movie.get("title") or "Untitled"
        release_date = movie.get("release_date") or ""
        year = release_date[:4] if release_date else "N/A"
        rating = movie.get("vote_average")
        rating_text = f"{rating:.1f}/10" if isinstance(rating, (int, float)) else "N/A"
        vote_count = movie.get("vote_count")
        votes_text = f"{vote_count:,}" if isinstance(vote_count, int) else "N/A"
        popularity = movie.get("popularity")
        popularity_text = f"{popularity:.1f}" if isinstance(popularity, (int, float)) else "N/A"
        language = movie.get("original_language") or "N/A"
        adult = movie.get("adult")
        adult_text = "Yes" if adult is True else "No" if adult is False else "Not specified"
        overview = movie.get("overview") or "No overview available."

        print("\n" + "─" * 68)
        print(f"{index}. {title} ({year})")
        print(f"   🆔 TMDb ID: {movie.get('id', 'N/A')}")
        print(f"   ⭐ Rating: {rating_text}  |  👥 Votes: {votes_text}  |  🔥 Popularity: {popularity_text}")
        print(f"   🌍 Language: {language}  |  🔞 Adult: {adult_text}")

        original_title = movie.get("original_title")
        if original_title and original_title != title:
            print(f"   🎞️ Original title: {original_title}")

        print("   📝 Overview:")
        print(textwrap.fill(overview, width=65, initial_indent="      ", subsequent_indent="      "))

    print("\n" + "=" * 68)
