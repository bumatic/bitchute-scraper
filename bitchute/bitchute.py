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


import time
import markdownify
import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from dateutil import parser
from tqdm import tqdm
from datetime import datetime
from retrying import retry


class Crawler():
    def __init__(self, headless=True, verbose=False, chrome_driver=None):
        self.options = Options()
        if headless:
            self.options.add_argument('--headless')
        self.options.add_argument('--disable-dev-shm-usage')
        self.options.add_argument('--no-sandbox')
        self.chrome_driver = chrome_driver
        self.wd = None
        self.status = []
        self.verbose = verbose
        self.bitchute_base = 'https://www.bitchute.com/'
        self.channel_base = 'https://www.bitchute.com/channel/{}/'
        self.video_base = 'https://www.bitchute.com/video/{}/'
        self.hashtag_base = 'https://www.bitchute.com/hashtag/{}/'
        self.profile_base = 'https://www.bitchute.com/profile/{}/'
        self.search_base = 'https://www.bitchute.com/search/?query={}&kind=video'

    def create_webdriver(self):
        if not self.chrome_driver:
            self.wd = webdriver.Chrome(ChromeDriverManager().install(), options=self.options)
        else:
            self.wd = webdriver.Chrome(self.chrome_driver, options=self.options)
    
    def reset_webdriver(self):
        #self.wd.close()
        if self.wd:
            self.wd.quit()
        self.wd = None

    @retry(stop_max_attempt_number=5, wait_random_min=1000, wait_random_max=2000)
    def call(self, url, click_link_text=None, scroll=True, top=None):
        if not self.wd:
            self.create_webdriver()
        if self.verbose:
            print('Retrieving: ' + url + ' ', end='')
        self.set_status('Retrieving: ' + url)
        
        if self.wd.current_url == url:
            self.wd.get('about:blank')
            self.wd.get(url)
        else:
            self.wd.get(url)
        
        time.sleep(2)

        if len(self.wd.find_elements_by_xpath('//button[normalize-space()="Dismiss"]')) > 0:
            time.sleep(2)
            self.wd.find_element_by_xpath('//button[normalize-space()="Dismiss"]').click()
            
        if click_link_text and not len(self.wd.find_elements(By.PARTIAL_LINK_TEXT, click_link_text))>0:
            time.sleep(5)
        
        if click_link_text:
            if len(self.wd.find_elements(By.PARTIAL_LINK_TEXT, click_link_text))>0:
                time.sleep(2)
                self.wd.find_element_by_partial_link_text(click_link_text).click()
                time.sleep(2)
            else:
                print('Cannot find link to click')

        sensitivity = 'Some videos are not shown'
        if len(self.wd.find_elements(By.PARTIAL_LINK_TEXT, sensitivity))>0:
            self.wd.find_element_by_partial_link_text(sensitivity).click()
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

            lenOfPage = self.wd.execute_script(script)
            match = False
            while not match and iteration < iterations:
                iteration += increment
                if self.verbose:
                    print('.', end='')
                self.set_status('.')
                lastCount = lenOfPage
                time.sleep(4)
                lenOfPage = self.wd.execute_script(script)
                if lastCount == lenOfPage:
                    match = True
        if self.verbose:
            print('')

        page_source = self.wd.page_source
        return page_source
    
    def process_views(self, views):
        if "k" in views or "K" in views:
            views = views.replace('K', '').replace('k', '')
            if '.' not in views:
                views = views[:-1]+'.'+views[-1:]
            views = float(views) * 1000
        elif "m" in views or "M" in views:
            views = views.replace('M', '').replace('m', '')
            if '.' not in views:
                views = views[:-1]+'.'+views[-1:]
            views = float(views) * 1000000
        return int(views)

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
        self.reset_webdriver()
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
            data = self.parser(src, type='recommended_videos', kind='popular')
            return data
        elif type == 'trending':
            src = self.call(self.bitchute_base, click_link_text='TRENDING')
            data = self.parser(src, type='recommended_videos', kind='trending-day')
            return data
        elif type == 'trending-day':
            src = self.call(self.bitchute_base, click_link_text='TRENDING')
            data = self.parser(src, type='recommended_videos', kind='trending-day')
            return data
        elif type == 'trending-week':
            src = self.call(self.bitchute_base, click_link_text='TRENDING')
            data = self.parser(src, type='recommended_videos', kind='trending-week')
            return data
        elif type == 'trending-month':
            src = self.call(self.bitchute_base, click_link_text='TRENDING')
            data = self.parser(src, type='recommended_videos', kind='trending-month')
            return data
        elif type == 'all':
            src = self.call(self.bitchute_base, click_link_text='ALL')
            data = self.parser(src, type='recommended_videos', kind='all')
            return data
        else:
            print('Wrong type. Accepted types are popular, trending and all.')
            return None
        self.reset_webdriver()

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
        self.reset_webdriver()
        return data

    def _get_channel(self, channel_id, get_channel_about=True, get_channel_videos=True):
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
            abouts, videos = self._get_channel(channel_ids, get_channel_about=get_channel_about, get_channel_videos=get_channel_videos)
            self.reset_webdriver()
            return abouts, videos
        elif type(channel_ids) == list:
            abouts = pd.DataFrame()
            videos = pd.DataFrame()
            for channel_id in (tqdm(channel_ids) if not self.verbose else channel_ids):
                about_tmp, videos_tmp = self._get_channel(channel_id, get_channel_about=get_channel_about, get_channel_videos=get_channel_videos)
                abouts = abouts.append(about_tmp)
                videos = videos.append(videos_tmp)
            self.reset_webdriver()
            return abouts, videos
        else:
            print('channel_ids must be of type list for multiple or str for single channels')
            return None

    
    def _get_video(self, video_id):
        '''
        Scrapes video metadata.

        Parameters:
        video_id (str): ID of video to be scraped.
        
        Returns:
        video_data: Dataframe of video metadata.
        '''

        video_url = self.video_base.format(video_id)
        src = self.call(video_url)
        video_data = self.parser(src, type='video')
        return video_data

    def get_videos(self, video_ids):
        '''
        Scapes metadata of multiple videos.

        Parameters:
        video_ids (list): List of video ids to be scraped.
        
        Returns:
        video_data: Dataframe of video metadata.
        '''

        if type(video_ids) == str:
            try:
                video_data = self._get_video(video_ids)
                self.reset_webdriver()
                return video_data
            except:
                print('Failed for video with id {}'.format(video_ids))
        elif type(video_ids) == list:
            video_data = pd.DataFrame()
            for video_id in (tqdm(video_ids) if not self.verbose else video_ids):
                try:
                    video_tmp = self._get_video(video_id)                
                    video_data = video_data.append(video_tmp)
                except:
                    print('Failed for video with id {}'.format(video_id))
                    self.reset_webdriver()
            self.reset_webdriver()
            return video_data
        else:
            print('video_ids must be of type list for multiple or str for single video')
            return None 

    def _get_hashtag(self, hashtag):
        '''
        Scapes video posted with a tag.

        Parameters:
        tag (str): Hashtag to be scraped.
        
        Returns:
        video_data: Dataframe of video metadata.
        '''
        hashtag_url = self.hashtag_base.format(hashtag)
        src = self.call(hashtag_url)
        video_data = self.parser(src, type='hashtag_videos')
        video_data['hashtag'] = hashtag
        return video_data

    def get_hashtags(self, hashtags):
        '''
        Scapes video posted with a tag.

        Parameters:
        tag (str): Hashtag to be scraped.
        
        Returns:
        video_data: Dataframe of video metadata.
        '''

        if type(hashtags) == str:
            video_data = self._get_hashtag(hashtags)
            video_data['hashtag'] = hashtags
            self.reset_webdriver()   
            return video_data
        elif type(hashtags) == list:
            video_data = pd.DataFrame()
            for hashtag in (tqdm(hashtags) if not self.verbose else hashtags):
                video_tmp = self._get_hashtag(hashtag)
                video_tmp['hashtag'] = hashtag             
                video_data = video_data.append(video_tmp)
            self.reset_webdriver()
            return video_data
        else:
            print('hashtags must be of type list for multiple or str for single hashtag')
            return None 

    def parser(self, src, type=None, kind=None, extended=False):
        scrape_time = str(int(datetime.utcnow().timestamp()))
        if not type:
            raise 'A parse type needs to be passed.'
        
        elif type == 'video_search' or type == 'hashtag_videos':
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
                        title = result.find(class_='video-result-title').text.strip('\n').strip()
                        id_ = result.find(class_='video-result-title').find('a').get('href').split('/')[-2]

                    if result.find(class_='video-views'):
                        view_count = self.process_views(result.find(class_='video-views').text.strip('\n').strip())

                    if result.find(class_='video-duration'):
                        duration = result.find(class_='video-duration').text.strip('\n').strip()

                    if result.find(class_='video-result-channel'):
                        channel = result.find(class_='video-result-channel').text.strip('\n').strip()
                        channel_id = result.find(class_='video-result-channel').find('a').get('href').split('/')[-2]

                    if result.find(class_='video-result-text'):
                        description = result.find(class_='video-result-text').decode_contents()
                        description = description.strip('\n')
                        description = markdownify.markdownify(description)

                        for link in result.find(class_='video-result-text').find_all('a'):
                            description_links.append(link.get('href'))

                    if result.find(class_='video-result-details'):
                        created_at = result.find(class_='video-result-details').text.strip('\n').strip()

                    
                    videos.append([counter, id_, title, view_count, duration, channel, channel_id, description, description_links, created_at, scrape_time])

            videos_columns = ['rank', 'id', 'title', 'view_count', 'duration', 'channel', 'channel_id', 'description', 'description_links', 'created_at', 'scrape_time']
            videos = pd.DataFrame(videos, columns=videos_columns)
            return videos

        elif type == 'recommended_channels':
            channels = []
            channel_ids = []
            soup = BeautifulSoup(src, 'html.parser')
            counter = 0
            if soup.find(id='carousel'):
                for item in soup.find(id='carousel').find_all(class_='channel-card'):
                    counter += 1
                    id_ = item.find('a').get('href').split('/')[-2]
                    name = item.find(class_='channel-card-title').text
                    channels.append([counter, id_, name, scrape_time])
                    channel_ids.append(id_)
            if extended:
                channel_ids = list(set(channel_ids))
                channels, videos = self.get_channels(channel_ids, get_channel_videos=False)
            else:
                columns = ['rank', 'id', 'name', 'scrape_time']
                channels = pd.DataFrame(channels, columns=columns)
                channels = channels.drop_duplicates(subset=['id'])
            return channels

        
        elif type == 'recommended_videos':
            videos = []
            tags = []
            soup = BeautifulSoup(src, 'html.parser')

            if kind == 'popular':
                if soup.find(id='listing-popular'):
                    soup = soup.find(id='listing-popular')
                else:
                    return None
                
            elif kind == 'trending-day':
                if soup.find(id='trending-day'):
                    soup = soup.find(id='trending-day')
                else:
                    return None

            elif kind == 'trending-week':
                if soup.find(id='trending-week'):
                    soup = soup.find(id='trending-week')
                else:
                    return None

            elif kind == 'trending-month':
                if soup.find(id='trending-month'):
                    soup = soup.find(id='trending-month')
                else:
                    return None
    
            elif kind == 'all':
                if soup.find(id='listing-all'):
                    soup = soup.find(id='listing-all')
                else:
                    return None
            else:
                print('kind needs to be passed for recommendations.')
                return None

            if soup.find(class_='video-result-container'):
                counter = 0
                for video in soup.find_all(class_='video-result-container'):
                    counter += 1
                    title = None
                    id_ = None
                    view_count = None
                    duration = None
                    channel = None
                    channel_url = None
                    created_at = None

                    if video.find(class_='video-result-title'):
                        title = video.find(class_='video-result-title').text.strip('\n')
                        id_ = video.find(class_='video-result-title').find('a').get('href').split('/')[-2]
                    
                    if video.find(class_='video-views'):
                        view_count = self.process_views(video.find(class_='video-views').text.strip('\n'))
                    if video.find(class_='video-duration'):
                        duration = video.find(class_='video-duration').text.strip('\n')
                    
                    if video.find(class_='video-result-channel'):
                        channel = video.find(class_='video-result-channel').text.strip('\n')
                        channel_id = video.find(class_='video-result-channel').find('a').get('href').split('/')[-2]
                    if video.find(class_='video-result-details'):
                        created_at = video.find(class_='video-result-details').text.strip('\n')
                    videos.append([counter, id_, title, view_count, duration, channel, channel_id, created_at, scrape_time])

            elif soup.find(class_='video-card'):
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
                        title = video.find(class_='video-card-title').text.strip('\n').strip()
                    if video.find(class_='video-card-id'):
                        id_ = video.find(class_='video-card-id').text.strip('\n').strip()
                    if video.find(class_='video-views'):
                        view_count = self.process_views(video.find(class_='video-views').text.strip('\n').strip())
                    if video.find(class_='video-duration'):
                        duration = video.find(class_='video-duration').text.strip('\n').strip()
                    if video.find(class_='video-card-channel'):
                        channel = video.find(class_='video-card-channel').text.strip('\n').strip()
                        channel_id = video.find(class_='video-card-channel').find('a').get('href').split('/')[-2]
                    if video.find(class_='video-card-published'):
                        created_at = video.find(class_='video-card-published').text.strip('\n').strip()
                    videos.append([counter, id_, title, view_count, duration, channel, channel_id, created_at, scrape_time])
            
            
            soup = BeautifulSoup(src, 'html.parser')
            if soup.find(class_='sidebar tags'):
                counter = 0
                for tag in soup.find(class_='sidebar tags').find_all('li'):
                    counter += 1
                    tag_name = tag.text.strip('\n').strip()
                    tag_url = tag.find('a').get('href')
                    tags.append([counter, tag_name, tag_url, scrape_time])
            
            videos_columns = ['rank', 'id', 'title', 'view_count', 'duration', 'channel', 'channel_id', 'created_at', 'scrape_time']
            videos = pd.DataFrame(videos, columns=videos_columns)

            tags_columns = ['rank', 'tag_name', 'tag_url', 'scrape_time']
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
                title = soup.find(class_='name').text.strip('\n').strip()
            if soup.find(class_='owner'):
                owner = soup.find(class_='owner').text.strip('\n').strip()
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
                        category = elem.find('a').text.strip('\n').strip()
                    elif elem.find(class_='fa-video'):
                        video_count = elem.text.split(' ')[1]
                    elif elem.find(class_='fa-users'):
                        subscriber_count = elem.text.split(' ')[1]
                    elif elem.find(class_='fa-eye'):
                        view_count = self.process_views(elem.text.split(' ')[1])
                    else:
                        created_at = elem.text.strip('\n').strip()
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
                channel_title = soup.find(class_='name').text.strip('\n')
            else:
                channel_title = None
            if soup.find(class_='channel-videos-list'):
                for video in soup.find(class_='channel-videos-list').find_all(class_='channel-videos-container'):
                    if video.find(class_='channel-videos-title'):
                        title = video.find(class_='channel-videos-title').text.strip('\n')
                        video_id = video.find(class_='channel-videos-title').find('a').get('href').split('/')[-2]
                    else:
                        title = None
                        video_id = None
                    if video.find(class_='channel-videos-text'):
                        description = video.find(class_='channel-videos-text').decode_contents()
                        description = description.strip('\n')
                        description = markdownify.markdownify(description)
                        description_links = [a.get('href') for a in video.find(class_='channel-videos-text').find_all('a')]
                    else:
                        description = None
                        description_links = []
                    if video.find(class_='video-duration'):
                        duration = video.find(class_='video-duration').text.strip('\n').strip()
                    else:
                        duration = None
                    if video.find(class_='channel-videos-details'):
                        created_at = str(parser.parse( video.find(class_='channel-videos-details').text.replace('\n', '')).date())
                    else:
                        created_at = None
                    if video.find(class_='video-views'):
                        view_count = self.process_views(video.find(class_='video-views').text.strip('\n').strip())
                    else:
                        view_count = None

                    data.append([channel_id, channel_title, video_id, title, created_at, duration, view_count, description, description_links, scrape_time])
            
            columns = ['channel_id', 'channel_title', 'video_id', 'title', 'created', 'duration', 'view_count', 'description', 'description_links', 'scrape_time']
            data = pd.DataFrame(data, columns=columns)
            return data
            
        elif type == 'video':
            id_ = None
            title = None
            description = None
            description_links = []
            view_count = None
            like_count = None
            dislike_count = None
            created_at = None
            hashtags = []
            category = None
            sensitivity = None
            channel_name = None
            channel_id = None
            owner_name = None
            owner_id = None
            subscribers = None
            next_id = None
            related_ids = []

            soup = BeautifulSoup(src, 'html.parser')
            
            if soup.find(id='canonical'):
                id_ = soup.find(id='canonical').get('href').split('/')[-2]
            if soup.find(id='video-title'):
                title = soup.find(id='video-title').text.strip('\n').strip()
            if soup.find(id='video-view-count'):
                view_count = self.process_views(soup.find(id='video-view-count').text.strip('\n').strip())
            if soup.find(id='video-like-count'):
                like_count = soup.find(id='video-like-count').text.strip('\n').strip()
            if soup.find(id='video-dislike-count'):
                dislike_count = soup.find(id='video-dislike-count').text.strip('\n').strip()
            if soup.find(class_='video-publish-date'):
                created_at = soup.find(class_='video-publish-date').text.strip('\n').strip().replace('First published at ', '')
                created_at = parser.parse(created_at)

            if soup.find(id='video-hashtags'):
                if soup.find(id='video-hashtags').find('li'):
                    for tag in soup.find(id='video-hashtags').find_all('li'):
                        hashtags.append(tag.text.strip('\n'))
            if soup.find(id='video-description'):
                description = soup.find(id='video-description').decode_contents()
                description = description.strip('\n')
                description = markdownify.markdownify(description)

                if soup.find(id='video-description').find('a'):
                    for link in soup.find(id='video-description').find_all('a'):
                        description_links.append(link.get('href'))
            if soup.find(class_='video-detail-list'):
                if soup.find(class_='video-detail-list').find('tr'):
                    for row in soup.find(class_='video-detail-list').find_all('tr'):
                        value = row.find('a').text
                        if 'Category' in row.text:
                            category = value
                        elif 'Sensitivity' in row.text:
                            sensitivity = value
            if soup.find(class_='channel-banner'):
                channel_data = soup.find(class_='channel-banner')
                if channel_data.find(class_='name'):
                    channel_name = channel_data.find(class_='name').text.strip('\n').strip()
                    channel_id = channel_data.find(class_='name').find('a').get('href').split('/')[-2]
                if channel_data.find(class_='owner'):
                    owner_name = channel_data.find(class_='owner').text.strip('\n').strip()
                    owner_id = channel_data.find(class_='owner').find('a').get('href').split('/')[-2]
                if channel_data.find(class_='subscribers'):
                    subscribers = channel_data.find(class_='subscribers').text.replace('subscribers', '').strip()

            if soup.find(class_='sidebar-next'):
                if soup.find(class_='sidebar-next').find(class_='video-card-title'):
                    next_id = soup.find(class_='sidebar-next').find(class_='video-card-title').find('a').get('href').split('/')[-2]

            if soup.find(class_='sidebar-recent'):
                if soup.find(class_='sidebar-recent').find(class_='video-card-title'):
                    for item in soup.find(class_='sidebar-recent').find_all(class_='video-card-title'):
                        related_ids.append(item.find('a').get('href').split('/')[-2])

            columns = ['id', 'title', 'description', 'description_links', 'view_count', 'like_count', 'dislike_count', 'created', 'hashtags', 'category', 'sensitivity', 'channel_name', 'channel_id', 'owner_name', 'owner_id', 'subscriber_count', 'next_video', 'releated_videos']
            data = pd.DataFrame([[id_, title, description, description_links, view_count, like_count, dislike_count, created_at, hashtags, category, sensitivity, channel_name, channel_id, owner_name, owner_id, subscribers, next_id, related_ids]], columns=columns)
            return data

        else:
            print('A correct type needs to be passed.')

    def get_status(self, reset=True):
        status = self.status
        if reset:
            self.status
        return status
    
    def set_status(self, message):
        self.status.append(message)

