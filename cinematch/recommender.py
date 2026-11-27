"""
CineMatch Bollywood Recommendation Engine
Filters the MovieLens SQLite database for Bollywood & Indian cinema titles,
preserves all original database records, and computes honest relative match scores
combining smoothed viewer co-occurrence, genre similarity, and dataset popularity.
"""

import re
import sqlite3
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

DB_PATH = str(Path(__file__).resolve().parent / "cinematch.db")

# Verified Bollywood and Indian cinema movieIds present in cinematch.db.
# No movie titles, genres, ratings, or poster URLs are invented; only factual
# industry classification and search aliases are mapped to existing DB rows.
BOLLYWOOD_CATALOG: Dict[int, Dict[str, Any]] = {
    73881: {
        "industry": "Bollywood (Hindi)",
        "is_core_bollywood": True,
        "aliases": ["three idiots", "rajkumar hirani", "aamir khan"],
    },
    6776: {
        "industry": "Bollywood (Hindi)",
        "is_core_bollywood": True,
        "aliases": ["lagaan", "aamir khan", "ashutosh gowariker"],
    },
    57183: {
        "industry": "Bollywood (Hindi)",
        "is_core_bollywood": True,
        "aliases": ["taare zameen par", "like stars on earth", "aamir khan"],
    },
    120138: {
        "industry": "Bollywood (Hindi)",
        "is_core_bollywood": True,
        "aliases": ["pk", "pee kay", "aamir khan", "rajkumar hirani"],
    },
    146244: {
        "industry": "Bollywood (Hindi)",
        "is_core_bollywood": True,
        "aliases": ["dil to pagal hai", "dtph", "shah rukh khan", "yash chopra"],
    },
    142831: {
        "industry": "Bollywood (Hindi)",
        "is_core_bollywood": True,
        "aliases": ["garam masala", "akshay kumar", "priyadarshan"],
    },
    135777: {
        "industry": "Bollywood (Hindi)",
        "is_core_bollywood": True,
        "aliases": ["golmaal", "fun unlimited", "rohit shetty", "ajay devgn"],
    },
    134334: {
        "industry": "Bollywood (Hindi)",
        "is_core_bollywood": True,
        "aliases": ["phir hera pheri", "hera pheri", "akshay kumar"],
    },
    94661: {
        "industry": "Bollywood (Hindi)",
        "is_core_bollywood": True,
        "aliases": ["rocket singh", "ranbir kapoor"],
    },
    88069: {
        "industry": "Bollywood (Hindi)",
        "is_core_bollywood": True,
        "aliases": ["delhi belly", "imran khan"],
    },
    6244: {
        "industry": "Bollywood (Hindi)",
        "is_core_bollywood": True,
        "aliases": ["salaam bombay", "mira nair"],
    },
    171751: {
        "industry": "Bollywood (Hindi)",
        "is_core_bollywood": True,
        "aliases": ["munna bhai", "munna bhai mbbs", "sanjay dutt", "hirani"],
    },
    43333: {
        "industry": "Bollywood (Hindi)",
        "is_core_bollywood": True,
        "aliases": ["water", "deepa mehta"],
    },
    5135: {
        "industry": "Indian Cinema (Hindi/English)",
        "is_core_bollywood": False,
        "aliases": ["monsoon wedding", "mira nair"],
    },
    51884: {
        "industry": "Indian Cinema (Crossover)",
        "is_core_bollywood": False,
        "aliases": ["the namesake", "namesake", "irrfan khan", "mira nair"],
    },
    6696: {
        "industry": "Indian Cinema (Crossover)",
        "is_core_bollywood": False,
        "aliases": ["bollywood hollywood", "deepa mehta"],
    },
    31694: {
        "industry": "Indian Cinema (Crossover)",
        "is_core_bollywood": False,
        "aliases": ["bride and prejudice", "aishwarya rai", "gurinder chadha"],
    },
    1475: {
        "industry": "Indian Cinema (Historical)",
        "is_core_bollywood": False,
        "aliases": ["kama sutra", "mira nair"],
    },
    668: {
        "industry": "Indian Cinema (Classic)",
        "is_core_bollywood": False,
        "aliases": ["pather panchali", "satyajit ray", "apu trilogy"],
    },
    6918: {
        "industry": "Indian Cinema (Classic)",
        "is_core_bollywood": False,
        "aliases": ["aparajito", "unvanquished", "satyajit ray", "apu trilogy"],
    },
    670: {
        "industry": "Indian Cinema (Classic)",
        "is_core_bollywood": False,
        "aliases": ["apur sansar", "world of apu", "satyajit ray", "apu trilogy"],
    },
    139157: {
        "industry": "Indian Cinema (Tamil)",
        "is_core_bollywood": False,
        "aliases": ["massu", "suriya", "tamil"],
    },
}

BOLLYWOOD_IDS: List[int] = list(BOLLYWOOD_CATALOG.keys())
_YEAR_RE = re.compile(r"\((\d{4})\)\s*$")


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def parse_title_and_year(raw_title: str) -> Tuple[str, Optional[int]]:
    """Extract clean display title and release year from MovieLens title format."""
    if not raw_title:
        return ("Unknown", None)
    title = raw_title.strip()
    year: Optional[int] = None
    match = _YEAR_RE.search(title)
    if match:
        year = int(match.group(1))
        title = title[: match.start()].strip()
    if title.endswith(", The"):
        title = "The " + title[:-5].strip()
    elif title.endswith(", A"):
        title = "A " + title[:-3].strip()
    elif title.endswith(", An"):
        title = "An " + title[:-4].strip()
    return title, year


def parse_genres(genres_str: Optional[str]) -> List[str]:
    if not genres_str or genres_str == "(no genres listed)":
        return []
    return [g.strip() for g in genres_str.split("|") if g.strip()]


def format_rating_label(pos_count: int) -> str:
    if pos_count <= 0:
        return "No ratings recorded in dataset"
    if pos_count == 1:
        return "1 positive rating (≥ 4.0★)"
    return f"{pos_count} positive ratings (≥ 4.0★)"


def _enrich_movie_row(row: sqlite3.Row) -> Dict[str, Any]:
    mid = row["movieId"]
    raw_title = row["title"]
    display_title, release_year = parse_title_and_year(raw_title)
    genres_str = row["genres"] or ""
    genre_list = parse_genres(genres_str)
    pos_count = int(row["pos_count"] or 0)
    catalog_meta = BOLLYWOOD_CATALOG.get(mid, {})
    return {
        "movieId": mid,
        "title": raw_title,
        "display_title": display_title,
        "release_year": release_year,
        "genres": genres_str,
        "genre_list": genre_list,
        "pos_count": pos_count,
        "rating_label": format_rating_label(pos_count),
        "poster_url": None,  # cinematch.db does not store poster URLs; handled gracefully in UI
        "industry_tag": catalog_meta.get("industry", "Indian Cinema"),
        "is_core_bollywood": catalog_meta.get("is_core_bollywood", False),
    }


def get_meta() -> Dict[str, int]:
    """Return full MovieLens metadata plus verified Bollywood subset statistics."""
    conn = get_connection()
    rows = conn.execute("SELECT key, value FROM meta").fetchall()
    meta = {r["key"]: int(r["value"]) for r in rows}

    ph = ",".join("?" * len(BOLLYWOOD_IDS))
    bolly_movies = conn.execute(
        f"SELECT COUNT(*) FROM movies WHERE movieId IN ({ph})", BOLLYWOOD_IDS
    ).fetchone()[0]
    bolly_positive = conn.execute(
        f"SELECT COUNT(*) FROM positive_prefs WHERE movieId IN ({ph})", BOLLYWOOD_IDS
    ).fetchone()[0]
    bolly_users = conn.execute(
        f"SELECT COUNT(DISTINCT userId) FROM positive_prefs WHERE movieId IN ({ph})",
        BOLLYWOOD_IDS,
    ).fetchone()[0]
    bolly_rated = conn.execute(
        f"SELECT COUNT(*) FROM movie_popularity WHERE movieId IN ({ph}) AND pos_count > 0",
        BOLLYWOOD_IDS,
    ).fetchone()[0]
    conn.close()

    meta.update(
        {
            "bollywood_movies": int(bolly_movies),
            "bollywood_positive": int(bolly_positive),
            "bollywood_users": int(bolly_users),
            "bollywood_rated_movies": int(bolly_rated),
        }
    )
    return meta


def get_all_bollywood_movies() -> List[Dict[str, Any]]:
    """Return all Bollywood & Indian movies present in the database."""
    conn = get_connection()
    ph = ",".join("?" * len(BOLLYWOOD_IDS))
    rows = conn.execute(
        f"""
        SELECT m.movieId, m.title, m.genres, COALESCE(p.pos_count, 0) AS pos_count
        FROM movies m
        LEFT JOIN movie_popularity p ON m.movieId = p.movieId
        WHERE m.movieId IN ({ph})
        """,
        BOLLYWOOD_IDS,
    ).fetchall()
    conn.close()

    movies = [_enrich_movie_row(r) for r in rows]
    movies.sort(
        key=lambda m: (
            1 if m["is_core_bollywood"] else 0,
            m["pos_count"],
            m["release_year"] or 0,
        ),
        reverse=True,
    )
    return movies


def search_movies(query: str, limit: int = 22) -> List[Dict[str, Any]]:
    """Search Bollywood & Indian movies by title, alias, genre, or release year."""
    all_bolly = get_all_bollywood_movies()
    q = (query or "").strip().lower()
    if not q:
        return all_bolly[:limit]

    terms = [t for t in q.split() if t]
    matched: List[Tuple[int, Dict[str, Any]]] = []

    for movie in all_bolly:
        mid = movie["movieId"]
        aliases = " ".join(BOLLYWOOD_CATALOG.get(mid, {}).get("aliases", []))
        haystack = " ".join(
            [
                movie["title"],
                movie["display_title"],
                str(movie["release_year"] or ""),
                movie["genres"].replace("|", " "),
                movie["industry_tag"],
                aliases,
            ]
        ).lower()

        if all(term in haystack for term in terms):
            score = 0
            if movie["display_title"].lower().startswith(q):
                score += 100
            elif q in movie["display_title"].lower():
                score += 60
            if movie["is_core_bollywood"]:
                score += 20
            score += movie["pos_count"]
            matched.append((score, movie))

    matched.sort(key=lambda item: item[0], reverse=True)
    return [item[1] for item in matched[:limit]]


def get_movie_by_id(movie_id: int) -> Optional[Dict[str, Any]]:
    if movie_id not in BOLLYWOOD_CATALOG:
        return None
    conn = get_connection()
    row = conn.execute(
        """
        SELECT m.movieId, m.title, m.genres, COALESCE(p.pos_count, 0) AS pos_count
        FROM movies m
        LEFT JOIN movie_popularity p ON m.movieId = p.movieId
        WHERE m.movieId = ?
        """,
        (movie_id,),
    ).fetchone()
    conn.close()
    return _enrich_movie_row(row) if row else None


def get_movies_by_ids(movie_ids: List[int]) -> List[Dict[str, Any]]:
    valid_ids = [mid for mid in movie_ids if mid in BOLLYWOOD_CATALOG]
    if not valid_ids:
        return []
    conn = get_connection()
    ph = ",".join("?" * len(valid_ids))
    rows = conn.execute(
        f"""
        SELECT m.movieId, m.title, m.genres, COALESCE(p.pos_count, 0) AS pos_count
        FROM movies m
        LEFT JOIN movie_popularity p ON m.movieId = p.movieId
        WHERE m.movieId IN ({ph})
        """,
        valid_ids,
    ).fetchall()
    conn.close()
    by_id = {r["movieId"]: _enrich_movie_row(r) for r in rows}
    return [by_id[mid] for mid in valid_ids if mid in by_id]


def get_popular_movies(limit: int = 22) -> List[Dict[str, Any]]:
    """Return Bollywood & Indian movies sorted by positive dataset ratings."""
    movies = get_all_bollywood_movies()
    movies.sort(
        key=lambda m: (m["pos_count"], 1 if m["is_core_bollywood"] else 0, m["release_year"] or 0),
        reverse=True,
    )
    return movies[:limit]


def get_genre_distribution() -> List[Dict[str, Any]]:
    """Count Bollywood & Indian movies per genre."""
    movies = get_all_bollywood_movies()
    counts: Dict[str, int] = defaultdict(int)
    for m in movies:
        for g in m["genre_list"]:
            counts[g] += 1
    return sorted(
        [{"genre": g, "count": c} for g, c in counts.items()],
        key=lambda x: (-x["count"], x["genre"]),
    )


def recommend(
    selected_movie_ids: List[int],
    top_n: int = 10,
) -> List[Dict[str, Any]]:
    """
    Recommend Bollywood & Indian movies based on selected movies.

    Scoring combines:
    1. Smoothed viewer co-occurrence from positive_prefs (Laplace prior k=2.0 to
       avoid exaggerating 1-user overlaps into 100% certainty).
    2. Genre Jaccard similarity with the selected movies' combined genres.
    3. Dataset popularity within the Bollywood/Indian catalog.
    4. Core Bollywood (Hindi) preference over crossover classics when tied.

    Returns a Relative Match Score (0-100%), not a guaranteed probability.
    """
    selected_ids = []
    seen = set()
    for mid in selected_movie_ids:
        if mid in BOLLYWOOD_CATALOG and mid not in seen:
            selected_ids.append(mid)
            seen.add(mid)

    if not selected_ids:
        return []

    all_bolly = get_all_bollywood_movies()
    by_id = {m["movieId"]: m for m in all_bolly}
    selected_movies = [by_id[mid] for mid in selected_ids if mid in by_id]
    candidate_movies = [m for m in all_bolly if m["movieId"] not in seen]

    if not selected_movies or not candidate_movies:
        return []

    max_bolly_pop = max((m["pos_count"] for m in all_bolly), default=1) or 1

    # Selected genre profile
    selected_genres = set()
    for sm in selected_movies:
        selected_genres.update(sm["genre_list"])

    conn = get_connection()
    meta_rows = conn.execute("SELECT key, value FROM meta").fetchall()
    total_users = next((int(r["value"]) for r in meta_rows if r["key"] == "total_users"), 610)

    sel_ph = ",".join("?" * len(selected_ids))
    cand_ids = [m["movieId"] for m in candidate_movies]
    cand_ph = ",".join("?" * len(cand_ids))

    # Positive user counts for selected movies
    sel_counts = {
        r["movieId"]: int(r["cnt"])
        for r in conn.execute(
            f"""
            SELECT movieId, COUNT(DISTINCT userId) AS cnt
            FROM positive_prefs
            WHERE movieId IN ({sel_ph})
            GROUP BY movieId
            """,
            selected_ids,
        ).fetchall()
    }

    # Co-occurrence restricted strictly to Bollywood/Indian candidates
    co_rows = conn.execute(
        f"""
        SELECT
            p2.movieId AS candidate_id,
            p1.movieId AS source_id,
            COUNT(DISTINCT p1.userId) AS common_users
        FROM positive_prefs p1
        JOIN positive_prefs p2 ON p1.userId = p2.userId
        WHERE p1.movieId IN ({sel_ph})
          AND p2.movieId IN ({cand_ph})
        GROUP BY p2.movieId, p1.movieId
        HAVING common_users >= 1
        """,
        selected_ids + cand_ids,
    ).fetchall()
    conn.close()

    # Aggregate co-occurrence per candidate
    co_agg: Dict[int, Dict[str, Any]] = defaultdict(
        lambda: {
            "raw_max_conf": 0.0,
            "smoothed_non_match": 1.0,
            "best_source_id": None,
            "best_common": 0,
            "best_source_total": 0,
            "total_common_pairs": 0,
            "links": [],
        }
    )

    prior_k = 2.0  # Shrinkage factor so 1/1 overlap yields 33.3%, not 100%
    for row in co_rows:
        cid = row["candidate_id"]
        sid = row["source_id"]
        common = int(row["common_users"])
        src_total = sel_counts.get(sid, 0)
        raw_conf = common / src_total if src_total > 0 else 0.0
        smoothed_conf = common / (src_total + prior_k) if src_total > 0 else 0.0

        entry = co_agg[cid]
        entry["smoothed_non_match"] *= 1.0 - smoothed_conf
        entry["total_common_pairs"] += common
        entry["links"].append(
            {
                "source_id": sid,
                "source_title": by_id[sid]["display_title"] if sid in by_id else "",
                "common": common,
                "source_total": src_total,
                "raw_conf": raw_conf,
            }
        )
        if raw_conf > entry["raw_max_conf"] or (
            raw_conf == entry["raw_max_conf"] and common > entry["best_common"]
        ):
            entry["raw_max_conf"] = raw_conf
            entry["best_source_id"] = sid
            entry["best_common"] = common
            entry["best_source_total"] = src_total

    scored: List[Dict[str, Any]] = []
    for cand in candidate_movies:
        cid = cand["movieId"]
        cand_genres = set(cand["genre_list"])
        shared_genres = sorted(selected_genres & cand_genres)
        union_genres = selected_genres | cand_genres
        genre_sim = (len(shared_genres) / len(union_genres)) if union_genres else 0.0

        pop_norm = cand["pos_count"] / max_bolly_pop
        industry_weight = 1.0 if cand["is_core_bollywood"] else 0.65

        co = co_agg.get(cid)
        has_overlap = bool(co and co["total_common_pairs"] > 0)

        if has_overlap:
            viewer_score = 1.0 - co["smoothed_non_match"]
            match_score = (
                0.32
                + 0.38 * viewer_score
                + 0.20 * genre_sim
                + 0.05 * pop_norm
                + 0.05 * industry_weight
            )
            match_method = "Viewer Overlap + Genre Match"
            raw_conf = co["raw_max_conf"]
            support_b = cand["pos_count"] / total_users if total_users > 0 else 0.0
            lift = raw_conf / support_b if support_b > 0 else 0.0
            best_source_id = co["best_source_id"]
            best_source = by_id[best_source_id]["display_title"] if best_source_id in by_id else ""
            common_users = co["best_common"]
            source_total = co["best_source_total"]
            num_associations = len(co["links"])

            viewer_phrase = (
                f"{common_users} of {source_total} viewer"
                f"{'s' if source_total != 1 else ''} who liked {best_source} also liked this movie"
            )
            if shared_genres:
                explanation = f"{viewer_phrase}, and it shares {', '.join(shared_genres)} genre{'s' if len(shared_genres) > 1 else ''}."
            else:
                explanation = f"{viewer_phrase}."
        else:
            viewer_score = 0.0
            # Capped at <= 45% so genre-only matches never outrank genuine viewer-overlap picks
            match_score = 0.45 * (
                0.65 * genre_sim + 0.20 * pop_norm + 0.15 * industry_weight
            )
            match_method = "Genre & Popularity Match"
            raw_conf = None
            lift = None
            best_source_id = None
            best_source = None
            common_users = 0
            source_total = 0
            num_associations = 0

            if shared_genres:
                explanation = (
                    f"Recommended for shared {', '.join(shared_genres)} "
                    f"genre{'s' if len(shared_genres) > 1 else ''} "
                    "(no shared viewer likes recorded in the dataset)."
                )
            else:
                explanation = (
                    f"Included from our {cand['industry_tag']} catalog based on dataset popularity "
                    "(no direct viewer or genre overlap with your current picks)."
                )

        match_percentage = round(min(max(match_score * 100.0, 1.0), 99.0), 1)
        scored.append(
            {
                **cand,
                "match_score": round(match_score, 4),
                "match_percentage": match_percentage,
                "viewer_score_pct": round(viewer_score * 100.0, 1),
                "genre_score_pct": round(genre_sim * 100.0, 1),
                "match_method": match_method,
                "has_viewer_overlap": has_overlap,
                "confidence": round(raw_conf, 4) if raw_conf is not None else None,
                "lift": round(lift, 3) if lift is not None else None,
                "common_users": common_users,
                "source_total": source_total,
                "best_source": best_source,
                "best_source_id": best_source_id,
                "num_associations": num_associations,
                "shared_genres": shared_genres,
                "explanation": explanation,
                "is_fallback": not has_overlap,
            }
        )

    scored.sort(
        key=lambda x: (
            x["match_percentage"],
            1 if x["has_viewer_overlap"] else 0,
            x["genre_score_pct"],
            x["pos_count"],
        ),
        reverse=True,
    )

    results = scored[:top_n]
    for idx, item in enumerate(results, 1):
        item["rank"] = idx
        item["is_top_pick"] = idx == 1

    return results


def get_association_stats(movie_a: int, movie_b: int) -> Optional[Dict[str, Any]]:
    """Detailed co-occurrence stats between two specific movies."""
    conn = get_connection()
    total_users = int(
        conn.execute("SELECT value FROM meta WHERE key = 'total_users'").fetchone()[0]
    )
    count_a = int(
        conn.execute(
            "SELECT COUNT(DISTINCT userId) FROM positive_prefs WHERE movieId = ?",
            (movie_a,),
        ).fetchone()[0]
    )
    count_b = int(
        conn.execute(
            "SELECT COUNT(DISTINCT userId) FROM positive_prefs WHERE movieId = ?",
            (movie_b,),
        ).fetchone()[0]
    )
    common = int(
        conn.execute(
            """
            SELECT COUNT(DISTINCT p1.userId)
            FROM positive_prefs p1
            JOIN positive_prefs p2 ON p1.userId = p2.userId
            WHERE p1.movieId = ? AND p2.movieId = ?
            """,
            (movie_a, movie_b),
        ).fetchone()[0]
    )
    conn.close()

    if count_a == 0:
        return None

    confidence = common / count_a
    smoothed_confidence = common / (count_a + 2.0)
    support = common / total_users if total_users > 0 else 0.0
    support_b = count_b / total_users if total_users > 0 else 0.0
    lift = confidence / support_b if support_b > 0 else 0.0

    return {
        "count_a": count_a,
        "count_b": count_b,
        "common": common,
        "confidence": round(confidence, 4),
        "confidence_pct": round(confidence * 100, 1),
        "smoothed_confidence_pct": round(smoothed_confidence * 100, 1),
        "support": round(support, 4),
        "lift": round(lift, 3),
    }


if __name__ == "__main__":
    print("Bollywood movies in DB:", len(get_all_bollywood_movies()))
    print("\nRecommendations for 3 Idiots (73881) + Taare Zameen Par (57183):")
    for rec in recommend([73881, 57183], top_n=5):
        print(
            f"  #{rec['rank']} {rec['display_title']} ({rec['release_year']}) "
            f"- {rec['match_percentage']}% [{rec['match_method']}] -> {rec['explanation']}"
        )
