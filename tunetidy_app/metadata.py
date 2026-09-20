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


def get_candidates(artist, title, local_duration=None, max_duration_diff=12, limit=2):
    """Like search_by_tags(), but returns up to `limit` scored candidates for a
    human to review and pick from, instead of auto-picking the single best one."""
    if not artist or not title:
        return []
    result = mb.search_recordings(artist=artist, recording=title, limit=5)
    recs = result.get("recording-list", [])

    scored = []
    for rec in recs:
        cand_length_ms = rec.get("length")
        if local_duration is not None and cand_length_ms:
            diff = abs((float(cand_length_ms) / 1000.0) - local_duration)
            if diff > max_duration_diff:
                continue
        cand_title = rec.get("title", "")
        cand_artist = ", ".join(
            a["artist"]["name"] for a in rec.get("artist-credit", []) if isinstance(a, dict) and "artist" in a
        )
        score = (_similar(artist, cand_artist) + _similar(title, cand_title)) / 2
        scored.append((score, rec["id"]))
    scored.sort(key=lambda x: x[0], reverse=True)

    candidates = []
    for score, rec_id in scored[:limit]:
        meta = get_recording_metadata(rec_id)
        meta["_score"] = round(score, 2)
        meta["_source"] = "MusicBrainz"
        candidates.append(meta)
    return candidates


def search_by_tags(artist, title, local_duration=None, min_confidence=0.55, max_duration_diff=12):
    """Fallback lookup when fingerprinting isn't available: search MB by existing tags.

    Fetches several candidates and only accepts one whose artist AND title are
    genuinely close matches - and, when we know the local file's duration,
    whose length is actually close to it too. A song can have a very similar
    title/artist text match while being a totally different (much longer or
    shorter) recording - a live version, extended mix, radio edit, etc. - so
    duration is an independent check that catches mistakes text-matching alone
    would miss. Candidates with a wildly different duration are rejected
    outright, before text-similarity is even considered.

    max_duration_diff is in seconds. MusicBrainz doesn't always know a
    recording's length, in which case we simply can't check it and don't
    penalize the candidate for that.
    """
    if not artist or not title:
        return None

    result = mb.search_recordings(artist=artist, recording=title, limit=5)
    recs = result.get("recording-list", [])
    if not recs:
        return None

    best, best_score = None, 0.0
    for rec in recs:
        cand_length_ms = rec.get("length")
        if local_duration is not None and cand_length_ms:
            diff = abs((float(cand_length_ms) / 1000.0) - local_duration)
            if diff > max_duration_diff:
                continue  # Wrong-length recording - skip regardless of text match.

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
