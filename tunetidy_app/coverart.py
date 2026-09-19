"""Fetch front cover art from the Cover Art Archive."""
import requests


def fetch_cover(release_mbid):
    if not release_mbid:
        return None
    url = f"https://coverartarchive.org/release/{release_mbid}/front"
    try:
        resp = requests.get(url, timeout=15, allow_redirects=True)
        if resp.status_code == 200:
            return resp.content
    except requests.RequestException:
        pass
    return None
