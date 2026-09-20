"""AcoustID fingerprinting wrapper.

Calls the 'fpcalc' binary directly via subprocess (with a hard timeout, so a
broken/misconfigured fpcalc can never freeze the app), then talks to the
AcoustID lookup API with `requests` so we get the real error message back
instead of a vague generic failure.
"""
import json
import os
import subprocess
import sys
import time

import requests

LOOKUP_URL = "https://api.acoustid.org/v2/lookup"

# AcoustID asks clients to stay under ~3 requests/second.
_MIN_INTERVAL = 0.34
_last_call_time = 0.0

# How long to wait for fpcalc before giving up on a single file, rather than
# hanging forever (e.g. if fpcalc can't start due to a missing dependency).
_FPCALC_TIMEOUT_SECONDS = 30


def _fpcalc_path():
    """Prefer the copy bundled inside the packaged .exe, if present."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        bundled = os.path.join(sys._MEIPASS, "fpcalc.exe")
        if os.path.exists(bundled):
            return bundled
    return os.environ.get("FPCALC", "fpcalc")


def _run_fpcalc(filepath):
    exe = _fpcalc_path()
    try:
        result = subprocess.run(
            [exe, "-json", filepath],
            capture_output=True,
            text=True,
            timeout=_FPCALC_TIMEOUT_SECONDS,
        )
    except FileNotFoundError:
        raise RuntimeError("chromaprint 'fpcalc' not found. Install it and ensure it's on PATH.")
    except subprocess.TimeoutExpired:
        raise RuntimeError(
            "fpcalc did not respond within 30 seconds and was stopped - it may be "
            "missing a required file to run correctly."
        )

    if result.returncode != 0:
        detail = (result.stderr or "").strip() or "unknown error"
        raise RuntimeError(f"fpcalc could not analyze this file: {detail}")

    try:
        data = json.loads(result.stdout)
    except ValueError:
        raise RuntimeError("fpcalc produced a response that couldn't be read.")

    return data.get("duration"), data.get("fingerprint")


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

    duration, fp = _run_fpcalc(filepath)
    if not fp or not duration:
        raise RuntimeError("Could not generate an audio fingerprint for this file.")

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
