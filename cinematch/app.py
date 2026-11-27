from flask import Flask, jsonify, render_template, request
from recommender import (
    get_all_bollywood_movies,
    get_association_stats,
    get_genre_distribution,
    get_meta,
    get_movies_by_ids,
    get_popular_movies,
    recommend,
    search_movies,
)

app = Flask(__name__)


@app.route("/")
def home():
    meta = get_meta()
    bollywood_movies = get_all_bollywood_movies()
    return render_template(
        "index.html",
        meta=meta,
        bollywood_movies=bollywood_movies,
        page="home",
    )


@app.route("/analytics")
def analytics():
    popular = get_popular_movies(22)
    genres = get_genre_distribution()
    meta = get_meta()
    return render_template(
        "analytics.html",
        popular=popular,
        genres=genres,
        meta=meta,
        page="analytics",
    )


@app.route("/insights")
def insights():
    meta = get_meta()
    example_idiots_pk = get_association_stats(73881, 120138)
    example_lagaan_monsoon = get_association_stats(6776, 5135)
    return render_template(
        "insights.html",
        meta=meta,
        example_idiots_pk=example_idiots_pk,
        example_lagaan_monsoon=example_lagaan_monsoon,
        page="insights",
    )


@app.route("/about")
def about():
    meta = get_meta()
    return render_template("about.html", meta=meta, page="about")


@app.route("/api/bollywood")
def api_bollywood():
    movies = get_all_bollywood_movies()
    return jsonify({"movies": movies, "total": len(movies)})


@app.route("/api/search")
def api_search():
    q = request.args.get("q", "")
    try:
        limit = max(1, min(int(request.args.get("limit", 15)), 50))
    except ValueError:
        limit = 15
    results = search_movies(q, limit)
    return jsonify({"results": results, "query": q.strip(), "count": len(results)})


@app.route("/api/recommend")
def api_recommend():
    movies_param = request.args.get("movies", "")
    try:
        top_n = max(1, min(int(request.args.get("top_n", 10)), 22))
    except ValueError:
        top_n = 10

    try:
        ids = [int(x.strip()) for x in movies_param.split(",") if x.strip()]
    except ValueError:
        return jsonify({"error": "Invalid movie IDs provided."}), 400

    if not ids:
        return jsonify(
            {
                "recommendations": [],
                "selected_movies": [],
                "selected_count": 0,
                "has_viewer_overlap": False,
                "fallback": True,
                "message": "Please select at least one Bollywood movie to get recommendations.",
            }
        )

    selected_movies = get_movies_by_ids(ids)
    if not selected_movies:
        return jsonify(
            {
                "error": "None of the selected movie IDs belong to the Bollywood/Indian catalog.",
                "recommendations": [],
                "selected_movies": [],
                "selected_count": 0,
            }
        ), 400

    recs = recommend(ids, top_n=top_n)
    has_overlap = any(r.get("has_viewer_overlap") for r in recs)

    return jsonify(
        {
            "recommendations": recs,
            "selected_movies": selected_movies,
            "selected_count": len(selected_movies),
            "has_viewer_overlap": has_overlap,
            "fallback": not has_overlap,
            "scoring_note": (
                "Match percentages are relative recommendation scores (0–100%), "
                "not guaranteed probabilities that you will like a movie. They combine "
                "smoothed viewer co-occurrence in the dataset, genre similarity, and "
                "dataset popularity."
            ),
        }
    )


if __name__ == "__main__":
    app.run(debug=True, port=5000)
