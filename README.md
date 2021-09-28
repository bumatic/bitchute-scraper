# Python Bitchute Scraper

This repository contains a simple scaper for the bitcute video plattform and is WIP.


## Installation

For using the scraper you can download, clone or fork the repsoitory and put the ```bitchute``` folder in the working directory of your python script.

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
about, videos = b.(channel_ids, get_channel_about=True, get_channel_videos=True)
```

Search Videos (sorted by relevance only).

```Python
videos = search(query, top=100)
```
