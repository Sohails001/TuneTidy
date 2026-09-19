"""AcoustID fingerprinting wrapper (requires the 'fpcalc' chromaprint binary on PATH,
or bundled alongside the app when packaged as an .exe)."""
import os
import sys

import acoustid


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
