
class Song:
    """
    Song class. Represents a song and its metadata.
    """
    def __init__(
        self, 
        url: str,
        url_type: Literal[None, "youtube-song", "youtube-playlist", "spotify-song", "spotify-playlist"],
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