"""Build a target path from a naming pattern and move/rename the file."""
import os
import re
import shutil

INVALID_CHARS = r'<>:"/\|?*'


def sanitize(name):
    return re.sub(f"[{re.escape(INVALID_CHARS)}]", "_", name).strip()


def build_path(base_dir, pattern, meta, ext):
    track = meta.get("track")
    fields = {
        "artist": sanitize(meta.get("artist") or "Unknown Artist"),
        "album": sanitize(meta.get("album") or "Unknown Album"),
        "title": sanitize(meta.get("title") or "Unknown Title"),
        "track": f"{int(track):02d}" if str(track or "").isdigit() else "00",
        "date": meta.get("date") or "",
    }
    rel_path = pattern.format(**fields) + ext
    # Split on both slash styles so each segment is sanitized independently
    parts = [sanitize(p) for p in re.split(r"[\\/]", rel_path)]
    return os.path.join(base_dir, *parts)


def move_file(src, dest, dry_run=False):
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    # Never silently overwrite a different existing file (e.g. two tracks that
    # both ended up numbered "00" because MusicBrainz had no track-position data).
    if os.path.exists(dest) and os.path.abspath(dest) != os.path.abspath(src):
        base, ext = os.path.splitext(dest)
        n = 2
        while os.path.exists(f"{base} ({n}){ext}"):
            n += 1
        dest = f"{base} ({n}){ext}"
    if dry_run:
        return dest
    if os.path.abspath(src) != os.path.abspath(dest):
        shutil.move(src, dest)
    return dest
