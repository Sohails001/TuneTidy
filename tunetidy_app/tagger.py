"""Write tags (and optional cover art) to an audio file using mutagen."""
import os
from mutagen import File as MutagenFile
from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3, APIC, ID3NoHeaderError
from mutagen.flac import FLAC, Picture
from mutagen.mp4 import MP4, MP4Cover


def _set(easy_tag, key, value):
    if value:
        easy_tag[key] = str(value)


def write_tags(filepath, meta, cover_bytes=None):
    ext = os.path.splitext(filepath)[1].lower()

    if ext == ".mp3":
        try:
            audio = EasyID3(filepath)
        except ID3NoHeaderError:
            audio = EasyID3()
            audio.save(filepath)
            audio = EasyID3(filepath)
        _set(audio, "artist", meta.get("artist"))
        _set(audio, "title", meta.get("title"))
        _set(audio, "album", meta.get("album"))
        _set(audio, "date", meta.get("date"))
        _set(audio, "tracknumber", meta.get("track"))
        audio.save()
        if cover_bytes:
            id3 = ID3(filepath)
            id3.delall("APIC")
            id3.add(APIC(encoding=3, mime="image/jpeg", type=3, desc="Cover", data=cover_bytes))
            id3.save()

    elif ext == ".flac":
        audio = FLAC(filepath)
        for k in ("artist", "title", "album", "date"):
            if meta.get(k):
                audio[k] = str(meta[k])
        if meta.get("track"):
            audio["tracknumber"] = str(meta["track"])
        if cover_bytes:
            audio.clear_pictures()
            pic = Picture()
            pic.data = cover_bytes
            pic.type = 3
            pic.mime = "image/jpeg"
            audio.add_picture(pic)
        audio.save()

    elif ext in (".m4a", ".mp4"):
        audio = MP4(filepath)
        if meta.get("artist"):
            audio["\xa9ART"] = meta["artist"]
        if meta.get("title"):
            audio["\xa9nam"] = meta["title"]
        if meta.get("album"):
            audio["\xa9alb"] = meta["album"]
        if meta.get("date"):
            audio["\xa9day"] = meta["date"]
        if meta.get("track"):
            try:
                audio["trkn"] = [(int(meta["track"]), int(meta.get("totaltracks") or 0))]
            except ValueError:
                pass
        if cover_bytes:
            audio["covr"] = [MP4Cover(cover_bytes, imageformat=MP4Cover.FORMAT_JPEG)]
        audio.save()

    else:
        audio = MutagenFile(filepath, easy=True)
        if audio is None:
            raise RuntimeError(f"Unsupported file type: {filepath}")
        for k in ("artist", "title", "album", "date"):
            if meta.get(k):
                audio[k] = str(meta[k])
        audio.save()
