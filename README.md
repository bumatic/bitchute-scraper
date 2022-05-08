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

Additionally this package requires Google Chrome and chromedriver to be installed on your system. Make sure that they are available.

``` bash
brew install --cask google-chrome
brew  install chromedriver
```

In addition to the python package the scraper makes use of the selenium chromedriver which is an application that programmatically controls the Google Chrome browser. While the package uses the webdriver-manager to ensure that the proper webdriver is installed on your system you need to make sure that Google Chrome is installed. On macOS you can install both easily with homebrew:

``` bash
brew install --cask google-chrome
```
On Linux and Windows installing Google Chrome should be straight forward as well. In case you don't know how to do this, just query it with the search engine of your trust!


## Usage

Create a crawler object and download the trending videos.

```Python
import bitchute as bc
b = bc.Crawler()        
trending_videos = b.get_trending_videos()
```

Besides videos the trending page lists tags that can be retrieved with.

```Python
trending_tags = b.get_trending_tags()
```

In case you want to retrieve both trending videos and trending tags at once, you can call.

```Python
trending_videos, trending_tags = b.get_trending()
```

You can also retrieve videos listed in ```popular``` and ```all``` from the homepage as well. 

```Python
popular_videos = b.get_popular_videos()
all_videos = b.get_all_videos()
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
