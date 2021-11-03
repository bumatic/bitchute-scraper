[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.5539420.svg)](https://doi.org/10.5281/zenodo.5539420)

# Bitchute Scraper

Python scraper for the Bitchute video platform. It allows you to query for videos and to retrieve platform recommendations such as trending videos, popular videos or trending tags. It makes use of Selenium for retrieving data.

## Installation

bitchute-scraper is available on PyPi:

```Shell
$ pip3 install bitchute-scraper
```

Alternatively you can download the repository and install the package by running the setup.py install routine. Make sure to install the requirements as well:

```Shell
$ pip3 install -r requirements.txt
$ python3 setup.py install
```

## Usage

Create a crawler object and download it the trending videos and tags.

```Python
import bitchute as bc
b = bc.Crawler()        
recommended_videos, tags = b.get_recommended_videos(type='trending')
```

You can also retrieve videos listed in ```popular``` and ```all``` from the homepage as well. These request currently return a list of videos as well as a list of tags. The latter is an artifact of the current implementation and is to be ignored. (Will be fixed later.)

```Python
recommended_videos, tags = b.get_recommended_videos(type='popular')
recommended_videos, tags = b.get_recommended_videos(type='all')
```

Recommended channels can be retrieved via.

```Python
recommended_channels = b.get_recommended_channels(extended=False)
```

Retrieve channel information containing both the channel about as well as the videos published by the channel.

```Python
about, videos = b.get_channels(channel_ids, get_channel_about=True, get_channel_videos=True)
```

Search Videos (sorted by relevance only).

```Python
videos = search(query, top=100)
```
