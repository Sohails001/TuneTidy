"""GetSongBPM lookup for tempo (BPM) and musical key.

This replaces the Spotify "audio features" idea, since Spotify permanently
closed that endpoint to any app registered after Nov 27, 2024. GetSongBPM is
a free, currently-working, officially documented API - see https://getsongbpm.com/api

IMPORTANT: per GetSongBPM's terms of service, using this API requires visibly
crediting https://getsongbpm.com wherever this data is shown or used - this
is a condition of their free tier, not optional. Don't strip this attribution
if you modify this file. See the README for where that's noted.
"""
import requests

from .metadata import _similar

SEARCH_URL = "https://api.getsong.co/search/"


def get_bpm_and_key(artist, title, api_key, min_confidence=0.55):
    """Return {"bpm": int, "key": str, "danceability": int|None} for the
    best-matching song, or None if no confident match / no key configured."""
    if not api_key or not artist or not title:
        return None

    lookup = f"song:{title} artist:{artist}"
    params = {"api_key": api_key, "type": "both", "lookup": lookup, "limit": 5}
    try:
        resp = requests.get(SEARCH_URL, params=params, timeout=20)
        data = resp.json()
    except requests.RequestException as e:
        raise RuntimeError(f"Could not reach GetSongBPM: {e}")
    except ValueError:
        raise RuntimeError("GetSongBPM sent back a response that couldn't be read.")

    if isinstance(data, dict) and "error" in data:
        raise RuntimeError(f"GetSongBPM rejected the request - {data['error']}")

    results = data.get("search") if isinstance(data, dict) else None
    if not results or not isinstance(results, list):
        return None  # No matches (API returns a non-list "false" value for no hits).

    best, best_score = None, 0.0
    for r in results:
        if not isinstance(r, dict):
            continue
        cand_title = r.get("title", "")
        cand_artist = (r.get("artist") or {}).get("name", "")
        score = (_similar(artist, cand_artist) + _similar(title, cand_title)) / 2
        if score > best_score:
            best, best_score = r, score

    if best is None or best_score < min_confidence:
        return None

    bpm = best.get("tempo")
    if not bpm:
        return None

    try:
        bpm = int(float(bpm))
    except (TypeError, ValueError):
        return None

    return {
        "bpm": bpm,
        "key": best.get("key_of") or None,
        "danceability": best.get("danceability"),
    }
