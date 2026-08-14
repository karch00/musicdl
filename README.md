# MusicDL

> [!WARNING]
> This is a personal project of mine curated to my tastes, needs and wants.
> Consider it unefficient, bloated or feature lacking at your own preference.

MusicDL is a **[yt-dlp](https://github.com/yt-dlp/yt-dlp)** wrapper meant to download music in bulk by reading
a xml-like formatted file with youtube/spotify song links and their titles or custom metadata.<br>
The main need behind creating this script was being able to add metadata at download, either automatically 
or manually.

By default, a simple list of `URL TITLE` lines will work to download the songs themselves, but unless the link has
spotify as source only the title will be added as metadata.

## Features

MusicDL offers some features to download your songs.

**Music format:** `mp3 @320` by default or `flac`<br>
**Spotify support:** Specifying path to a `.env` with ID and SECRET to a spotify app will allow spotify search.
Will gather basic metadata (Artist, album cover image) and apply it unless specified manually.<br>
**Youtube support:** A youtube link will initiate direct download and apply manually entered metadata<br>
**File based:** Core funcionality, a file formatted `xml`-like simplified style with the songs and metadata will
be the entry point for your songs to be downloaded

## Usage
### Basic usage
Once installed, to use it you will first need to create a file with your songs to download in bulk.<br>
It can be any format as long as the text inside is in plain text and readable (UTF-8).

Add your songs, **one per line**, following the format below: <br>
```
https://youtube.com/watch?v=dQw4w9WgXcQ Sample Title
```

### Adding metadata

Multiple tags can be nested as long as they are within different lines and unique to their line.<br>
Indentation is _**optional**_ but helps readability.<br>
Here are some examples.

**With one tag:**
```
<artist=Sample Artist>
        https://www.youtube.com/watch?v=t-BIwxvGRRI Sample Title
        https://www.youtube.com/watch?v=4G2pkt6btjs Sample Title 2
</artist>
```

**With multiple tags:**
```
<artist=Sample Artist>
    <album=Sample Album 1>
        https://www.youtube.com/watch?v=t-BIwxvGRRI Sample Title
        https://www.youtube.com/watch?v=4G2pkt6btjs Sample Title 2
    </album>
    <album=Sample Album 2>
        https://www.youtube.com/watch?v=iY4S2kMJzP4 Sample Title 3
        https://www.youtube.com/watch?v=ZItaF-CBd8E Sample Title 4
    </album>
</artist>
```

**All possible tags**<br>
With usage examples:
```
artist=Pink Floyd
album=Dark Side of the Moon
cover=https://domain.com/cover.png
genre=Progressive Rock
year=2000
track=10
```

### Executing command
For a file with youtube songs only, use as follows:
```bash
musicdl -f flac|mp3 -o /directory/to/download/songs songs_file
```

If using spotify links, a .env file with the `ID` and `SECRET` of a spotify app will be needed:
```bash
musicdl -f flac|mp3 -s /path/to/.env -o /directory/to/download/songs songs_file
```

By default the format will be `mp3` and the output directory will be `./music`.

**Additional flags:** `-v` for yt-dlp verbosity and `-h` for help 

## Requirements

Both `ffmpeg` and `python >= 3.13` are needed.

Additional support for yt-dlp challenges might be warned by yt-dlp download system, optional but recommended.<br>
Yt-dlp's github offers a guide on how to install it.

## Installing

Clone the repo
```bash
git clone https://github.com/karch00/musicdl && cd musicdl
```

And install
```bash
pip install .
```

Then get help on usage
```bash
musicdl -h
```
or
```bash
python3 -m musicdl -h
```