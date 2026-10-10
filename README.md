# TuneTidy

![License](https://img.shields.io/github/license/Sohails001/TuneTidy)
![Release](https://img.shields.io/github/v/release/Sohails001/TuneTidy?include_prereleases)
![Build](https://img.shields.io/github/actions/workflow/status/Sohails001/TuneTidy/build-windows.yml?branch=main&label=Windows%20build)
![Platform](https://img.shields.io/badge/platform-Windows-0078D6)
![Python](https://img.shields.io/badge/python-3.11-blue)

**Free, open-source audio auto-tagger and file organizer for Windows.** Identifies
your tracks (by audio fingerprint or existing tags), fetches metadata and cover
art from MusicBrainz/Discogs, adds BPM/key, and renames/organizes your files —
with a review step so you choose the right match before anything is touched.

Not affiliated with AudioRanger, OneTagger, or any other commercial tagger —
built from scratch.

---

### Contents
[Screenshots](#screenshots) ·
[Download](#download) ·
[Features](#features) ·
[Quick Start](#quick-start) ·
[Configuration](#configuration) ·
[Building from Source](#building-from-source) ·
[Project Layout](#project-layout) ·
[Known Limitations](#known-limitations) ·
[License](#license)

---

## Screenshots

📸 *Add a screenshot of the main window and the review screen here.*
Drag a `.png` into this README on GitHub's web editor (Edit → drop image into the
text box) and it'll generate the right markdown automatically, e.g.:
```markdown
![Main window](docs/screenshot-main.png)
![Review screen](docs/screenshot-review.png)
```

## Download

Grab the latest `TuneTidy.exe` from the [Releases page](../../releases/latest) —
no installation, no Python required, just run it.

*(To publish a release: push a tag like `v1.0.0`, which triggers the GitHub
Actions build and attaches the exe automatically — see
[Building from Source](#building-from-source).)*

## Features

- **Review before applying** — scans first, shows you a few candidate matches
  per song, you pick the right one (or skip it) before anything is written.
- **Multiple sources** — audio fingerprinting (AcoustID), MusicBrainz, and
  Discogs as a fallback, so more obscure tracks still get found.
- **BPM & musical key** — via GetSongBPM, added as real tags.
- **Cover art** — fetched automatically, with a choice of resolution
  (250px / 500px / 1200px / original).
- **Safe by default** — dry-run mode previews every change; never silently
  overwrites a different file; full tagged/skipped/error report after each run.
- **No installation hassle** — the Windows build bundles everything it needs,
  including the fingerprinting tool, into one `.exe`.

## Quick Start

1. Download `TuneTidy.exe` from [Releases](../../releases/latest).
2. Run it. No install, no Python needed.
3. (Optional but recommended) Get free API keys — see [Configuration](#configuration).
4. Point it at your music folder → **Scan for Matches** → review and pick the
   right match for each song → **Apply All & Tag Files**.

## Configuration

All of these are optional — TuneTidy works with none of them set, just with
fewer/lower-confidence matches.

| Service | Used for | Get a free key |
|---|---|---|
| AcoustID | Audio fingerprint identification | [acoustid.org/new-application](https://acoustid.org/new-application) |
| Discogs | Fallback metadata source | [discogs.com/settings/developers](https://www.discogs.com/settings/developers) |
| GetSongBPM | BPM & musical key tags | [getsongbpm.com/api](https://getsongbpm.com/api) |

Paste keys directly into the app, or set them as environment variables
(`ACOUSTID_API_KEY`, `DISCOGS_TOKEN`, `GETSONGBPM_API_KEY`) to avoid re-entering
them each time.

> GetSongBPM's free tier requires crediting them wherever their data is shown —
> this project does that here: BPM/key data via [GetSongBPM](https://getsongbpm.com).

## Building from Source

```bash
git clone https://github.com/Sohails001/TuneTidy.git
cd TuneTidy
pip install -r requirements.txt
python main.py          # launches the GUI
python main.py --help   # CLI mode options
```

To build your own `.exe`: push a version tag (`git tag v1.0.0 && git push origin v1.0.0`)
or trigger **Actions → Build Windows EXE → Run workflow** manually. The build
downloads and bundles `fpcalc` (Chromaprint) automatically — nothing to install
by hand.

## Project Layout

```
TuneTidy/
├── main.py                 # entry point (GUI or CLI)
├── requirements.txt
├── tunetidy_app/
│   ├── gui.py               # Tkinter UI (scan → review → apply)
│   ├── cli.py                # scan/match/apply orchestration
│   ├── fingerprint.py       # AcoustID fingerprinting
│   ├── metadata.py           # MusicBrainz lookup + matching
│   ├── discogs.py            # Discogs fallback source
│   ├── getsongbpm.py         # BPM/key lookup
│   ├── tagger.py              # writes tags to MP3/FLAC/M4A/etc.
│   ├── renamer.py            # builds output paths, avoids overwrites
│   └── coverart.py           # cover art fetching, multiple sizes
└── .github/workflows/
    └── build-windows.yml     # builds the self-contained .exe via CI
```

## Known Limitations

- Fingerprint coverage depends on AcoustID's community database — some obscure
  tracks/edits won't be found by fingerprint and fall back to text search.
  This is a free-database limitation, not a bug.
- Discogs search doesn't expose per-track duration, so that fallback can't
  cross-check song length the way the MusicBrainz path does.
- Windows only, for now (the GitHub Actions build targets `windows-latest`).

## Contributing

Bug reports, feature ideas, and pull requests are welcome — see
[CONTRIBUTING.md](CONTRIBUTING.md).

## License

[MIT](LICENSE) © Sohail Sher Ali and TuneTidy contributors. Free to use,
modify, and distribute.

TuneTidy is an independent project and is not affiliated with or endorsed by
AudioRanger, OneTagger, or any other commercial tagger. Product names are used
only to describe compatibility/comparison.

---

Created by **Sohail Sher Ali** · If TuneTidy is useful to you, a ⭐ helps others find it.
