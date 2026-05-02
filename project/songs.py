from typing import Literal
import requests


class Song:
    """
    Song class. Represents a song and its metadata.
    """
    def __init__(
        self, 
        url: str,
        url_type: Literal[None, "youtube-song", "spotify-song"],
        title: str|None = None, 
        artist: str|None = None, 
        album: str|None = None, 
        cover: str|None = None,
        genre: str|None = None,
        year: str|None = None,
        track: int|None = None
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
    
    def __get_spotify_metadata__(self, session: requests.Session, bearer_token: str) -> dict[str, str] | None:
        """
        Gets metadata from the spotify link and returns the Title, Artist and Art album cover.

        Params:
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

    


    def download(self, session: requests.Session, bearer_token: str) -> None:
        raise NotImplementedError