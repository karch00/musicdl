import argparse
import os
import signal
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from time import sleep
from requests import Session
from musicdl.fileparse import MusicList
from musicdl.songs import *
from musicdl.constants import *

def signal_handler(sig, frame):
    """
    Signal handler for exit
    """
    print("\n[~] Interrupting downloads")
    os.kill(os.getpid(), signal.SIGTERM)

def download_song_wrapper(song_to_process: dict) -> None:
    """
    Download song wrapper for multithreading implementation

    Args:
        song_to_process (dict): Song containing all info required for multithreaded processing
    """
    # Variable init
    bearer_token: str = song_to_process["bearer_token"]
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
    res = song.download_song(output_path, song_format, session, verbose, bearer_token) # Add bearer token when spotify is set up
    if isinstance(res, FailedSongDownloadError):
        print(f"[-] Failed downloading song: {res.message}")
        return
    
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

    # Sleep
    sleep(5)

def get_bearer_token(session: Session, client_id: str, client_secret: str) -> dict | None:
    """
    Gets bearer token for spotify API

    Args:
        session (Session): request session
        client_id (str): app client id
        client_secret (str): app client secret
    Returns:
        out (dict|None): post content, None if invalid
    """
    res = session.post(
        f"https://accounts.spotify.com/api/token?grant_type=client_credentials&client_id={client_id}&client_secret={client_secret}",
        headers=SP_HEADERS
    )

    return res.json()

def main():
    # Set sigint
    signal.signal(signal.SIGINT, signal_handler)

    # Parse args
    parser = argparse.ArgumentParser()
    parser.add_argument("filename", help="Music list file name or path")
    parser.add_argument("-f", "--format", choices=["mp3", "flac"], required=False, help="Music format to download songs as. Valid are: mp3 and flac. Default mp3")
    parser.add_argument("-o", "--output", required=False, help="Parent directory where songs will be downloaded and sorted. Default is ./music. If path does not exist, will create it")
    parser.add_argument("-v", "--verbose", required=False, action="store_true", help="Controls whether yt-dlp will be verbose or not")
    parser.add_argument("-s", "--spotify_credentials", required=False, help="Path to spotify credentials (app ID and secret). File must be formatted .env-style and contain the variables: ID=1234 and SECRET=1bf3")
    args = parser.parse_args()

    list_filename = args.filename
    song_format = args.format or "mp3"
    output_path = args.output or "./music"
    verbose = args.verbose
    spotify_envpath = args.spotify_credentials or None
    
    # Check spotify env path validity
    spotify_id = ""
    spotify_secret = ""
    if spotify_envpath:
        # File exists / doesnt exist
        if Path(spotify_envpath).exists() and Path(spotify_envpath).is_file():
            print("[+] Spotify env found")
            
            # Check for environment variables present
            load_dotenv(spotify_envpath)
            spotify_id = os.getenv("ID")
            spotify_secret = os.getenv("SECRET")

            if spotify_id and spotify_secret:
                print("[+] Spotify credentials succesfully set")
            else:
                print("[-] Couldn't set spotify credentials\n    Will prompt for credentials if spotify URL found in music file.")
        else:
            print("[-] Spotify env not found / invalid file type.\n    Will prompt for credentials if spotify URL found in music file.")

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
    
    # Session init
    session = Session()

    # Get spotify bearer token
    bearer_token = ""
    if songs_file.contains_spotify:
        print("[+] Spotify songs found in file")
        
        # Prompt, id and secret not set
        if not spotify_id or not spotify_secret:
            print("[~] Spotify credentials not specified or could not be set")
            
            # Request bearer token until valid
            while True:
                spotify_id = input("> App ID: ")
                spotify_secret = input("> App Secret: ")
                token_dict = get_bearer_token(session, spotify_id, spotify_secret)

                if token_dict and "access_token" in token_dict:
                    print("[+] Bearer token acquired")
                    bearer_token = token_dict["access_token"]
                    break

                print(f"[-] Could not get bearer token: {token_dict}. Re-enter credentials.")
        # Get bearer token directly
        else:
            token_dict = get_bearer_token(session, spotify_id, spotify_secret)
            if token_dict and "access_token" in token_dict:
                print("[+] Bearer token acquired")
                bearer_token = token_dict["access_token"]
            else:
                print(f"[-] Could not get bearer token: {token_dict}")
                return

    # Song list for thread pool init
    songs_to_process = []
    for idx, song in enumerate(songs, start=1):
        songs_to_process.append({
            "bearer_token": bearer_token,
            "song": song,
            "song_idx": idx,
            "song_count": len(songs),
            "output_path": output_path,
            "song_format": song_format,
            "session": session,
            "verbose": verbose
        })
    
    # Start song processing
    with ThreadPoolExecutor(max_workers=4) as executor:
        executor.map(download_song_wrapper, songs_to_process)

if __name__ == "__main__":
    main()