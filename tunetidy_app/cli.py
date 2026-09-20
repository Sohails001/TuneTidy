"""Command-line interface: scan a folder, identify tracks, tag and organize them."""
import argparse
import os
import time

from mutagen import File as MutagenFile

from . import fingerprint, metadata, tagger, renamer, coverart

AUDIO_EXTS = {".mp3", ".flac", ".m4a", ".mp4", ".ogg", ".wav"}


def find_audio_files(folder):
    for root, _, files in os.walk(folder):
        for f in files:
            if os.path.splitext(f)[1].lower() in AUDIO_EXTS:
                yield os.path.join(root, f)


def process_file(path, api_key, pattern, out_dir, dry_run, no_cover, log=print):
    """Returns a dict: {"status": "tagged" | "skipped" | "error", "reason": str, "dest": str|None}."""
    log(f"Scanning: {path}")
    meta = None

    local_audio = MutagenFile(path, easy=True)
    local_duration = None
    if local_audio and getattr(local_audio, "info", None):
        local_duration = getattr(local_audio.info, "length", None)

    try:
        matches = fingerprint.identify(path, api_key)
        if matches:
            _, rec_id = matches[0]
            meta = metadata.get_recording_metadata(rec_id)
    except Exception as e:
        log(f"  Fingerprint lookup failed: {e}")

    if not meta:
        if local_audio:
            artist = (local_audio.get("artist") or [""])[0]
            title = (local_audio.get("title") or [""])[0]
            try:
                meta = metadata.search_by_tags(artist, title, local_duration=local_duration)
            except Exception as e:
                log(f"  Tag-based lookup failed: {e}")
                return {"status": "error", "reason": str(e), "dest": None}

    if not meta:
        log("  No confident match found, skipping.")
        return {"status": "skipped", "reason": "No confident match found", "dest": None}

    cover = None
    if not no_cover and meta.get("mbid_release"):
        cover = coverart.fetch_cover(meta["mbid_release"])

    try:
        tagger.write_tags(path, meta, cover)
    except Exception as e:
        log(f"  Failed to write tags: {e}")
        return {"status": "error", "reason": f"Could not write tags: {e}", "dest": None}

    ext = os.path.splitext(path)[1]
    dest = renamer.build_path(out_dir, pattern, meta, ext)
    final = renamer.move_file(path, dest, dry_run=dry_run)
    log(f"  Tagged -> {meta.get('artist')} - {meta.get('title')}")
    log(f"  {'Would move' if dry_run else 'Moved'} to: {final}")
    return {"status": "tagged", "reason": "", "dest": final}


def write_report(out_dir, results, dry_run):
    """Write a plain-text summary so skipped/errored files are easy to find and
    fix by hand, instead of having to scroll back through console output."""
    tagged = [r for r in results if r["status"] == "tagged"]
    skipped = [r for r in results if r["status"] == "skipped"]
    errors = [r for r in results if r["status"] == "error"]

    lines = [
        "TuneTidy report",
        f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"Mode: {'DRY RUN (nothing moved)' if dry_run else 'Live run'}",
        "",
        f"Tagged: {len(tagged)}   Skipped: {len(skipped)}   Errors: {len(errors)}",
        "",
    ]

    if skipped:
        lines.append("--- SKIPPED (no confident match - needs manual review) ---")
        for r in skipped:
            lines.append(f"  {r['path']}")
        lines.append("")

    if errors:
        lines.append("--- ERRORS ---")
        for r in errors:
            lines.append(f"  {r['path']}")
            lines.append(f"    reason: {r['reason']}")
        lines.append("")

    if tagged:
        lines.append("--- TAGGED ---")
        for r in tagged:
            lines.append(f"  {r['path']} -> {r['dest']}")

    report_path = os.path.join(out_dir, "tunetidy_report.txt")
    os.makedirs(out_dir, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return report_path


def main():
    p = argparse.ArgumentParser(description="TuneTidy: auto-tag and organize audio files.")
    p.add_argument("folder", help="Folder to scan for audio files")
    p.add_argument("--out", default=None, help="Output folder (default: same as input)")
    p.add_argument("--api-key", default=os.environ.get("ACOUSTID_API_KEY"), help="AcoustID API key")
    p.add_argument(
        "--pattern",
        default="{artist}/{album}/{track} - {title}",
        help="Naming pattern, e.g. '{artist}/{album}/{track} - {title}'",
    )
    p.add_argument("--dry-run", action="store_true", help="Preview changes without writing files")
    p.add_argument("--no-cover", action="store_true", help="Skip embedding cover art")
    args = p.parse_args()

    if not args.api_key:
        print("Note: no AcoustID API key set - fingerprint ID disabled, using tag-based lookup only.")

    out_dir = args.out or args.folder
    files = list(find_audio_files(args.folder))
    print(f"Found {len(files)} audio file(s).")

    results = []
    for f in files:
        outcome = process_file(f, args.api_key, args.pattern, out_dir, args.dry_run, args.no_cover)
        outcome["path"] = f
        results.append(outcome)

    report_path = write_report(out_dir, results, args.dry_run)
    tagged = sum(1 for r in results if r["status"] == "tagged")
    skipped = sum(1 for r in results if r["status"] == "skipped")
    errors = sum(1 for r in results if r["status"] == "error")
    print(f"\nDone. Tagged: {tagged}   Skipped: {skipped}   Errors: {errors}")
    print(f"Full report saved to: {report_path}")


if __name__ == "__main__":
    main()
