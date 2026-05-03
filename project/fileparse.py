import pathlib
from typing import Literal
import re
from project.songs import Song


class MusicList:
    """
    Music list class. Represents the music list file.

    Automatically parses file and creates songs with their respective metadata on class creation.

    ### Attributes:
    - path (str): File path
    """
    def __init__(self, path: str):
        self.path = path
        self.songs = self.__parse_songs__()
    

    def __read_file__(self) -> list[str]:
        """
        Reads file lines, returns a list with each read line.

        ### Returns:
        - out (list[str]): Lines read
        """
        if not pathlib.Path(self.path).exists():
            return FileNotFoundError
        
        with open(file=self.path, mode="r", encoding="utf-8") as f:
            return f.readlines()
    

    def __get_section_metadata__(self, line: str) -> dict[str, str|None] | None:
        """
        Gets the metadata set for the tag section in the line. Returns None if not a valid metadata tag

        ### Params:
        - line (str): Line to read for metadata tag

        ### Returns:
        - out (dict | None): Tag metadata to add/remove or None if not a valid tag
        """
        
        # Get tag type, opening | closing or return None if invalid
        TYPE_PATTERNS = { 
            "opening": re.compile(r"<((?:artist|album|cover|genre)=[\w ]+|(?:year|track)=\d+)>"),
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
            
            if tag_key == "track":
                tag_value = int(tag_value)

            metadata[tag_key] = tag_value
        else:
            metadata[tag_key] = None
        
        return metadata
    

    def __get_song_line__(self, line: str) -> dict[str, str] | None:
        """
        Gets the song title and URL. Line must be formatted as follows: URL TITLE

        Returns a dictionary with the url and title items, or None if wrongly formatted

        ### Params:
        - line (str): Line to be read

        ### Returns:
        - out (dict): Dictionary with title and url items
        """
        PATTERN = re.compile(r"((?:https?:\/\/)?(?:www\.)?[-a-zA-Z0-9@%._\+~#=]{2,256}\.[a-z]{2,6}\b(?:[-a-zA-Z0-9@:%_\+.~#?&\/=]*))(?: (.+))?")
        
        # Checks if line is formatted URL TITLE
        is_formatted = PATTERN.match(line)
        if not is_formatted:
            return None
        
        line_groups = PATTERN.match(line).groups()

        return {"url": line_groups[0], "title": line_groups[1]}
        


    def __get_url_type__(self, url: str) -> str | None:
        """
        Gets the type of URL returning the following:
        - **youtube-song**: A youtube song or a 
        - **spotify-song**: A spotify song or a 
        - None: Not a valid URL

        ### Returns:
        - out (str|None): Type of the url, None if invalid
        """
        PATTERNS = {
            "spotify-song": re.compile(r'https?://open\.spotify\.com/track/[A-Za-z0-9]+'),
            "youtube-song": re.compile(r'https?://(www\.)?(youtube\.com/watch\?v=|youtu\.be/)[A-Za-z0-9_-]+'),
        }

        for url_type, pattern in PATTERNS.items():
            if pattern.match(url):
                return url_type
        return None


    def __parse_songs__(self) -> list[Song] | FileNotFoundError:
        """
        Parses the read file list to generate every song and append it to self.songs

        ### Returns:
        - out (list): List of Song objects
        """
        lines = self.__read_file__()
        if lines is FileNotFoundError:
            return FileNotFoundError

        songs = []
        metadata = {
            "title": None,
            "artist": None,
            "album": None,
            "cover": None,
            "genre": None,
            "year": None,
            "track": None
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
            custom_metadata = self.__get_section_metadata__(line)
            if custom_metadata:
                (key, value), = custom_metadata.items()
                metadata[key] = value
                continue

            # Read and assign song title and URL and append metadata if present and valid
            # continue to next iteration if song or URL not valid
            song = self.__get_song_line__(line)
            if not song:
                print(f"Warning: Invalid song at line {line_count}: {line}")
                continue
            
            title = song["title"]
            url = song["url"]
            url_type = self.__get_url_type__(url)
            if not url_type:
                print(f"Warning: Invalid song URL at line {line_count}: {line}")
                continue

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
            if not metadata["track"] is None:
                metadata["track"] += 1

            line_count+=1
        
        # Return songs list
        return songs