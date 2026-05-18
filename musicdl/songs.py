from typing import Literal
import requests
import re
import yt_dlp
import os
from mutagen.flac import FLAC, Picture
from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3, APIC

class FailedSongDownloadError(Exception):
    def __init__(self, message: str|None = None):
        self.message = message
class FailedCoverDownloadError(Exception):
    def __init__(self, message: str|None = None):
        self.message = message
class FailedMetadataApplyError(Exception):
    def __init__(self, message: str|None = None):
        self.message = message
class CoverExistsError(Exception):
    def __init__(self, message: str|None = None):
        self.message = message

class Song:
    """
    Song class. Represents a song and its metadata.

    Args:
        url (str): Song URL
        url_type (str): youtube-song or spotify-song
        title (str)
        artist (str)
        album (str)
        cover(str) : Album cover art URL or path
        genre(str)
        year(str)
        track(str)
    """
    def __init__(
        self, 
        url: str,
        url_type: Literal[None, "youtube-song", "spotify-song"],
        title: str, 
        artist: str|None = None, 
        album: str|None = None, 
        cover: str|None = None,
        genre: str|None = None,
        year: str|None = None,
        track: str|None = None
    ):
        self.url = url
        self.url_type = url_type
        self.title = title
        self.artist = artist
        self.album = album
        self.cover = cover
        self.genre = genre
        self.year = year
        self.track = track
    
    def __get_spotify_metadata(self, session: requests.Session, bearer_token: str) -> dict[str, str] | None:
        """
        Gets metadata from the spotify link and returns the Title, Artist and Art album cover for
        more accurate search results from youtube.

        Args:
            session (requests.Session): Parent session
            bearer_token (str): Spotify bearing token

        Returns:
            out (dict[str, str]): Title, Artist and art cover URL. None if request error
        """
        # Set headers and URL
        HEADERS = {
            f"Authorization: Bearer {bearer_token}"
        }
        url_id = self.url.strip("https://open.spotify.com/track/")
        URL = f"https://api.spotify.com/v1/tracks/{url_id}"
        
        # Get request and check for ok status
        # Return None if not 200
        r = session.get(url=URL, headers=HEADERS)
        if not r.ok or "error" in r.json():
            return None

        # Get title and album art
        r_data = r.json()
        title = r_data["name"]
        artist = r_data["artists"][0]["name"]
        cover = r_data["album"]["images"][0]["url"]

        # Return metadata
        return {"title": title, "artist": artist, "cover": cover}
    
    def __query_youtube(self, title: str, artist: str, session: requests.Session) -> str | None:
        """
        Queries youtube and searches for the title to return the corresponding URL

        Args:
            title (str): The title to query

        Returns:
            out (str): Corresponding URL, None if query error
        """
        # Init variables
        PATTERN=re.compile(r"\/watch\?v=.{11}")
        title_list = title.split(" ")
        artist_list = artist.split(" ")

        # Search query
        # Return None if request error
        r = session.get(url=f"https://www.youtube.com/results?search_query={'+'.join(title_list)}+{'+'.join(artist_list)}")
        if not r.ok:
            return None

        # Get only first match, most relevant
        url_component = PATTERN.search(r.content.decode())[0]

        return f"https://youtube.com{url_component}"

    def __get_download_path_dir_tree(self, parent_directory: str) -> str:
        """
        Returns the download path directory tree for song/cover to download

        Args:
            parent_directory (str): Parent path

        Returns:
            out (str): Full directory tree from parent_directory  
        """
        # /artist/album/song ; artist and album can be missing practically, but not recommended!
        parent_directory = parent_directory.replace("\\", "/")
        output_path = f"{parent_directory}{'/' if parent_directory[-1] != '/' else ''}"
        if self.artist:
            output_path += f"{'/' if output_path[-1] != '/' else ''}{self.artist.replace(' ', '_')}"
        if self.album:
            output_path += f"{'/' if output_path[-1] != '/' else ''}{self.album.replace(' ', '_')}"
        if not self.artist and not self.album:
            output_path += f"{'/' if output_path[-1] != '/' else ''}{self.title.replace(' ', '_')}"

        return output_path
    
    def __detect_image_mime(self, data: bytes) -> str:
        """
        Detects mime type of the cover image

        Args:
            data (bytes): Cover data in bytes

        Returns:
            out (str): Mime type
        """
        if data[:3] == b'\xff\xd8\xff':
            return "image/jpeg"
        if data[:8] == b'\x89PNG\r\n\x1a\n':
            return "image/png"
        if data[:4] == b'RIFF' and data[8:12] == b'WEBP':
            return "image/webp"
        return "image/jpeg"

    def download_song(self, parent_directory: str, song_format: Literal["mp3", "flac"], session: requests.Session, verbose: bool = False, bearer_token: str|None = None) -> None|FailedSongDownloadError:
        """
        Downloads the song and its cover image onto the same 'Artist/Album/' directory

        Args:
            parent_directory (str): base output directory path
            song_format (str): format: mp3 or flac
            session (requests.Session): The session to make requests from
            bearer_token (str|None): Spotify bearer token, None if no succesful spotify API bind or Spotify credentials not present

        Returns:
            error (FailedSongDownloadError): Error produced if any
        """
        # Get spotify metadata
        # Change artist and cover to queried if not set by custom metadata
        # Query youtube for /watch?v= URL
        # Return FailedSongDownloadError if download failed for any reason
        if self.url_type == "spotify-song":
            if not bearer_token:
                return FailedSongDownloadError("Failed getting spotify metadata: Bearer token invalid or missing")

            spotify_metadata = self.__get_spotify_metadata(session=session, bearer_token=bearer_token)
            if not spotify_metadata:
                return FailedSongDownloadError("Failed getting spotify metadata: Request failed")

            title = spotify_metadata["title"]
            self.artist = self.artist or spotify_metadata["artist"]
            self.cover = self.cover or spotify_metadata["cover"]
            self.url = self.__query_youtube(title=title, artist=self.artist, session=session)
            if not self.url:
                return FailedSongDownloadError("Failed getting youtube URL: Request failed")
        
        # Create download directory inside parent output directory path
        output_path = self.__get_download_path_dir_tree(parent_directory)

        if not os.path.exists(output_path):
            os.makedirs(output_path)
        
        # Get song format, mp3 fallback; output path and options
        if song_format not in ["mp3", "flac"]:
            song_format = "mp3"

        # Set options and download song
        options = {
            "format": "bestaudio/best", 
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": song_format,
                "preferredquality": "192" if song_format == "mp3" else "0",
            }],
            "outtmpl": f"{output_path}/{self.title.replace(' ', '_')}",
            "quiet": not verbose,
            "no_warnings": False,
        }
        try:
            with yt_dlp.YoutubeDL(options) as ydl:
                ydl.download([self.url])
        except Exception as e:
            return FailedSongDownloadError(f"Failed downloading song: {e}")
        
    def download_cover(self, parent_directory: str, session: requests.Session) -> None|FailedCoverDownloadError:
        """
        Downloads cover from self.cover URL. Meant to be called after download()
        Will return FailedCoverDownloadError if path does not exist since it means download() failed or was not called beforehand

        Args:
            parent_directory (str): Base path
            session (requests.Session): The session to make requests from

        Returns:
            error (FailedCoverDownloadError): Error produced, if any
        """ 
        # Download cover if present
        # Get request as stream, write by chunks into the cover path if does not exist already
        # Invalidates multiple <cover> tags inside the same album by design
        output_path = self.__get_download_path_dir_tree(parent_directory)
        if not os.path.exists(output_path):
            return FailedCoverDownloadError("Song download path does not exist")
        
        try:
            r = session.get(self.cover, stream=True)
            if not r.ok:
                return FailedCoverDownloadError("Failed fetching cover image")

            if os.path.exists(f"{output_path}/cover"):
                return  CoverExistsError(output_path)
            with open(file=f"{output_path}/cover", mode="wb") as f:
                for chunk in r:
                    f.write(chunk)
        
        except Exception as e:
            return FailedCoverDownloadError("Failed fetching cover image")
    
    def apply_metadata(self, parent_directory: str, song_format: Literal["mp3", "flac"]) -> None|FailedMetadataApplyError:
        """
        Applies applicable metadata to the song

        Args:
            parent_directory (str): Parent directory
            song_format (str): Song format

        Returns:
            error (FailedMetadataApplyError): 
        """
        # Init variables
        # Ensure valid song format, mp3 fallback
        if song_format not in ["mp3", "flac"]:
            song_format = "mp3"

        # Check if parent dir and song paths exist
        dir_path= self.__get_download_path_dir_tree(parent_directory)
        song_path = f"{dir_path}/{self.title.replace(' ', '_')}.{song_format}"
        for path in [dir_path, song_path]:
            if not os.path.exists(path):
                return FailedMetadataApplyError(f"Failed metadata apply: File [{path}] does not exist")

        # Change metadata to each attribute
        # MAP[attribute : metatag]
        ATTRIBUTES_MAP = {
            "title": "title",
            "artist": "artist",
            "album": "album",
            "genre": "genre",
            "year": "date",
            "track": "tracknumber"
        }
        if song_format == "flac":
            audio = FLAC(song_path)
        else:
            audio = EasyID3(song_path)

        for attribute, metatag in ATTRIBUTES_MAP.items():
            audio[metatag] = self.__getattribute__(attribute)
        audio.save()

        # Set cover 
        if not self.cover:
            return

        # Check if cover_path exists
        cover_path = f"{dir_path}/cover"
        if not os.path.exists(cover_path):
            return FailedMetadataApplyError(f"Failed metadata cover apply: Cover [{path}] does not exist")
        
        try:
            if song_format == "flac":
                image = Picture()
                image.type = 3
                image.mime = self.__detect_image_mime(cover_data)
                image.data = open(cover_path, "rb").read()
                image.desc = "Cover art"
                audio.add_picture(image)
            else:
                audio = ID3(song_path)
                with open(cover_path, "rb") as f:
                    cover_data = f.read()
                    audio.add(APIC(
                        encoding = 3,
                        mime = self.__detect_image_mime(cover_data),
                        type = 3,
                        desc = "Cover art",
                        data = cover_data
                    ))
            audio.save()
        except Exception as e:
            return FailedMetadataApplyError(f"Failed metadata cover apply: {e}")


                    
        