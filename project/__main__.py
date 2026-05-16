import argparse
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from time import sleep
from random import randint
from requests import Session
from fileparse import MusicList
from songs import *


def download_song_wrapper(song_to_process: dict) -> None:
    """
    Download song wrapper for multithreading implementation

    Args:
        song_to_process (dict): Song containing all info required for multithreaded processing
    """
    # Initial sleep
    sleep(randint(1, 10))
    
    # Variable init
    song: Song = song_to_process["song"]
    song_idx: int = song_to_process["song_idx"]
    song_count: int = song_to_process["song_count"]
    output_path: str = song_to_process["output_path"]
    song_format: str = song_to_process["song_format"]
    session: Session = song_to_process["session"]
    verbose: bool = song_to_process["verbose"]
    
    # Song variable unpack
    url = song.url
    title = song.title
    artist = song.artist
    album = song.album
    cover = song.cover
    track = song.track
    genre = song.genre
    year = song.year

    # Download song
    print(f"[+] Downloading song {song_idx}/{song_count}:\n\t- URL: {url}\n\t- Title: {title}\n\t- Artist: {artist}\n\t- Album: {album}\n\t- Cover: {cover}\n\t- Track: {track}\n\t- Genre: {genre}\n\t- Year: {year}")
    res = song.download_song(output_path, song_format, session, verbose) # Add bearer token when spotify is set up
    if isinstance(res, FailedSongDownloadError):
        print(f"[-] Failed downloading song: {res.message}")
    
    # Download cover if present
    print(f"[+] Downloading cover...")
    if song.cover:
        res = song.download_cover(output_path, session)
        if isinstance(res, FailedCoverDownloadError):
            print(f"[-] Faled downloading cover: {res.message}")
    
    # Apply metadata
    print("[+] Applying metadata...")
    res = song.apply_metadata(output_path, song_format)
    if isinstance(res, FailedMetadataApplyError):
        print(f"[-] Failed applying metadata: {res.message}")

    print(f"[+] Finished processing song {song_idx}\n")

def main():
    # Parse args
    parser = argparse.ArgumentParser()
    parser.add_argument("filename", help="Music list file name or path")
    parser.add_argument("-f", "--format", choices=["mp3", "flac"], required=False, help="Music format to download songs as. Valid are: mp3 and flac. Default mp3")
    parser.add_argument("-o", "--output", required=False, help="Parent directory where songs will be downloaded and sorted. Default is ./music. If path does not exist, will create it")
    parser.add_argument("-v", "--verbose", required=False, help="Controls whether yt-dlp will be verbose or not")
    args = parser.parse_args()

    list_filename = args.filename
    song_format = args.format or "mp3"
    output_path = args.output or "./music"
    verbose = args.verbose or False
    
    # Check for output path validity
    if not Path(output_path).exists():
        print(f"[~] Output path does not exist, creating directories: {output_path}")
        os.makedirs(output_path, exist_ok=True)
    
    # Read file
    print("[+] Reading music list file")
    songs_file = MusicList(list_filename)
    songs = songs_file.songs
    
    if songs is FileNotFoundError:
        print(f"[-] Music list file does not exist: {list_filename}")
        return 1
    
    print(f"[+] {len(songs)} songs read succesfully, starting downloads")

    # Get spotify bearer token
    if songs_file.contains_spotify:
        print("[+] Spotify songs found in file")
        raise NotImplementedError
        # TODO: 
        # Implement arg to spotify secret env, validate
        # If not found, ask here for spotify env

    # Youtube session init
    youtube_session = Session()
    youtube_session.headers= {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }

    # Song list for thread pool init
    songs_to_process = []
    for song in songs:
        songs_to_process.append({
            "song": song,
            "song_idx": songs.index(song)+1,
            "song_count": len(songs),
            "output_path": output_path,
            "song_format": song_format,
            "session": youtube_session,
            "verbose": verbose
        })
    
    # Start song processing
    with ThreadPoolExecutor(max_workers=4) as executor:
        executor.map(download_song_wrapper, songs_to_process)

if __name__ == "__main__":
    main()