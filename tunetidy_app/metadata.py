"""MusicBrainz metadata lookup."""
import musicbrainzngs as mb

mb.set_useragent("TuneTidy", "0.1.0", "https://github.com/yourname/tunetidy")


def get_recording_metadata(recording_id):
    result = mb.get_recording_by_id(
        recording_id, includes=["artists", "releases", "release-groups"]
    )
    rec = result["recording"]
    meta = {
        "title": rec.get("title", ""),
        "artist": ", ".join(
            a["artist"]["name"] for a in rec.get("artist-credit", []) if isinstance(a, dict) and "artist" in a
        ),
    }
    releases = rec.get("release-list", [])
    if releases:
        rel = releases[0]
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


def search_by_tags(artist, title):
    """Fallback lookup when fingerprinting isn't available: search MB by existing tags."""
    if not artist or not title:
        return None
    result = mb.search_recordings(artist=artist, recording=title, limit=1)
    recs = result.get("recording-list", [])
    if not recs:
        return None
    return get_recording_metadata(recs[0]["id"])
