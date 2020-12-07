# Simple Python module for retrieving data from bitchute.
# Copyright (C) 2020 Marcus Burkhardt
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.



#from datetime import timedelta  # datetime, date,
#from dateutil.relativedelta import relativedelta
#import csv

import time
import datetime
import markdownify
import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import dateutil 
from datetime import datetime


class Crawler():
    def __init__(self, headless=True):
        
        self.options = Options()
        if headless:
            self.options.add_argument('--headless')
        self.options.add_argument('--disable-dev-shm-usage')
        self.status = []
        self.bitchute_base = 'https://www.bitchute.com/'
        self.channel_base = 'https://www.bitchute.com/channel/{}/'
        self.video_base = 'https://www.bitchute.com/video/{}/'
        self.profile_base = 'https://www.bitchute.com/profile/{}/'
        self.search_base = 'https://www.bitchute.com/search/?query={}&kind=video'
        
    
    def call(self, url, click_link_text=None, scroll=True, top=None):
        wd = webdriver.Chrome(ChromeDriverManager().install(), options=self.options)
        print('Retrieving: ' + url + ' ', end='')
        self.set_status('Retrieving: ' + url)

        wd.get(url)
        time.sleep(2)
        #return wd

        if len(wd.find_elements_by_xpath('//button[normalize-space()="Dismiss"]')) > 0:
            time.sleep(2)
            wd.find_element_by_xpath('//button[normalize-space()="Dismiss"]').click()
            
        if click_link_text and not len(wd.find_elements(By.PARTIAL_LINK_TEXT, click_link_text))>0:
            time.sleep(5)
        
        if click_link_text:
            if len(wd.find_elements(By.PARTIAL_LINK_TEXT, click_link_text))>0:
                time.sleep(2)
                wd.find_element_by_partial_link_text(click_link_text).click()
                time.sleep(2)
            else:
                print('Cannot find link to click')

        sensitivity = 'Some videos are not shown'
        if len(wd.find_elements(By.PARTIAL_LINK_TEXT, sensitivity))>0:
            wd.find_element_by_partial_link_text(sensitivity).click()
            time.sleep(2)

        if scroll:
            if top:
                iterations = (top//10) + (top % 10 > 0)
                iteration = 1
                increment = 1

            else:
                iterations = 1
                iteration = 0
                increment = 0

            script = (
                'window.scrollTo(0, document.body.scrollHeight);'
                'var lenOfPage=document.body.scrollHeight;'
                'return lenOfPage;'
            )

            lenOfPage = wd.execute_script(script)
            match = False
            while not match and iteration < iterations:
                iteration += increment
                print('.', end='')
                self.set_status('.')
                lastCount = lenOfPage
                time.sleep(4)
                lenOfPage = wd.execute_script(script)
                if lastCount == lenOfPage:
                    match = True
        print('')

        page_source = wd.page_source
        wd.close()

        return page_source
        

    def parser(self, src, type=None, extended=False):
        scrape_time = str(time.time())
        if not type:
            raise 'A parse type needs to be passed.'
        elif type == 'recommended_channels':
            channels = []
            channel_ids = []
            soup = BeautifulSoup(src, 'html.parser')
            if soup.find(id='carousel'):
                for item in soup.find(id='carousel').find_all(class_='channel-card'):
                    id_ = item.find('a').get('href').split('/')[-2]
                    name = item.find(class_='channel-card-title').text
                    channels.append([id_, name, scrape_time])
                    channel_ids.append(id_)
            if extended:
                channel_ids = list(set(channel_ids))
                channels, videos = self.get_channels(channel_ids, get_channel_videos=False)
            else:
                columns = ['id', 'name', 'scrape_time']
                channels = pd.DataFrame(channels, columns=columns)
                channels = channels.drop_duplicates(subset=['id'])
            return channels

        
        elif type == 'video_search':
            videos = []
            soup = BeautifulSoup(src, 'html.parser')
            if soup.find(class_='results-list'):
                counter = 0
                for result in soup.find(class_='results-list').find_all(class_='video-result-container'):
                    counter += 1
                    title = None
                    id_ = None
                    view_count = None
                    duration = None
                    channel = None
                    channel_url = None
                    description = None
                    description_links = []
                    created_at = None

                    if result.find(class_='video-result-title'):
                        title = result.find(class_='video-result-title').text
                        id_ = result.find(class_='video-result-title').find('a').get('href').split('/')[-2]

                    if result.find(class_='video-views'):
                        view_count = result.find(class_='video-views').text.strip()

                    if result.find(class_='video-duration'):
                        duration = result.find(class_='video-duration').text.strip()

                    if result.find(class_='video-result-channel'):
                        channel = result.find(class_='video-result-channel').text
                        channel_url = result.find(class_='video-result-channel').find('a').get('href')

                    if result.find(class_='video-result-text'):
                        description = result.find(class_='video-result-text').decode_contents()
                        description = description.strip('\n')
                        description = markdownify.markdownify(description)

                        for link in result.find(class_='video-result-text').find_all('a'):
                            description_links.append(link.get('href'))

                    if result.find(class_='video-result-details'):
                        created_at = result.find(class_='video-result-details').text

                    
                    videos.append([counter, id_, title, view_count, duration, channel, channel_url, description, description_links, created_at, scrape_time])

            videos_columns = ['counter', 'id', 'title', 'view_count', 'duration', 'channel', 'channel_url', 'description', 'description_links', 'created_at', 'scrape_time']
            videos = pd.DataFrame(videos, columns=videos_columns)
            return videos

                    

        elif type == 'recommended_videos':
            videos = []
            tags = []
            soup = BeautifulSoup(src, 'html.parser')
            if soup.find(class_='video-card'):
                counter = 0
                for video in soup.find_all(class_='video-card'):
                    counter += 1
                    title = None
                    id_ = None
                    view_count = None
                    duration = None
                    channel = None
                    channel_url = None
                    created_at = None

                    if video.find(class_='video-card-title'):
                        title = video.find(class_='video-card-title').text
                    if video.find(class_='video-card-id'):
                        id_ = video.find(class_='video-card-id').text
                    if video.find(class_='video-views'):
                        view_count = video.find(class_='video-views').text
                    if video.find(class_='video-duration'):
                        duration = video.find(class_='video-duration').text
                    if video.find(class_='video-card-channel'):
                        channel = video.find(class_='video-card-channel').text
                        channel_url = video.find(class_='video-card-channel').find('a').get('href')
                    if video.find(class_='video-card-published'):
                        created_at = video.find(class_='video-card-published').text
                    videos.append([counter, id_, title, view_count, duration, channel, channel_url, created_at, scrape_time])
            
            if soup.find(class_='sidebar tags'):
                for tag in soup.find(class_='sidebar tags').find_all('li'):
                    tag_name = tag.text 
                    tag_url = tag.find('a').get('href')
                    tags.append([tag_name, tag_url, scrape_time])

            
            videos_columns = ['counter', 'id', 'title', 'view_count', 'duration', 'channel', 'channel_url', 'created_at', 'scrape_time']
            videos = pd.DataFrame(videos, columns=videos_columns)

            tags_columns = ['tag_name', 'tag_url', 'scrape_time']
            tags = pd.DataFrame(tags, columns=tags_columns)

            return videos, tags

        elif type == 'channel_about':
            id_ = None
            title = None
            owner = None
            owner_link = None
            description = None
            description_links = []
            social_links = []
            category = None
            video_count = None
            subscriber_count = None
            view_count = None
            created_at = None

            soup = BeautifulSoup(src, 'html.parser')            
            if soup.find('link', id='canonical'):
                id_ = soup.find('link', id='canonical').get('href').split('/')[-2]
            if soup.find(class_='name'):
                title = soup.find(class_='name').text
            if soup.find(class_='owner'):
                owner = soup.find(class_='owner').text
                owner_link = soup.find(class_='owner').find('a').get('href')
            if soup.find(id='channel-description'):
                description = soup.find(id='channel-description').decode_contents()
                description = description.strip('\n')
                description = markdownify.markdownify(description)
                for link in soup.find(id='channel-description').find_all('a'):
                    description_links.append(link.get('href'))
            if soup.find(class_='social'):
                for link in soup.find(class_='social').find_all('a'):
                    social_links.append([link.get('data-original-title'), link.get('href')])
            if soup.find(class_='channel-about-details'):
                for elem in soup.find(class_='channel-about-details').find_all('p'):
                    if 'Category' in elem.text and elem.find('a'):
                        category = elem.find('a').text
                    elif elem.find(class_='fa-video'):
                        video_count = elem.text.split(' ')[1]
                    elif elem.find(class_='fa-users'):
                        subscriber_count = elem.text.split(' ')[1]
                    elif elem.find(class_='fa-eye'):
                        view_count = elem.text.split(' ')[1]
                    else:
                        created_at = elem.text
                        pass
            data = [id_, title, social_links, description, description_links, video_count, subscriber_count, view_count, created_at, category, social_links, owner, owner_link, scrape_time]
            columns = ['id', 'title', 'social_links', 'description', 'description_links', 'video_count', 'subscriber_count', 'view_count', 'created_at', 'category', 'social_links', 'owner', 'owner_link', 'scrape_time']
            data = pd.DataFrame([data], columns=columns)
            return data

        elif type == 'channel_videos':
            soup = BeautifulSoup(src, 'html.parser')
            data = []

            if soup.find('link', id='canonical').get('href'):
                channel_id = soup.find('link', id='canonical').get('href').split('/')[-2]
            else:
                channel_id = None
            if soup.find(class_='name'):
                channel_title = soup.find(class_='name').text
            else:
                channel_title = None
            if soup.find(class_='channel-videos-list'):
                for video in soup.find(class_='channel-videos-list').find_all(class_='channel-videos-container'):
                    if video.find(class_='channel-videos-title'):
                        title = video.find(class_='channel-videos-title').text
                        link = video.find(class_='channel-videos-title').find('a').get('href')
                    else:
                        title = None
                        link = None
                    if video.find(class_='channel-videos-text'):
                        description = video.find(class_='channel-videos-text').decode_contents()
                        description = description.strip('\n')
                        description = markdownify.markdownify(description)
                        description_links = [a.get('href') for a in video.find(class_='channel-videos-text').find_all('a')]
                    else:
                        description = None
                        description_links = []
                    if video.find(class_='video-duration'):
                        duration = video.find(class_='video-duration').text
                    else:
                        duration = None
                    if video.find(class_='channel-videos-details'):
                        created_at = str(dateutil.parser.parse( video.find(class_='channel-videos-details').text.replace('\n', '')).date())
                    else:
                        created_at = None
                    if video.find(class_='video-views'):
                        view_count = video.find(class_='video-views').text.strip()
                    else:
                        view_count = None

                    data.append([channel_id, channel_title, title, link, created_at, duration, view_count, description, description_links, scrape_time])
            
            columns = ['channel_id', 'channel_title', 'title', 'link', 'created', 'duration', 'view_count', 'description', 'description_links']
            data = pd.DataFrame(data, columns=columns)
            return data
            
        else:
            print('A correct type needs to be passed.')

    
    def search(self, query, top=100):
        '''
        Queries Bitchute and retrieves top n results according to the relevance ranking.

        Parameters:
        query (str): Search string
        top (int): Number of results to be retrieved

        Returns:
        data: Dataframe of search results.
        '''
        url = self.search_base.format(query)
        src = self.call(url, top=top)
        data = self.parser(src, type='video_search')
        return data
        

    def get_recommended_videos(self, type='popular'):
        '''
        Scapes recommended videos on bitchute homepage.

        Parameters:
        type (str): POPULAR, TRENDING, ALL

        Returns:
        data: Dataframe of recommended videos.
        '''
        if type == 'popular':
            src = self.call(self.bitchute_base)
            data = self.parser(src, type='recommended_videos')
            return data
        elif type == 'trending':
            src = self.call(self.bitchute_base, click_link_text='TRENDING')
            data = self.parser(src, type='recommended_videos')
            return data
        elif type == 'all':
            src = self.call(self.bitchute_base, click_link_text='ALL')
            data = self.parser(src, type='recommended_videos')
            return data
        else:
            print('Wrong type. Accepted types are popular, trending and all.')
            return None

    def get_recommended_channels(self, extended=True):
        '''
        Scapes recommended channels on bitchute homepage.

        Parameters:
        extended (bool): whether to retrieve extended channel information. Default: True

        Returns:
        data: Dataframe of recommended channels.
        '''
        src = self.call(self.bitchute_base, scroll=False)
        data = self.parser(src, type='recommended_channels', extended=extended)
        return data

    def get_channel(self, channel_id, get_channel_about=True, get_channel_videos=True):
        '''
        Scapes channel information.

        Parameters:
        channel_id (str): ID of channel to be scraped.
        get_channel_about (bool): Get the about information by a channel. Default:True 
        get_channel_videos (bool): Get the information of videos published by a channel. Default:True

        Returns:
        about_data: Dataframe of channel about.
        videos_data: Dataframe of channel videos.
        '''

        if get_channel_about:
            channel_about_url = self.channel_base.format(channel_id)
            src = self.call(channel_about_url, click_link_text='ABOUT', scroll=False)
            about_data = self.parser(src, type='channel_about')
        else:
            about_data = pd.DataFrame()

        if get_channel_videos:
            channel_videos_url = self.channel_base.format(channel_id)
            src = self.call(channel_videos_url, click_link_text='VIDEOS')
            videos_data = self.parser(src, type='channel_videos')
        else:
            videos_data = pd.DataFrame()

        return about_data, videos_data

    def get_channels(self, channel_ids, get_channel_about=True, get_channel_videos=True):
        '''
        Scapes information for multiple channels.

        Parameters:
        channel_ids (list): List of channel ids to be scraped.
        get_channel_about (bool): Get the about information by a channel. Default:True 
        get_channel_videos (bool): Get the information of videos published by a channel. Default:True

        Returns:
        abouts: Dataframe of channel abouts.
        videos: Dataframe of channel videos.
        '''
        if type(channel_ids) == str:
            return self.get_channel(channel_ids, get_channel_about=get_channel_about, get_channel_videos=get_channel_videos)
        elif type(channel_ids) == list:
            abouts = pd.DataFrame()
            videos = pd.DataFrame()
            for channel_id in channel_ids:
                about_tmp, videos_tmp = self.get_channel(channel_id, get_channel_about=get_channel_about, get_channel_videos=get_channel_videos)
                abouts = abouts.append(about_tmp)
                videos = videos.append(videos_tmp)
            return abouts, videos
        else:
            print('channel_ids must be of type list for multiple or str for single channels')
            return None
    
    def get_status(self, reset=True):
        status = self.status
        if reset:
            self.status
        return status
    
    def set_status(self, message):
        self.status.append(message)
    
    
'''
class Entity():
    def __init__(self):
        self.id = None
        self.name = None
        self.created = None
        self.crawl_date = None

    def calculate_date_created(self, crawl_date, created_at):
        pass

    def set_data(self, id_=None, name=None, created=None, crawl_date=None):
        if id_:
            self.id = id_
        if name:
            self.name = name
        if created:
            self.created = created
        if crawl_date:
            self.crawl_date = crawl_date


class Video(Entity):
    def __init__(self):
        pass


class Channel(Entity):
    def __init__(self):
        pass


class Recommendations(Entity):
    def __init__(self):
        pass


class (Entity):
    def __init__(self):
        pass

'''

