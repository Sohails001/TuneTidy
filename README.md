# TuneTidy

A **free, open-source** audio auto-tagger and file organizer, inspired by TuneTidy's
functionality — automatically identify tracks, fetch metadata + cover art from
MusicBrainz/AcoustID, write proper tags, and rename/organize files into a clean folder
structure. Written from scratch in Python; not affiliated with or based on TuneTidy's
code.

## Features
- Identifies tracks via acoustic fingerprinting (AcoustID/Chromaprint), with a tag-based
  MusicBrainz search fallback when fingerprinting isn't available.
- Writes standard tags (artist, title, album, date, track number) to MP3, FLAC, M4A/MP4,
  and other formats mutagen supports.
- Downloads and embeds front cover art from the Cover Art Archive.
- Renames and organizes files using a customizable pattern, e.g.
  `{artist}/{album}/{track} - {title}`.
- Both a simple GUI (Tkinter, no extra dependencies) and a CLI for batch/scripted use.
- Dry-run mode to preview changes before touching your files.

## Setup
1. Install Python 3.9+.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. If running from source (not the prebuilt .exe), install `fpcalc` (Chromaprint) for
   fingerprinting and make sure it's on your PATH:
   - Windows/macOS/Linux builds: https://acoustid.org/chromaprint
   - Debian/Ubuntu: `sudo apt install libchromaprint-tools`
   - macOS (Homebrew): `brew install chromaprint`

   **Note:** the prebuilt Windows `.exe` (built via GitHub Actions) already has
   `fpcalc` bundled inside it — no separate install needed for that version.
4. Get a free AcoustID API key: https://acoustid.org/new-application
   Set it as an environment variable:
   ```bash
   export ACOUSTID_API_KEY=your_key_here      # macOS/Linux
   setx ACOUSTID_API_KEY "your_key_here"       # Windows
   ```
   (Fingerprinting is optional — without a key, the tool falls back to searching
   MusicBrainz using each file's existing artist/title tags.)

## Usage

### GUI
```bash
python main.py
```

### CLI
```bash
python main.py /path/to/music --dry-run
python main.py /path/to/music --pattern "{artist}/{album}/{track} - {title}"
python main.py /path/to/music --out /path/to/organized --no-cover
```

| Flag | Description |
|---|---|
| `folder` | Folder to scan (recursively) for audio files |
| `--out` | Output folder (defaults to the input folder) |
| `--api-key` | AcoustID API key (or set `ACOUSTID_API_KEY`) |
| `--pattern` | Naming pattern using `{artist} {album} {title} {track} {date}` |
| `--dry-run` | Preview changes without writing/moving anything |
| `--no-cover` | Skip downloading/embedding cover art |

## Getting a standalone Windows .exe (no install needed for end users)

This repo includes a GitHub Actions workflow (`.github/workflows/build-windows.yml`)
that automatically builds a single-file `TuneTidy.exe` on GitHub's own Windows
servers — you don't need a Windows machine or PyInstaller installed locally.

1. Push a version tag to trigger it:
   ```bash
   git tag v0.1.0
   git push origin v0.1.0
   ```
2. Go to your repo's **Actions** tab and watch the "Build Windows EXE" run finish
   (~2-3 minutes).
3. The `.exe` is attached automatically to a **GitHub Release** (under the repo's
   "Releases" section) and also uploaded as a workflow artifact. Anyone can download
   `TuneTidy.exe` and just double-click it — no Python, no installer.

You can also trigger a build manually anytime from Actions → "Build Windows EXE" →
"Run workflow", without needing a new tag.

### Building the .exe yourself on a Windows PC (optional)
```powershell
pip install -r requirements.txt
pip install pyinstaller
pyinstaller --onefile --windowed --name TuneTidy main.py
```
The .exe will appear in `dist\TuneTidy.exe`.

## License
MIT — see [LICENSE](LICENSE). Free to use, modify, and distribute.

## Disclaimer
This is an independent, from-scratch project inspired by the *idea* of automatic
audio tagging tools like TuneTidy. It shares no code with, and is not endorsed by
or affiliated with, TuneTidy or its developers. Metadata is provided by the
MusicBrainz/AcoustID community projects — please consider supporting them.
