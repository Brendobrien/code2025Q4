# 🎥⬇️ YouTube Audio Downloader

```
pipenv install
prp main.py
```

This script downloads audio from YouTube videos, adds metadata, and converts them to .m4a format with album art.

## Features

- Downloads audio from YouTube videos
- Adds album art from video thumbnail
- Sets metadata (title, artist, year, album)
- Handles chapter information in filenames
- Includes retry mechanism for failed downloads

## Requirements

- Python 3.x
- FFmpeg
- Required Python packages (install via `pipenv install`):
  - pytubefix
  - requests
- Pipenv (optional, for managing Python packages)

## Usage

1. Ensure FFmpeg is installed and accessible in your system PATH.
2. Set up your environment variables or modify the script to include your YouTube API credentials.
3. Run the script:

```python
pipenv run python main.py
```

## Key Concepts and Code Snippets

### Downloading YouTube Audio

```python
yt = YouTube(url, on_progress_callback=on_progress)
audio_stream = yt.streams.filter(only_audio=True).first()
out_file = audio_stream.download()
```

### Adding Album Art

```python
ffmpeg_add_album_cover = [
    'ffmpeg',
    '-i', new_file,
    '-i', thumbnail_file,
    '-map', '0',
    '-map', '1',
    '-c', 'copy',
    '-disposition:v', 'attached_pic',
    '-metadata:s:v', 'title="Album cover"',
    '-metadata:s:v', 'comment="Cover (front)"',
    new_file_with_cover
]
subprocess.run(ffmpeg_add_album_cover, check=True)
```

### Adding Metadata

```python
ffmpeg_add_metadata = [
    'ffmpeg',
    '-i', new_file_with_cover,
    '-c', 'copy',
    '-metadata', f'title={chapter_name}',
    '-metadata', f'artist={artist}',
    '-metadata', f'year={year}',
    '-metadata', f'album={album}',
    output_file
]
subprocess.run(ffmpeg_add_metadata, check=True)
```

# Aug 15 2024

### Original FFmpeg command line prompts

Add album art

```
ffmpeg -i input.mp3 -i cover.png -map 0 -map 1 -c copy -disposition:v attached_pic -metadata:s:v title="Album cover" -metadata:s:v comment="Cover (front)" output.m4a
```

Add title, artist, year, and album

```
ffmpeg -i input.mp3 -c copy -metadata title="Song Title" -metadata artist="Artist Name" -metadata year="2024" -metadata album="Album Name" output-2.m4a
```
