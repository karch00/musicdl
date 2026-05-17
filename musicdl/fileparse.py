import pathlib
from typing import Literal
import re
from musicdl.songs import Song


class MusicList:
    """
    Music list class. Represents the music list file.

    Automatically parses file and creates songs with their respective metadata on class creation.

    Args:
        path (str): File path
    Attributes:
        path (str): File path
        songs (list[Song]): list of songs read from file
        contains_spotify (bool): Whether there are spotify songs within the list or not
    """
    def __init__(self, path: str):
        self.path = path
        self.songs = self.__parse_songs()
        self.contains_spotify = False

    def __read_file(self) -> list[str]:
        """
        Reads file lines, returns a list with each read line.

        ### Returns:
        - out (list[str]): Lines read
        """
        if not pathlib.Path(self.path).exists():
            return FileNotFoundError
        
        with open(file=self.path, mode="r", encoding="utf-8") as f:
            return f.readlines()

    def __get_section_metadata(self, line: str) -> dict[str, str|None] | None:
        """
        Gets the metadata set for the tag section in the line. Returns None if not a valid metadata tag

        Args:
            line (str): Line to read for metadata tag

        Returns:
            out (dict | None): Tag metadata to add/remove or None if not a valid tag
        """
        
        # Get tag type, opening | closing or return None if invalid
        TYPE_PATTERNS = { 
            "opening": re.compile(r"<((?:artist|album|cover|genre)=.+|(?:year|track)=\d+)>"),
            "closing": re.compile(r"<\/(artist|album|cover|genre|year|track)>")
        }

        tag_type = None
        for kind, pattern in TYPE_PATTERNS.items():
            if pattern.match(line):
                tag_type = kind 
        if not tag_type:
            return None
        
        # Assign metadata to add or remove
        tag_group = TYPE_PATTERNS[tag_type].match(line).groups()[0]
        tag_key = re.compile(r"(artist|album|cover|genre|year|track)").match(tag_group).group()
        
        # Tag opening, get string value/s after tag_key= and assign them, set to None if to be removed
        # Converts value to int if tag is a track tag
        metadata = {}
        if tag_type == "opening":
            tag_value = " ".join(tag_group.rsplit(f"{tag_key}="))[1:]

            metadata[tag_key] = tag_value
        else:
            metadata[tag_key] = ""
        
        return metadata
    

    def __get_song_line(self, line: str) -> dict[str, str] | None:
        """
        Gets the song title and URL. Line must be formatted as follows: URL TITLE

        Returns a dictionary with the url and title items, or None if wrongly formatted

        Args:
            line (str): Line to be read

        Returns:
            out (dict): Dictionary with title and url items
        """
        PATTERN = re.compile(r"((?:https?:\/\/)?(?:www\.)?[-a-zA-Z0-9@%._\+~#=]{2,256}\.[a-z]{2,6}\b(?:[-a-zA-Z0-9@:%_\+.~#?&\/=]*))(?: (.+))?")
        
        # Checks if line is formatted URL TITLE
        is_formatted = PATTERN.match(line)
        if not is_formatted:
            return None
        
        line_groups = PATTERN.match(line).groups()

        return {"url": line_groups[0], "title": line_groups[1]}
        
    def __get_url_type(self, url: str) -> str | None:
        """
        Gets the type of URL returning the following:
        - youtube-song: A youtube song 
        - spotify-song: A spotify song 
        - None: Not a valid URL

        Args:
            url (str): Song URL to validate

        Returns:
            out (str|None): Type of the url, None if invalid
        """
        PATTERNS = {
            "spotify-song": re.compile(r'https?://open\.spotify\.com\/track\/[A-Za-z0-9]+'),
            "youtube-song": re.compile(r'https?:\/\/(www\.)?(youtube\.com\/watch\?v=|youtu\.be\/)[A-Za-z0-9_-]+'),
        }

        for url_type, pattern in PATTERNS.items():
            if pattern.match(url):
                if not self.contains_spotify and url_type == "spotify-song":
                    self.contains_spotify = True
                return url_type
        return None

    def __parse_songs(self) -> list[Song] | FileNotFoundError:
        """
        Parses the read file list to generate every song and append it to self.songs

        Returns:
            out (list): List of Song objects
        """
        lines = self.__read_file()
        if lines is FileNotFoundError:
            return FileNotFoundError

        songs = []
        metadata = {
            "title": "",
            "artist": "",
            "album": "",
            "cover": "",
            "genre": "",
            "year": "",
            "track": ""
        }
        line_count = 1
        for line in lines:
            # Sanitize line of spaces and code characters at beggining/end of line
            # Skip if empty line
            line = line.strip()
            if line == "":
                continue

            # Read and Assign metadata if present and valid
            # continue to next iteration to skip song validation
            custom_metadata = self.__get_section_metadata(line)
            if custom_metadata:
                (key, value), = custom_metadata.items()
                metadata[key] = value
                continue

            # Read and assign song title and URL and append metadata if present and valid
            # continue to next iteration if song or URL not valid
            song = self.__get_song_line(line)
            if not song:
                print(f"[~] Warning: Invalid song at line {line_count}: {line}")
                continue
            
            title = song["title"]
            url_type = self.__get_url_type(song["url"])
            if not url_type:
                print(f"[~] Warning: Invalid song URL at line {line_count}: {line}")
                continue

            # Sanitize song for any ?list or additional URL queries if youtube song
            if url_type == "youtube-song":
                video_pattern = re.compile(r"https?:\/\/(www\.)?(youtube\.com\/watch\?v=|youtu\.be\/)[A-Za-z0-9_-]+")
                url = video_pattern.match(song["url"])[0]
            else: 
                url = song["url"]

            # Append song to song list
            songs.append(
                Song(
                    url=url,
                    url_type=url_type,
                    title=title,
                    artist=metadata["artist"],
                    album=metadata["album"],
                    cover=metadata["cover"],
                    genre=metadata["genre"],
                    year=metadata["year"],
                    track=metadata["track"]
                )
            )
            
            # Add track count if present in metadata
            if metadata["track"]:
                track_int = int(metadata["track"]) + 1
                metadata["track"] = str(track_int)

            line_count+=1
        
        # Return songs list
        return songs