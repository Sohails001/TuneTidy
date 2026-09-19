"""AcoustID fingerprinting wrapper.

Uses pyacoustid/chromaprint only to generate the local audio fingerprint (which
calls the bundled or system 'fpcalc' binary), then talks to the AcoustID lookup
API directly with `requests` so we can surface the real error message the API
sends back - pyacoustid's own lookup() swallows this into an unhelpful generic
"status: error" with no detail, which makes real problems (bad API key, rate
limiting, etc.) impossible to diagnose.
"""
import os
import sys
import time

import acoustid
import requests

LOOKUP_URL = "https://api.acoustid.org/v2/lookup"

# AcoustID asks clients to stay under ~3 requests/second.
_MIN_INTERVAL = 0.34
_last_call_time = 0.0


def _use_bundled_fpcalc_if_present():
    """When running as a PyInstaller --onefile exe, fpcalc.exe is bundled inside
    and extracted to a temp folder at startup (sys._MEIPASS). Point pyacoustid at
    it via the FPCALC env var so users don't need to install anything separately.
    """
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        bundled = os.path.join(sys._MEIPASS, "fpcalc.exe")
        if os.path.exists(bundled):
            os.environ["FPCALC"] = bundled


_use_bundled_fpcalc_if_present()


def _throttle():
    global _last_call_time
    elapsed = time.time() - _last_call_time
    if elapsed < _MIN_INTERVAL:
        time.sleep(_MIN_INTERVAL - elapsed)
    _last_call_time = time.time()


def identify(filepath, api_key):
    """Return a list of (score, recording_id) matches for a file, best first."""
    if not api_key:
        return []

    try:
        duration, fp = acoustid.fingerprint_file(filepath)
    except acoustid.NoBackendError:
        raise RuntimeError("chromaprint 'fpcalc' not found. Install it and ensure it's on PATH.")
    except acoustid.FingerprintGenerationError as e:
        raise RuntimeError(f"Could not generate an audio fingerprint for this file: {e}")

    _throttle()
    params = {
        "client": api_key,
        "duration": int(duration),
        "fingerprint": fp,
        "meta": "recordings",
        "format": "json",
    }
    try:
        resp = requests.post(LOOKUP_URL, data=params, timeout=20)
        data = resp.json()
    except requests.RequestException as e:
        raise RuntimeError(f"Could not reach the AcoustID service: {e}")
    except ValueError:
        raise RuntimeError("AcoustID sent back a response that couldn't be read.")

    if data.get("status") != "ok":
        msg = (data.get("error") or {}).get("message", "no further detail given")
        raise RuntimeError(f"AcoustID rejected the request - {msg}")

    results = []
    for r in data.get("results", []):
        score = r.get("score", 0)
        recordings = r.get("recordings") or []
        for rec in recordings:
            rec_id = rec.get("id")
            if rec_id:
                results.append((score, rec_id))
    results.sort(key=lambda x: x[0], reverse=True)
    return results
