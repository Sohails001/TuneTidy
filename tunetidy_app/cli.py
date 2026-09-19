"""Command-line interface: scan a folder, identify tracks, tag and organize them."""
import argparse
import os

from mutagen import File as MutagenFile

from . import fingerprint, metadata, tagger, renamer, coverart

AUDIO_EXTS = {".mp3", ".flac", ".m4a", ".mp4", ".ogg", ".wav"}


def find_audio_files(folder):
    for root, _, files in os.walk(folder):
        for f in files:
            if os.path.splitext(f)[1].lower() in AUDIO_EXTS:
                yield os.path.join(root, f)


def process_file(path, api_key, pattern, out_dir, dry_run, no_cover, log=print):
    log(f"Scanning: {path}")
    meta = None

    try:
        matches = fingerprint.identify(path, api_key)
        if matches:
            _, rec_id, _, _ = matches[0]
            meta = metadata.get_recording_metadata(rec_id)
    except Exception as e:
        log(f"  Fingerprint lookup failed: {e}")

    if not meta:
        audio = MutagenFile(path, easy=True)
        if audio:
            artist = (audio.get("artist") or [""])[0]
            title = (audio.get("title") or [""])[0]
            try:
                meta = metadata.search_by_tags(artist, title)
            except Exception as e:
                log(f"  Tag-based lookup failed: {e}")

    if not meta:
        log("  No match found, skipping.")
        return

    cover = None
    if not no_cover and meta.get("mbid_release"):
        cover = coverart.fetch_cover(meta["mbid_release"])

    try:
        tagger.write_tags(path, meta, cover)
    except Exception as e:
        log(f"  Failed to write tags: {e}")
        return

    ext = os.path.splitext(path)[1]
    dest = renamer.build_path(out_dir, pattern, meta, ext)
    final = renamer.move_file(path, dest, dry_run=dry_run)
    log(f"  Tagged -> {meta.get('artist')} - {meta.get('title')}")
    log(f"  {'Would move' if dry_run else 'Moved'} to: {final}")


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
    for f in files:
        process_file(f, args.api_key, args.pattern, out_dir, args.dry_run, args.no_cover)


if __name__ == "__main__":
    main()
