#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import requests
import subprocess
import logging
import time
import random
import datetime
import shutil

from pytubefix import YouTube, Playlist, Channel
from pytubefix.cli import on_progress

# ----------------------------------
# Logging
# ----------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# ----------------------------------
# Helpers
# ----------------------------------
def sanitize_filename(name: str) -> str:
    name = re.sub(r'[\\/*?:"<>|]+', "_", name or "").strip()
    return re.sub(r"\s+", " ", name)

def create_requests_session():
    from requests.adapters import HTTPAdapter
    from requests.packages.urllib3.util.retry import Retry
    session = requests.Session()
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "HEAD"]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update(
        {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/123.0 Safari/537.36"}
    )
    return session

def download_thumbnail(url: str, filename: str):
    sess = create_requests_session()
    try:
        r = sess.get(url, timeout=20)
        if r.status_code == 200:
            with open(filename, "wb") as f:
                f.write(r.content)
            logging.info(f"Thumbnail downloaded: {filename}")
        else:
            logging.error(f"Failed to download thumbnail. HTTP {r.status_code}")
    except Exception as e:
        logging.error(f"Thumbnail download error: {e}")

def extract_chapter_info(filename: str) -> str:
    pattern = re.search(r"(Bab \d+\s*[^(]+)(?=\s*\(Audiobook)", filename)
    if pattern:
        chapter_info = pattern.group(1).strip().rstrip(".")
        chapter_info = re.sub(r"Bab (\d+)", lambda m: f"{int(m.group(1)):02d}", chapter_info)
        return " ".join(chapter_info.split())
    return "NO RENAME - " + filename

def make_yt(url: str, client: str | None = None) -> YouTube:
    kwargs = dict(on_progress_callback=on_progress, use_oauth=True, allow_oauth_cache=True)
    if client:
        kwargs["client"] = client  # pytubefix supports client override (e.g., "ANDROID")
    return YouTube(url, **kwargs)

def looks_like_cipher_error(msg: str) -> bool:
    if not msg:
        return False
    msg = msg.lower()
    return any(
        k in msg for k in [
            "get_initial_function_name",
            "cipher", "signature",
            "base.js", "player_ias", "decrypt", "throttling", "js"
        ]
    )

# ----------------------------------
# Audio-only (with cover & metadata)
# ----------------------------------
def download_youtube_audio(url: str, artist: str, year: str, album: str):
    max_retries = 3
    last_err = None

    for attempt in range(1, max_retries + 1):
        try:
            yt = make_yt(url)
            logging.info(f"Downloading m4a audio... (Attempt {attempt})")

            audio_stream = (
                yt.streams.filter(only_audio=True, mime_type="audio/mp4")
                .order_by("abr").desc().first()
                or yt.streams.get_audio_only("m4a")
                or yt.streams.filter(only_audio=True).order_by("abr").desc().first()
            )
            if not audio_stream:
                raise RuntimeError("No audio stream available.")

            temp_audio = audio_stream.download()
            base, ext = os.path.splitext(temp_audio)

            audio_file = base + ".m4a"
            if ext.lower() != ".m4a":
                logging.info(f"Transcoding {ext} -> .m4a")
                subprocess.run(
                    ["ffmpeg", "-y", "-i", temp_audio, "-c:a", "aac", "-b:a", "192k", audio_file],
                    check=True
                )
                os.remove(temp_audio)
            else:
                audio_file = temp_audio

            thumb_file = base + "_thumb.png"
            download_thumbnail(yt.thumbnail_url, thumb_file)

            with_cover = base + "_with_cover.m4a"
            subprocess.run(
                ["ffmpeg", "-y",
                 "-i", audio_file, "-i", thumb_file,
                 "-map", "0", "-map", "1",
                 "-c", "copy",
                 "-disposition:v", "attached_pic",
                 "-metadata:s:v", "title=Album cover",
                 "-metadata:s:v", "comment=Cover (front)",
                 with_cover],
                check=True
            )

            inferred_title = extract_chapter_info(os.path.basename(base))
            safe_title = sanitize_filename(inferred_title)
            output_file = f"{safe_title}.m4a"
            subprocess.run(
                ["ffmpeg", "-y",
                 "-i", with_cover,
                 "-c", "copy",
                 "-metadata", f"title={safe_title}",
                 "-metadata", f"artist={artist}",
                 "-metadata", f"date={year}",
                 "-metadata", f"album={album}",
                 output_file],
                check=True
            )

            for p in [thumb_file, with_cover]:
                if os.path.exists(p):
                    os.remove(p)
            if os.path.exists(audio_file) and audio_file != output_file:
                os.remove(audio_file)

            logging.info(f"Done: {output_file}")
            return

        except Exception as e:
            last_err = e
            msg = str(e)
            logging.error(f"Audio error {url} (Attempt {attempt}): {msg}")
            if looks_like_cipher_error(msg):
                logging.info("Cipher/JS parse issue detected; falling back to yt-dlp for audio.")
                return download_audio_with_ytdlp(url, artist, year, album)
            if attempt < max_retries:
                time.sleep((2 ** (attempt - 1)) + random.random())

    raise RuntimeError(f"Failed to download audio after {max_retries} attempts: {last_err}")

# ----------------------------------
# yt-dlp fallbacks
# ----------------------------------
def ensure_tool(tool: str) -> bool:
    return shutil.which(tool) is not None

def download_video_with_ytdlp(url: str, output_file: str, preferred_height: int = 1080):
    """
    Use yt-dlp to get best MP4 at <=preferred_height with best m4a, merged to output_file.
    """
    if not ensure_tool("yt-dlp"):
        raise RuntimeError("yt-dlp not found in PATH. Install it to enable fallback.")
    # Build format string: prefer mp4 video <=height + m4a, else best mp4 fallback
    fmt = f"bestvideo[ext=mp4][height<={preferred_height}]+bestaudio[ext=m4a]/best[ext=mp4][height<={preferred_height}]/best"
    tmp_template = output_file.rsplit(".", 1)[0] + ".%(ext)s"
    cmd = [
        "yt-dlp",
        "-f", fmt,
        "-o", tmp_template,
        "--merge-output-format", "mp4",
        "--no-continue",
        "--no-part",
        "--newline",
        url,
    ]
    logging.info("yt-dlp fallback running...")
    subprocess.run(cmd, check=True)
    # yt-dlp will output the final mp4 at tmp_template with ext mp4
    final_guess = tmp_template.replace("%(ext)s", "mp4")
    # If yt-dlp picked a different exact name, try to locate newest mp4 in cwd as a last resort
    if not os.path.exists(final_guess):
        # don't be destructive; search for a close match
        candidates = [f for f in os.listdir(".") if f.endswith(".mp4")]
        if candidates:
            final_guess = max(candidates, key=lambda p: os.path.getmtime(p))
    if final_guess != output_file and os.path.exists(final_guess):
        os.replace(final_guess, output_file)
    logging.info(f"yt-dlp fallback complete: {output_file}")
    return output_file

def download_audio_with_ytdlp(url: str, artist: str, year: str, album: str):
    if not ensure_tool("yt-dlp"):
        raise RuntimeError("yt-dlp not found in PATH. Install it to enable fallback.")
    # Extract m4a with metadata tagging where possible
    cmd = [
        "yt-dlp",
        "-f", "bestaudio[ext=m4a]/bestaudio",
        "--extract-audio",
        "--audio-format", "m4a",
        "--audio-quality", "0",
        "--add-metadata",
        "--parse-metadata", f"title:%(title)s",
        "--parse-metadata", f"artist:{artist}",
        "--parse-metadata", f"date:{year}",
        "--parse-metadata", f"album:{album}",
        "-o", "%(title)s.%(ext)s",
        url
    ]
    logging.info("yt-dlp audio fallback running...")
    subprocess.run(cmd, check=True)
    logging.info("yt-dlp audio fallback done.")
    return

# ----------------------------------
# Video (1080p preferred) via pytubefix, with yt-dlp fallback
# ----------------------------------
def download_youtube_video(url: str, videoObj: any, useVideoObj: bool, preferred_res: str = "1080p"):
    """
    Download a video at preferred_res (default 1080p). If pytubefix fails on cipher/JS,
    fallback to yt-dlp. Returns produced filename.
    """
    if useVideoObj:
        yt = videoObj
    else:
        yt = make_yt(url)

    title = sanitize_filename(getattr(yt, "title", None) or "untitled")
    pub = yt.publish_date.strftime("%Y-%m-%d") if getattr(yt, "publish_date", None) else datetime.date.today().isoformat()
    output_file = f"{pub} - {title}.mp4"
    logging.info(f"Downloading {output_file}...")

    try:
        # 1) Progressive exact res (rare for 1080p)
        progressive = yt.streams.filter(progressive=True, res=preferred_res, file_extension="mp4").first()
        if not progressive and preferred_res != "720p":
            progressive = yt.streams.filter(progressive=True, res="720p", file_extension="mp4").first()
        if progressive:
            tmp = progressive.download()
            os.replace(tmp, output_file)
            logging.info("Downloaded progressive stream (no merge).")
            return output_file

        # 2) DASH: MP4 video at preferred res (or best), and best m4a
        video_stream = yt.streams.filter(adaptive=True, mime_type="video/mp4", res=preferred_res).first()
        if not video_stream:
            video_stream = yt.streams.filter(adaptive=True, mime_type="video/mp4").order_by("resolution").desc().first()
        if not video_stream:
            raise RuntimeError("No suitable MP4 video stream found.")

        audio_stream = (
            yt.streams.filter(only_audio=True, mime_type="audio/mp4").order_by("abr").desc().first()
            or yt.streams.get_audio_only("m4a")
            or yt.streams.filter(only_audio=True).order_by("abr").desc().first()
        )
        if not audio_stream:
            raise RuntimeError("No suitable audio stream found.")

        temp_v = video_stream.download()
        temp_a = audio_stream.download()

        base_a, ext_a = os.path.splitext(temp_a)
        audio_file = base_a + ".m4a"
        if ext_a.lower() != ".m4a":
            logging.info(f"Transcoding audio {ext_a} -> .m4a")
            subprocess.run(
                ["ffmpeg", "-y", "-i", temp_a, "-c:a", "aac", "-b:a", "192k", audio_file],
                check=True
            )
            os.remove(temp_a)
        else:
            audio_file = temp_a

        logging.info("Combining video and audio with ffmpeg...")
        subprocess.run(
            ["ffmpeg", "-y",
             "-i", temp_v,
             "-i", audio_file,
             "-c:v", "copy",
             "-c:a", "aac",
             "-shortest",
             "-movflags", "+faststart",
             output_file],
            check=True
        )

        if os.path.exists(temp_v):
            os.remove(temp_v)
        if os.path.exists(audio_file):
            os.remove(audio_file)

        logging.info("Successfully downloaded and combined.")
        return output_file

    except Exception as e:
        msg = str(e)
        logging.error(f"pytubefix failed for this video: {msg}")
        if looks_like_cipher_error(msg):
            logging.info("Cipher/JS parse issue detected; using yt-dlp fallback for this video.")
            return download_video_with_ytdlp(yt.watch_url if hasattr(yt, "watch_url") else url, output_file, preferred_height=int(preferred_res.replace("p","")))
        # Try again with ANDROID client (sometimes avoids web player JS issues)
        try:
            logging.info("Retrying with ANDROID client...")
            yt_alt = make_yt(yt.watch_url if hasattr(yt, "watch_url") else url, client="ANDROID")
            return download_youtube_video("", yt_alt, True, preferred_res=preferred_res)
        except Exception as e2:
            msg2 = str(e2)
            logging.error(f"ANDROID client attempt failed: {msg2}")
            if looks_like_cipher_error(msg2):
                logging.info("Falling back to yt-dlp after ANDROID client failure.")
                return download_video_with_ytdlp(yt.watch_url if hasattr(yt, "watch_url") else url, output_file, preferred_height=int(preferred_res.replace("p","")))
            raise

# ----------------------------------
# Playlist / Channel
# ----------------------------------
def get_urls_from_youtube_playlist(playlist_url: str):
    pl = Playlist(playlist_url, use_oauth=True, allow_oauth_cache=True)
    urls = pl.video_urls
    logging.info(f"Number of videos in playlist: {len(urls)}")
    return urls

def get_videos_from_youtube_playlist(playlist_url: str, preferred_res: str = "1080p"):
    urls = get_urls_from_youtube_playlist(playlist_url)
    for url in urls:
        max_retries = 2
        for attempt in range(1, max_retries + 1):
            try:
                yt = make_yt(url)
                download_youtube_video("", yt, True, preferred_res=preferred_res)
                time.sleep(random.uniform(1.0, 2.5))
                break
            except Exception as e:
                logging.error(f"[{attempt}/{max_retries}] {url} -> {e}")
                if attempt == max_retries:
                    logging.error(f"Giving up on {url}")
                else:
                    time.sleep((2 ** (attempt - 1)) + random.random())

def get_videos_from_youtube_channel(channel_url: str, preferred_res: str = "1080p"):
    try:
        ch = Channel(channel_url)
        video_urls = ch.video_urls
        logging.info(f"Number of videos in channel: {len(video_urls)}")
        for v in ch.videos:
            download_youtube_video("", v, True, preferred_res=preferred_res)
            time.sleep(random.uniform(1.0, 2.5))
    except Exception as e:
        logging.error(f"Error downloading videos from channel: {e}")

# ----------------------------------
# Optional utilities you had
# ----------------------------------
def fix_metadata():
    logging.info("Fixing metadata...")
    chapter_names = ["01 Anak Laki-Laki yang Bertahan Hidup"]
    for chapter_name in chapter_names:
        input_file = chapter_name + ".m4a"
        output_file = chapter_name + "_fixed.m4a"
        subprocess.run(
            ["ffmpeg", "-y", "-i", input_file, "-c", "copy",
             "-metadata", f"title={chapter_name}", output_file],
            check=True
        )
        logging.info(f"Metadata added. Final output: {output_file}")

def remove_fixed_suffix():
    logging.info("Removing '_fixed' suffix from filenames...")
    for filename in os.listdir():
        if filename.endswith("_fixed.m4a"):
            new_filename = filename.replace("_fixed.m4a", ".m4a")
            os.rename(filename, new_filename)
            logging.info(f"Renamed: {filename} -> {new_filename}")

# ----------------------------------
# Entrypoint
# ----------------------------------
def main():
    # --- A) SINGLE VIDEO ---
    # url = "https://www.youtube.com/watch?v=fZC-IR5kl1U"
    # download_youtube_video(url, None, False, preferred_res="1080p")

    # --- B) PLAYLIST VIDEOS (your case) ---
    playlist_url = "https://www.youtube.com/playlist?list=PLZ81_TikBBITZxfbFUGbD1cF1O5d91jTf"
    get_videos_from_youtube_playlist(playlist_url, preferred_res="1080p")

    # --- C) AUDIO-ONLY EXAMPLE ---
    # download_youtube_audio(url, artist="YouTube", year="2025", album="Brendan OBrien")

    # --- D) WHOLE CHANNEL ---
    # channel_url = "https://www.youtube.com/@SwiftfulThinking"
    # get_videos_from_youtube_channel(channel_url, preferred_res="1080p")
    pass

if __name__ == "__main__":
    main()
