# Simple Python Bitchute Scraper

This repository contains a simple scaper for the bitcute video plattform and is WIP.


## Installation

For using the scraper you can download, clone or fork the repsoitory and put the ```bitchute``` folder in the working directory of your python script.

## Usage

Create a crawler object and download it the trending videos and tags:

```Python
import bitchute as bc
b = bc.Crawler()        
rv, tags = b.get_recommended_videos(type='trending')
```

You can retrieve ```popular``` and ```all``` videos from the homepage as well. These request currently a list of videos as well as a list of tags. The latter is an artefact of the implementation and is empty.

```Python
rv, tags = b.get_recommended_videos(type='popular')
rv, tags = b.get_recommended_videos(type='all')
```

Recommended channels can be retrieved via:

```Python
rc = b.get_recommended_channels(extended=False)
```

Channel information

```Python
about, videos = b.(channel_ids, get_channel_about=True, get_channel_videos=True)
```

Search Videos (sorted by relevance only)

```Python
 def search(query, top=100)
```