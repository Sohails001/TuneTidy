"""Discogs metadata lookup - official, free API (personal access token required).

Used as a fallback after MusicBrainz finds nothing confident. Note: Discogs'
search is release-level and doesn't return per-track duration, so (unlike the
MusicBrainz path in metadata.py) this can't cross-check song length - it
relies on artist/title text similarity alone.
"""
import requests

from .metadata import _similar

SEARCH_URL = "https://api.discogs.com/database/search"
USER_AGENT = "TuneTidy/0.1.0 +https://github.com/yourname/tunetidy"


def _headers(token):
    return {"User-Agent": USER_AGENT, "Authorization": f"Discogs token={token}"}


def _get_release_track_info(release_id, title, token):
    """Look up the release's full tracklist to find this track's position and
    the release's total track count, for filling in {track}/{totaltracks}."""
    try:
        resp = requests.get(
            f"https://api.discogs.com/releases/{release_id}",
            headers=_headers(token),
            timeout=20,
        )
        data = resp.json()
    except (requests.RequestException, ValueError):
        return None, None

    tracklist = [t for t in data.get("tracklist", []) if t.get("type_", "track") == "track"]
    if not tracklist:
        return None, None

    best_pos, best_score = None, 0.0
    for t in tracklist:
        score = _similar(title, t.get("title", ""))
        if score > best_score:
            best_score, best_pos = score, t.get("position")
    return best_pos, len(tracklist)


def get_candidates(artist, title, token, limit=1):
    """Like search_by_tags(), but returns up to `limit` scored candidates for a
    human to review and pick from, instead of auto-picking the single best one."""
    if not token or not artist or not title:
        return []
    params = {"artist": artist, "track": title, "type": "release", "per_page": 5}
    try:
        resp = requests.get(SEARCH_URL, headers=_headers(token), params=params, timeout=20)
        data = resp.json()
    except (requests.RequestException, ValueError):
        return []

    results = data.get("results", []) if isinstance(data, dict) else []
    scored = []
    for r in results:
        combined = r.get("title", "")
        cand_artist = combined.split(" - ", 1)[0] if " - " in combined else ""
        scored.append((_similar(artist, cand_artist), r))
    scored.sort(key=lambda x: x[0], reverse=True)

    candidates = []
    for score, r in scored[:limit]:
        combined = r.get("title", "")
        album = combined.split(" - ", 1)[1] if " - " in combined else combined
        release_id = r.get("id")
        track_pos, total_tracks = (None, None)
        if release_id:
            track_pos, total_tracks = _get_release_track_info(release_id, title, token)
        candidates.append({
            "title": title,
            "artist": artist,
            "album": album,
            "date": str(r.get("year", "")) if r.get("year") else "",
            "track": track_pos,
            "totaltracks": total_tracks,
            "cover_url": r.get("cover_image") or r.get("thumb"),
            "_score": round(score, 2),
            "_source": "Discogs",
        })
    return candidates


def search_by_tags(artist, title, token, min_confidence=0.55):
    """Search Discogs for a release matching artist+title. Returns a metadata
    dict in the same shape as metadata.get_recording_metadata(), or None."""
    if not token or not artist or not title:
        return None

    params = {"artist": artist, "track": title, "type": "release", "per_page": 5}
    try:
        resp = requests.get(SEARCH_URL, headers=_headers(token), params=params, timeout=20)
        data = resp.json()
    except requests.RequestException as e:
        raise RuntimeError(f"Could not reach Discogs: {e}")
    except ValueError:
        raise RuntimeError("Discogs sent back a response that couldn't be read.")

    if "results" not in data:
        raise RuntimeError(f"Discogs rejected the request - {data.get('message', 'unknown error')}")

    results = data.get("results", [])
    if not results:
        return None

    # Discogs search results give a combined "Artist - Release Title" string.
    best, best_score = None, 0.0
    for r in results:
        combined = r.get("title", "")
        cand_artist = combined.split(" - ", 1)[0] if " - " in combined else ""
        score = _similar(artist, cand_artist)
        if score > best_score:
            best, best_score = r, score

    if best is None or best_score < min_confidence:
        return None  # No confident match - skip rather than mis-tag.

    combined = best.get("title", "")
    album = combined.split(" - ", 1)[1] if " - " in combined else combined
    release_id = best.get("id")

    track_pos, total_tracks = (None, None)
    if release_id:
        track_pos, total_tracks = _get_release_track_info(release_id, title, token)

    return {
        "title": title,
        "artist": artist,
        "album": album,
        "date": str(best.get("year", "")) if best.get("year") else "",
        "track": track_pos,
        "totaltracks": total_tracks,
        "cover_url": best.get("cover_image") or best.get("thumb"),
        "source": "discogs",
    }
