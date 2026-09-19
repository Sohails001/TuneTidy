"""MusicBrainz metadata lookup, with safeguards against picking the wrong match."""
import difflib
import re

import musicbrainzngs as mb

mb.set_useragent("TuneTidy", "0.1.0", "https://github.com/yourname/tunetidy")


def _normalize(s):
    """Lowercase, strip punctuation/feat-credits, collapse whitespace, for fuzzy comparison."""
    s = (s or "").lower()
    s = re.sub(r"\(feat\.?.*?\)|\bfeat\.?.*", "", s)
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _similar(a, b):
    return difflib.SequenceMatcher(None, _normalize(a), _normalize(b)).ratio()


def get_recording_metadata(recording_id):
    result = mb.get_recording_by_id(
        recording_id, includes=["artists", "releases", "media"]
    )
    rec = result["recording"]
    meta = {
        "title": rec.get("title", ""),
        "artist": ", ".join(
            a["artist"]["name"] for a in rec.get("artist-credit", []) if isinstance(a, dict) and "artist" in a
        ),
    }
    releases = rec.get("release-list", [])
    if not releases:
        return meta

    # Prefer an officially released studio release over live albums, compilations,
    # bootlegs, etc. Among equally-"official" candidates, prefer the earliest date
    # (closest to the original release rather than a later reissue/compilation).
    def sort_key(r):
        is_official = r.get("status", "").lower() == "official"
        date = r.get("date", "") or "9999"
        return (0 if is_official else 1, date)

    rel = sorted(releases, key=sort_key)[0]

    meta["album"] = rel.get("title", "")
    meta["date"] = (rel.get("date", "") or "")[:4]
    meta["mbid_release"] = rel.get("id", "")
    for medium in rel.get("medium-list", []):
        for track in medium.get("track-list", []):
            if track.get("recording", {}).get("id") == recording_id:
                meta["track"] = track.get("position", "")
                meta["totaltracks"] = medium.get("track-count", "")
                meta["disc"] = medium.get("position", "")
    return meta


def search_by_tags(artist, title, min_confidence=0.55):
    """Fallback lookup when fingerprinting isn't available: search MB by existing tags.

    Fetches several candidates and only accepts one whose artist AND title are
    genuinely close matches to what was searched for, instead of blindly trusting
    the #1 result (which can otherwise return a completely unrelated song).
    """
    if not artist or not title:
        return None

    result = mb.search_recordings(artist=artist, recording=title, limit=5)
    recs = result.get("recording-list", [])
    if not recs:
        return None

    best, best_score = None, 0.0
    for rec in recs:
        cand_title = rec.get("title", "")
        cand_artist = ", ".join(
            a["artist"]["name"] for a in rec.get("artist-credit", []) if isinstance(a, dict) and "artist" in a
        )
        score = (_similar(artist, cand_artist) + _similar(title, cand_title)) / 2
        if score > best_score:
            best, best_score = rec, score

    if best is None or best_score < min_confidence:
        return None  # No confident match - better to skip than to mis-tag the file.

    return get_recording_metadata(best["id"])
