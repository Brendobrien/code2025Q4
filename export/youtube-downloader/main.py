import os
import re
import requests
import subprocess
from pytubefix import YouTube, Playlist, Channel
from pytubefix.cli import on_progress
import logging
import time
import random
import re
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def download_thumbnail(url, filename):
    """Download thumbnail image from URL."""
    response = requests.get(url)
    if response.status_code == 200:
        with open(filename, "wb") as f:
            f.write(response.content)
        logging.info(f"Thumbnail downloaded: {filename}")
    else:
        logging.error(
            f"Failed to download thumbnail. Status code: {response.status_code}"
        )


def extract_chapter_info(filename):
    """Extract chapter information from filename."""
    pattern = re.search(r"(Bab \d+\s*[^(]+)(?=\s*\(Audiobook)", filename)

    if pattern:
        chapter_info = pattern.group(1).strip().rstrip(".")

        # Format chapter number and remove "Bab"
        chapter_info = re.sub(
            r"Bab (\d+)", lambda m: f"{int(m.group(1)):02d}", chapter_info
        )

        return " ".join(chapter_info.split())

    return "NO RENAME - " + filename


def download_youtube_audio(url, artist, year, album, session):
    """Download audio from YouTube, add metadata and album cover."""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            yt = YouTube(url, on_progress_callback=on_progress)
            yt.use_oauth = True
            yt.allow_oauth_cache = True

            logging.info(f"Downloading audio stream... (Attempt {attempt + 1})")
            audio_stream = yt.streams.filter(only_audio=True).first()
            out_file = audio_stream.download()
            logging.info(f"Audio downloaded: {out_file}")

            base, _ = os.path.splitext(out_file)
            new_file = base + ".m4a"
            os.rename(out_file, new_file)
            logging.info(f"File renamed to: {new_file}")

            logging.info("Downloading thumbnail...")
            thumbnail_file = base + "_thumb.png"
            download_thumbnail(yt.thumbnail_url, thumbnail_file)

            # Add album cover to the audio file
            logging.info("Adding album cover...")
            new_file_with_cover = base + "_with_cover.m4a"
            ffmpeg_add_album_cover = [
                "ffmpeg",
                "-i",
                new_file,
                "-i",
                thumbnail_file,
                "-map",
                "0",
                "-map",
                "1",
                "-c",
                "copy",
                "-disposition:v",
                "attached_pic",
                "-metadata:s:v",
                'title="Album cover"',
                "-metadata:s:v",
                'comment="Cover (front)"',
                new_file_with_cover,
            ]
            subprocess.run(ffmpeg_add_album_cover, check=True)
            logging.info(f"Album cover added: {new_file_with_cover}")

            # Add metadata to the audio file
            logging.info("Adding metadata...")
            chapter_name = extract_chapter_info(os.path.basename(base))
            output_file = chapter_name + ".m4a"
            ffmpeg_add_metadata = [
                "ffmpeg",
                "-i",
                new_file_with_cover,
                "-c",
                "copy",
                "-metadata",
                f"title={chapter_name}",
                "-metadata",
                f"artist={artist}",
                "-metadata",
                f"year={year}",
                "-metadata",
                f"album={album}",
                output_file,
            ]
            subprocess.run(ffmpeg_add_metadata, check=True)
            logging.info(f"Metadata added. Final output: {output_file}")

            # Clean up temporary files
            os.remove(new_file)
            os.remove(thumbnail_file)
            os.remove(new_file_with_cover)
            logging.info("Temporary files cleaned up.")

            return  # Success, exit the function

        except Exception as e:
            logging.error(f"Error processing {url} (Attempt {attempt + 1}): {str(e)}")
            if attempt < max_retries - 1:
                wait_time = (2**attempt) + random.random()
                logging.info(f"Retrying in {wait_time:.2f} seconds...")
                time.sleep(wait_time)
            else:
                logging.error(f"Failed to process {url} after {max_retries} attempts.")


def get_urls_from_youtube_playlist(playlist_url, session):
    """Get all video URLs from a YouTube playlist."""
    playlist = Playlist(playlist_url)
    playlist.use_oauth = True
    playlist.allow_oauth_cache = True
    logging.info(f"Number of videos in playlist: {len(playlist.video_urls)}")
    return playlist.video_urls


def create_session():
    session = requests.Session()
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update(
        {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
    )
    return session


def fix_metadata():
    # Fix metadata in the audio file
    logging.info("Fixing metadata...")

    chapter_names = ["01 Anak Laki-Laki yang Bertahan Hidup"]

    for chapter_name in chapter_names:
        input_file = chapter_name + ".m4a"
        output_file = chapter_name + "_fixed.m4a"
        ffmpeg_add_metadata = [
            "ffmpeg",
            "-i",
            input_file,
            "-c",
            "copy",
            "-metadata",
            f"title={chapter_name}",
            "-y",
            output_file,
        ]
        subprocess.run(ffmpeg_add_metadata, check=True)
        logging.info(f"Metadata added. Final output: {output_file}")


def remove_fixed_suffix():
    logging.info("Removing '_fixed' suffix from filenames...")
    for filename in os.listdir():
        if filename.endswith("_fixed.m4a"):
            new_filename = filename.replace("_fixed.m4a", ".m4a")
            os.rename(filename, new_filename)
            logging.info(f"Renamed: {filename} -> {new_filename}")


def get_audio_for_youtube_playlist():
    artist = "J.K. Rowling"
    year = "1997"
    album = "Harry Potter dan Batu Bertuah"

    playlist_url = (
        "https://www.youtube.com/playlist?list=PL3Z2GzUD5TnX0cCZRmOBfTTg9r2pWHeHt"
    )

    session = create_session()
    all_urls_from_playlist = get_urls_from_youtube_playlist(playlist_url, session)

    for url in all_urls_from_playlist:
        download_youtube_audio(url, artist, year, album, session)
        time.sleep(random.uniform(1, 3))  # Add a random delay between requests


def get_videos_from_youtube_channel(channel_url):
    """Get all video URLs from a YouTube channel. Have to combine video and audio for 720p"""
    try:
        channel = Channel(channel_url)
        video_urls = channel.video_urls
        logging.info(f"Number of videos in channel: {len(video_urls)}")
        for i in range(0, len(channel.videos)):
            video = channel.videos[i]
            download_youtube_video_720p("", video, True)
            
    except Exception as e:
        logging.error(f"Error downloading videos from channel: {e}")
        return []
    
def download_youtube_video_720p(url: str, videoObj: any, useVideoObj: bool):
    video = videoObj
    if useVideoObj != True:
        yt = YouTube(url, on_progress_callback=on_progress)
        video = yt

    print(video.title)

    output_file = f"{video.publish_date.strftime("%Y-%m-%d")} - {video.title}.mp4"
    logging.info(f"Downloading {output_file}...")

    # Get the audio stream
    audio_stream = video.streams.filter(only_audio=True).first()
    temp_audio_file = audio_stream.download()
    logging.info(f"Audio downloaded:\n{temp_audio_file}")
    
    base, _ = os.path.splitext(temp_audio_file)
    audio_file = base + ".m4a"
    os.rename(temp_audio_file, audio_file)
    logging.info(f"File renamed to: {audio_file}")
    
    video_stream = video.streams.filter(resolution='720p').first()
    video_file = video_stream.download()
    logging.info(f"Video downloaded:\n{video_file}")

    # Combine video and audio using ffmpeg
    print("Combining video and audio...")
    os.system(f'ffmpeg -i "{video_file}" -i "{audio_file}" -c:v copy -c:a aac "{output_file}"')
    
    # Remove temporary files
    os.remove(video_file)
    os.remove(audio_file)

    logging.info(f"Successfully downloaded and combined")

def main():
    # channel_url = "https://www.youtube.com/@twostraws"
    # channel_url = "https://www.youtube.com/@swiftandtips"
    # channel_url = "https://www.youtube.com/@tundsdev"
    # channel_url = "https://www.youtube.com/@SwiftfulThinking"
    # get_videos_from_youtube_channel(channel_url)

    # download_youtube_video_720p("https://www.youtube.com/watch?v=75-c6jSE8kU", "", False)
    download_youtube_video_720p("https://www.youtube.com/watch?v=LRlSjdTuHWY", "", False)
    download_youtube_video_720p("https://www.youtube.com/watch?v=2VvoLlk0_88", "", False)

if __name__ == "__main__":
    main()
