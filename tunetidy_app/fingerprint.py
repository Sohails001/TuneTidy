"""AcoustID fingerprinting wrapper (requires the 'fpcalc' chromaprint binary on PATH)."""
import acoustid


def identify(filepath, api_key):
    """Return a list of (score, recording_id, title, artist) matches for a file."""
    if not api_key:
        return []
    try:
        results = list(acoustid.match(api_key, filepath))
    except acoustid.NoBackendError:
        raise RuntimeError("chromaprint 'fpcalc' not found. Install it and ensure it's on PATH.")
    except acoustid.FingerprintGenerationError:
        raise RuntimeError("Could not generate an audio fingerprint for this file.")
    except acoustid.WebServiceError as e:
        raise RuntimeError(f"AcoustID web service error: {e}")
    return results
