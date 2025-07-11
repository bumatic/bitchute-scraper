# Simple Python module for retrieving data from bitchute.
# Created and maintained since 2022 by Marcus Burkhardt. 
# 2025 code enhancements with support by Claude.
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


# Enhanced Bitchute Scraper with improved architecture and error handling
# Copyright (C) 2025 Enhanced by Claude
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

import time
import logging
import json
from typing import Dict, List, Optional, Union, Tuple, Any
from dataclasses import dataclass, asdict
from abc import ABC, abstractmethod
from urllib.parse import urljoin, urlparse
import requests
from pathlib import Path
import asyncio
import aiohttp
import hashlib

import markdownify
import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
from dateutil import parser as date_parser
from tqdm import tqdm
from datetime import datetime
from retrying import retry

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class VideoData:
    """Data structure for video information"""
    id: str = ""
    title: str = ""
    description: str = ""
    view_count: int = 0
    like_count: int = 0
    dislike_count: int = 0
    duration: str = ""
    channel_name: str = ""
    channel_id: str = ""
    created_at: str = ""
    thumbnail_url: str = ""
    hashtags: List[str] = None
    category: str = ""
    sensitivity: str = ""
    description_links: List[str] = None
    scrape_time: str = ""

    def __post_init__(self):
        if self.hashtags is None:
            self.hashtags = []
        if self.description_links is None:
            self.description_links = []
        if not self.scrape_time:
            self.scrape_time = str(int(datetime.utcnow().timestamp()))


@dataclass 
class ChannelData:
    """Data structure for channel information"""
    id: str = ""
    title: str = ""
    description: str = ""
    video_count: int = 0
    subscriber_count: str = ""
    view_count: int = 0
    created_at: str = ""
    category: str = ""
    social_links: List[Tuple[str, str]] = None
    owner_name: str = ""
    owner_id: str = ""
    thumbnail_url: str = ""
    scrape_time: str = ""

    def __post_init__(self):
        if self.social_links is None:
            self.social_links = []
        if not self.scrape_time:
            self.scrape_time = str(int(datetime.utcnow().timestamp()))


class SelectorConfig:
    """Configurable CSS selectors for Bitchute elements"""
    
    def __init__(self, config_file: Optional[str] = None):
        # Updated selectors based on actual 2025 Bitchute HTML structure
        self.selectors = {
            # Video cards - confirmed from debug: .q-card works
            'video_cards': [
                '.q-card',  # Primary selector - found 21 elements
                '#video-card',  # Specific video card ID
                '.video-card', 
                '.video-result-container',
                '[data-video-id]'
            ],
            # Video titles - based on structure with .q-item__section
            'video_title': [
                '.q-item__section--main a',  # Links in main sections
                '.q-item a[href*="/video/"]',  # Video links in items
                'a[href*="/video/"]',  # Any video link
                '.q-item__label a',  # Labels with links
                '.video-card-title a', 
                '.video-result-title a'
            ],
            # Video channels - look for channel links
            'video_channel': [
                'a[href*="/channel/"]',  # Any channel link
                '.q-item__section a[href*="/channel/"]',
                '.channel-name a',
                '.video-card-channel a', 
                '.video-result-channel a'
            ],
            # View counts - look in various containers
            'video_views': [
                '.q-item__label:contains("visibility")',  # Based on debug output
                '.view-count',
                '.views',
                '.q-item__section .q-item__label',
                '.video-views',
                '[data-views]'
            ],
            # Duration information
            'video_duration': [
                '.q-item__label',  # Duration might be in labels
                '.duration',
                '.time',
                '.video-duration',
                '.video-time'
            ],
            # Thumbnail images in q-img components
            'video_thumbnail': [
                '.q-img img',  # Quasar image components
                '.q-img',  # The component itself might have background
                '.video-card-image img',
                '.video-result-image img',
                '.thumbnail img'
            ],
            # Channel cards for recommendations
            'channel_cards': [
                '.q-card',  # Same structure as videos
                '.channel-card',
                '.channel-item',
                '[data-channel-id]'
            ],
            # Channel titles
            'channel_title': [
                '.q-item__section--main',
                '.channel-card-title',
                '.name a',
                '.channel-name'
            ],
            # Trending tags - updated for new button structure
            'trending_tags': [
                'a[href*="/hashtag/"]',  # Found in debug output
                '.q-btn[href*="/hashtag/"]',
                '.sidebar.tags li a',
                '.tag-list a',
                '.hashtag-list a'
            ],
            # Video descriptions
            'video_description': [
                '.q-item__section',
                '#video-description',
                '.video-result-text',
                '.description',
                '.content-description'
            ],
            # Channel descriptions
            'channel_description': [
                '#channel-description',
                '.channel-desc',
                '.about-text'
            ],
            # Navigation elements
            'pagination_next': [
                '.next',
                '[aria-label="Next"]',
                '.pagination-next',
                '.q-btn:contains("Next")'
            ],
            # Dismiss buttons
            'dismiss_button': [
                'button:contains("Dismiss")',
                '.dismiss',
                '.close-button',
                '[aria-label="Close"]',
                '.q-btn:contains("Dismiss")'
            ],
            # Sensitivity warnings
            'sensitivity_link': [
                'a:contains("Some videos are not shown")',
                '.sensitivity-warning a',
                '.content-warning a'
            ]
        }
        
        if config_file and Path(config_file).exists():
            self._load_config(config_file)
    
    def _load_config(self, config_file: str):
        """Load selector configuration from JSON file"""
        try:
            with open(config_file, 'r') as f:
                custom_selectors = json.load(f)
                self.selectors.update(custom_selectors)
        except Exception as e:
            logger.warning(f"Failed to load selector config: {e}")
    
    def get_selectors(self, element_type: str) -> List[str]:
        """Get list of selectors for an element type"""
        return self.selectors.get(element_type, [])
    
    def save_config(self, config_file: str):
        """Save current selector configuration to JSON file"""
        with open(config_file, 'w') as f:
            json.dump(self.selectors, f, indent=2)


class BasePage(ABC):
    """Abstract base class for page parsers"""
    
    def __init__(self, soup: BeautifulSoup, selectors: SelectorConfig):
        self.soup = soup
        self.selectors = selectors
    
    @abstractmethod
    def parse(self) -> Any:
        """Parse the page and return structured data"""
        pass
    
    def find_element_safe(self, element_type: str, parent=None) -> Optional[Any]:
        """Safely find an element using multiple selector fallbacks"""
        search_scope = parent or self.soup
        selectors = self.selectors.get_selectors(element_type)
        
        for selector in selectors:
            try:
                element = search_scope.select_one(selector)
                if element:
                    return element
            except Exception as e:
                logger.debug(f"Selector '{selector}' failed: {e}")
                continue
        return None
    
    def find_elements_safe(self, element_type: str, parent=None) -> List[Any]:
        """Safely find elements using multiple selector fallbacks"""
        search_scope = parent or self.soup
        selectors = self.selectors.get_selectors(element_type)
        
        for selector in selectors:
            try:
                elements = search_scope.select(selector)
                if elements:
                    return elements
            except Exception as e:
                logger.debug(f"Selector '{selector}' failed: {e}")
                continue
        return []


class VideoPageParser(BasePage):
    """Parser for individual video pages"""
    
    def parse(self) -> List[VideoData]:
        """Enhanced parsing for 2025 BitChute structure"""
        videos = []
        
        # Try multiple selectors for video containers
        video_containers = (
            self.soup.select('.q-card') or 
            self.soup.select('.video-card') or 
            self.soup.select('[data-video-id]') or
            self.soup.select('article') or
            []
        )
        
        if not video_containers:
            # Fallback: look for any links to videos
            video_links = self.soup.select('a[href*="/video/"]')
            # Group links by their parent containers
            containers = set(link.parent for link in video_links if link.parent)
            video_containers = list(containers)[:50]  # Limit to reasonable number
        
        for i, container in enumerate(video_containers, 1):
            try:
                video = VideoData()
                video.rank = i
                
                # Extract video ID and title - multiple approaches
                main_video_link = (
                    container.select_one('a[href*="/video/"]') or
                    container.find('a', href=lambda x: x and '/video/' in x)
                )
                
                if main_video_link:
                    href = main_video_link.get('href', '')
                    if href:
                        # Extract video ID
                        video.id = href.split('/')[-1] if '/' in href else href
                        
                        # Try to get title from link text
                        title_text = main_video_link.get_text().strip()
                        if title_text and len(title_text) > 3:
                            video.title = title_text
                
                # Try alternative title extraction methods
                if not video.title:
                    title_selectors = [
                        '.q-item__label',
                        '.video-card-title',
                        '.video-title',
                        'h1', 'h2', 'h3',
                        '[title]'
                    ]
                    
                    for selector in title_selectors:
                        title_elem = container.select_one(selector)
                        if title_elem:
                            title_text = title_elem.get_text().strip()
                            if title_text and len(title_text) > 3:
                                video.title = title_text
                                break
                
                # Extract channel information
                channel_link = (
                    container.select_one('a[href*="/channel/"]') or
                    container.find('a', href=lambda x: x and '/channel/' in x)
                )
                
                if channel_link:
                    channel_href = channel_link.get('href', '')
                    if channel_href:
                        video.channel_id = channel_href.split('/')[-1]
                    
                    channel_text = channel_link.get_text().strip()
                    if channel_text:
                        video.channel_name = channel_text
                
                # Extract view count - multiple approaches
                view_selectors = [
                    '.absolute-bottom-left .text-caption',
                    '.video-views',
                    '.views',
                    '.q-item__label'
                ]
                
                for selector in view_selectors:
                    views_elem = container.select_one(selector)
                    if views_elem:
                        views_text = views_elem.get_text().strip()
                        if 'view' in views_text.lower() or views_text.replace(',', '').isdigit():
                            video.view_count = self._process_views(views_text)
                            break
                
                # Extract duration
                duration_selectors = [
                    '.absolute-bottom-right .text-caption',
                    '.video-duration',
                    '.duration'
                ]
                
                for selector in duration_selectors:
                    duration_elem = container.select_one(selector)
                    if duration_elem:
                        duration_text = duration_elem.get_text().strip()
                        if ':' in duration_text:  # Format like "10:30"
                            video.duration = duration_text
                            break
                
                # Extract thumbnail URL
                thumbnail_selectors = [
                    '.q-img__image',
                    '.q-img img',
                    '.video-card-image img',
                    'img[data-src]',
                    'img[src]'
                ]
                
                for selector in thumbnail_selectors:
                    thumbnail_elem = container.select_one(selector)
                    if thumbnail_elem:
                        thumbnail_url = (
                            thumbnail_elem.get('data-src') or 
                            thumbnail_elem.get('src') or 
                            ''
                        )
                        if thumbnail_url and 'http' in thumbnail_url:
                            video.thumbnail_url = thumbnail_url
                            break
                
                # Extract creation/publish date
                date_selectors = [
                    '.q-item__label:last-child',
                    '.video-card-published',
                    '.published',
                    '.date'
                ]
                
                for selector in date_selectors:
                    date_elem = container.select_one(selector)
                    if date_elem:
                        date_text = date_elem.get_text().strip()
                        if any(word in date_text.lower() for word in ['ago', 'day', 'hour', 'minute', 'week', 'month', 'year']):
                            video.created_at = date_text
                            break
                
                # Only add video if we have essential data
                if video.id or video.title:
                    videos.append(video)
                    
            except Exception as e:
                logger.warning(f"Failed to parse video container {i}: {e}")
                continue
        
        return videos

    def _process_views(self, views_str: str) -> int:
        """Convert view count string to integer with enhanced parsing"""
        try:
            # Clean the string
            views = views_str.lower().replace(',', '').replace(' ', '').replace('views', '').replace('view', '')
            
            # Handle different formats
            if 'k' in views:
                num = float(views.replace('k', ''))
                return int(num * 1000)
            elif 'm' in views:
                num = float(views.replace('m', ''))
                return int(num * 1000000)
            elif 'b' in views:
                num = float(views.replace('b', ''))
                return int(num * 1000000000)
            else:
                # Try to extract number directly
                import re
                numbers = re.findall(r'\d+', views)
                if numbers:
                    return int(numbers[0])
                return 0
        except (ValueError, AttributeError, IndexError):
            return 0


class SearchPageParser(BasePage):
    """Parser for search results pages"""
    
    def parse(self) -> List[VideoData]:
        videos = []
        
        # Look for video cards with the new structure
        video_containers = self.soup.select('.q-card')
        
        for i, container in enumerate(video_containers, 1):
            try:
                video = VideoData()
                video.rank = i
                
                # Extract video ID from the main video link
                main_video_link = container.select_one('a[href*="/video/"]')
                if main_video_link:
                    href = main_video_link.get('href', '')
                    if href:
                        # Extract video ID (e.g., "/video/dqoDDpLoQuL2" -> "dqoDDpLoQuL2")
                        video.id = href.split('/')[-1]
                
                # Extract TITLE, CREATOR, PUBLISHED AGO from the main content section
                # Target specifically .q-item__section--main (Section 2 from debug)
                main_section = container.select_one('.q-item__section--main')
                if main_section:
                    labels = main_section.select('.q-item__label')
                    
                    if len(labels) >= 1:
                        # 1st .q-item__label = TITLE
                        video.title = labels[0].get_text().strip()
                    
                    if len(labels) >= 2:
                        # 2nd .q-item__label = CREATOR
                        video.channel_name = labels[1].get_text().strip()
                    
                    if len(labels) >= 3:
                        # 3rd .q-item__label = PUBLISHED AGO
                        video.created_at = labels[2].get_text().strip()
                
                # Extract channel ID from channel link
                channel_link = container.select_one('a[href*="/channel/"]')
                if channel_link:
                    channel_href = channel_link.get('href', '')
                    if channel_href:
                        video.channel_id = channel_href.split('/')[-1]
                
                # Extract VIEWS from .absolute-bottom-left
                views_elem = container.select_one('.absolute-bottom-left .text-caption')
                if views_elem:
                    views_text = views_elem.get_text().strip()
                    # Remove commas and parse number
                    views_clean = views_text.replace(',', '')
                    try:
                        video.view_count = int(views_clean)
                    except ValueError:
                        video.view_count = 0
                
                # Extract DURATION from .absolute-bottom-right
                duration_elem = container.select_one('.absolute-bottom-right .text-caption')
                if duration_elem:
                    video.duration = duration_elem.get_text().strip()
                
                # Extract thumbnail URL from the main image
                thumbnail_elem = container.select_one('.q-img__image')
                if thumbnail_elem:
                    video.thumbnail_url = thumbnail_elem.get('src', '')
                
                # Only add video if we have essential data
                if video.id or video.title:
                    videos.append(video)
                    
            except Exception as e:
                logger.warning(f"Failed to parse video container {i}: {e}")
                continue
        
        return videos
    
    def _process_views(self, views_str: str) -> int:
        """Convert view count string to integer"""
        try:
            # Clean the string and remove commas
            views = views_str.replace(',', '').strip()
            
            # Handle K/M suffixes
            if views.lower().endswith('k'):
                return int(float(views[:-1]) * 1000)
            elif views.lower().endswith('m'):
                return int(float(views[:-1]) * 1000000)
            else:
                # Try to parse as integer
                return int(views)
        except (ValueError, AttributeError):
            return 0
    
    def _process_views(self, views_str: str) -> int:
        """Convert view count string to integer"""
        try:
            # Clean the string and remove commas
            views = views_str.replace(',', '').strip()
            
            # Handle K/M suffixes
            if views.lower().endswith('k'):
                return int(float(views[:-1]) * 1000)
            elif views.lower().endswith('m'):
                return int(float(views[:-1]) * 1000000)
            else:
                # Try to parse as integer
                return int(views)
        except (ValueError, AttributeError):
            return 0


class EnhancedCrawler:
    """Enhanced Bitchute crawler with improved error handling and features"""
    
    def __init__(self, headless: bool = True, verbose: bool = False, 
                 chrome_driver: Optional[str] = None, config_file: Optional[str] = None,
                 download_thumbnails: bool = False, thumbnail_dir: str = "thumbnails"):
        
        self.options = Options()
        if headless:
            self.options.add_argument('--headless=new')
        
        # Enhanced Chrome options for better compatibility
        self.options.add_argument('--disable-dev-shm-usage')
        self.options.add_argument('--no-sandbox')
        self.options.add_argument('--disable-extensions')
        self.options.add_argument('--disable-gpu')
        self.options.add_argument('--window-size=1920,1080')
        self.options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        
        self.chrome_driver = chrome_driver
        self.wd = None
        self.verbose = verbose
        self.download_thumbnails = download_thumbnails
        self.thumbnail_dir = Path(thumbnail_dir)
        
        # Create thumbnail directory
        if self.download_thumbnails:
            self.thumbnail_dir.mkdir(exist_ok=True)
        
        # Initialize selectors and URL patterns
        self.selectors = SelectorConfig(config_file)
        self._init_url_patterns()
        
        # Rate limiting
        self.last_request_time = 0
        self.min_delay = 1.0  # Minimum 1 second between requests
    
    def _init_url_patterns(self):
        """Initialize URL patterns for different page types"""
        self.base_url = 'https://www.bitchute.com/'
        self.url_patterns = {
            'channel': 'https://www.bitchute.com/channel/{}/',
            'video': 'https://www.bitchute.com/video/{}/',
            'hashtag': 'https://www.bitchute.com/hashtag/{}/',
            'search': 'https://www.bitchute.com/search/?query={}&kind=video',
            # Video listing pages
            'trending': 'https://www.bitchute.com/trending/',
            'trending_week': 'https://www.bitchute.com/trending/?period=week',
            'trending_month': 'https://www.bitchute.com/trending/?period=month',
            'popular': 'https://www.bitchute.com/popular/',  # "Fresh" on site
            'all': 'https://www.bitchute.com/all/',
            'member_picked': 'https://www.bitchute.com/memberpicked/',
            'shorts': 'https://www.bitchute.com/shorts/'
        }
    
    def create_webdriver(self):
        """Create WebDriver with enhanced options"""
        try:
            if not self.chrome_driver:
                self.wd = webdriver.Chrome(
                    service=webdriver.ChromeService(ChromeDriverManager().install()),
                    options=self.options
                )
            else:
                self.wd = webdriver.Chrome(
                    service=webdriver.ChromeService(self.chrome_driver),
                    options=self.options
                )
            
            # Set implicit wait and page load timeout
            self.wd.implicitly_wait(10)
            self.wd.set_page_load_timeout(30)
            
            logger.info("WebDriver created successfully")
            
        except Exception as e:
            logger.error(f"Failed to create WebDriver: {e}")
            raise
    
    def reset_webdriver(self):
        """Safely close and reset WebDriver"""
        if self.wd:
            try:
                self.wd.quit()
            except Exception as e:
                logger.warning(f"Error closing WebDriver: {e}")
            finally:
                self.wd = None
    
    def _respect_rate_limit(self):
        """Implement rate limiting to be respectful to the server"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.min_delay:
            sleep_time = self.min_delay - time_since_last
            if self.verbose:
                logger.info(f"Rate limiting: sleeping for {sleep_time:.2f} seconds")
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    @retry(stop_max_attempt_number=3, wait_fixed=2000)
    def _fetch_page(self, url: str, click_elements: Optional[List[str]] = None, 
                   scroll: bool = True, max_items: Optional[int] = None) -> str:
        """Fetch page with enhanced error handling and retry logic"""
        
        if not self.wd:
            self.create_webdriver()
        
        self._respect_rate_limit()
        
        try:
            if self.verbose:
                logger.info(f'Fetching: {url}')
            
            self.wd.get(url)
            
            # Wait for page to load
            WebDriverWait(self.wd, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Handle common popups and overlays
            self._handle_popups()
            
            # Click specified elements if provided
            if click_elements:
                for element_text in click_elements:
                    self._click_element_safe(element_text)
            
            # Handle scrolling for infinite scroll pages
            if scroll:
                self._smart_scroll(max_items)
            
            return self.wd.page_source
            
        except TimeoutException:
            logger.error(f"Timeout loading page: {url}")
            raise
        except WebDriverException as e:
            logger.error(f"WebDriver error fetching {url}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error fetching {url}: {e}")
            raise
    
    def _handle_popups(self):
        """Handle common popups and dismissible elements"""
        # Handle dismiss button
        try:
            dismiss_selectors = self.selectors.get_selectors('dismiss_button')
            for selector in dismiss_selectors:
                elements = self.wd.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    if element.is_displayed():
                        element.click()
                        time.sleep(1)
                        break
        except Exception as e:
            logger.debug(f"No dismiss button found or error clicking: {e}")
        
        # Handle sensitivity warning
        try:
            elements = self.wd.find_elements(By.PARTIAL_LINK_TEXT, "Some videos are not shown")
            for element in elements:
                if element.is_displayed():
                    element.click()
                    time.sleep(2)
                    break
        except Exception as e:
            logger.debug(f"No sensitivity warning found: {e}")
    
    def _click_element_safe(self, element_text: str):
        """Safely click an element by text"""
        try:
            wait = WebDriverWait(self.wd, 10)
            element = wait.until(
                EC.element_to_be_clickable((By.PARTIAL_LINK_TEXT, element_text))
            )
            element.click()
            time.sleep(2)
        except TimeoutException:
            logger.warning(f"Element with text '{element_text}' not found or not clickable")
        except Exception as e:
            logger.warning(f"Error clicking element '{element_text}': {e}")
    
    def _smart_scroll(self, max_items: Optional[int] = None):
        """Implement smart scrolling with item count limits"""
        if max_items:
            target_iterations = (max_items // 10) + 1
        else:
            target_iterations = 1
        
        script = """
        window.scrollTo(0, document.body.scrollHeight);
        return document.body.scrollHeight;
        """
        
        last_height = self.wd.execute_script(script)
        iteration = 0
        
        while iteration < target_iterations:
            iteration += 1
            time.sleep(2)  # Wait for content to load
            
            new_height = self.wd.execute_script(script)
            if new_height == last_height:
                break  # No more content to load
            
            last_height = new_height
            
            if self.verbose:
                logger.info(f"Scroll iteration {iteration}/{target_iterations}")
    
    def search(self, query: str, max_results: int = 100) -> pd.DataFrame:
        """Enhanced search with better error handling"""
        try:
            url = self.url_patterns['search'].format(query)
            page_source = self._fetch_page(url, max_items=max_results)
            
            soup = BeautifulSoup(page_source, 'html.parser')
            parser = SearchPageParser(soup, self.selectors)
            videos = parser.parse()
            
            # Convert to DataFrame
            data = [asdict(video) for video in videos[:max_results]]
            df = pd.DataFrame(data)
            
            # Download thumbnails if requested
            if self.download_thumbnails and not df.empty:
                df = self._download_thumbnails_sync(df)
            
            return df
            
        except Exception as e:
            logger.error(f"Search failed for query '{query}': {e}")
            return pd.DataFrame()
        finally:
            self.reset_webdriver()
    
    def get_video(self, video_id: str) -> Optional[VideoData]:
        """Get detailed video information"""
        try:
            url = self.url_patterns['video'].format(video_id)
            page_source = self._fetch_page(url, scroll=False)
            
            soup = BeautifulSoup(page_source, 'html.parser')
            parser = VideoPageParser(soup, self.selectors)
            video = parser.parse()
            
            # Download thumbnail if requested
            if self.download_thumbnails and video and video.thumbnail_url:
                video.thumbnail_url = self._download_single_thumbnail(video.thumbnail_url, video.id)
            
            return video
            
        except Exception as e:
            logger.error(f"Failed to get video {video_id}: {e}")
            return None
        finally:
            self.reset_webdriver()
    
    def _download_single_thumbnail(self, thumbnail_url: str, video_id: str) -> str:
        """Download a single thumbnail synchronously"""
        try:
            if not thumbnail_url:
                return thumbnail_url
            
            # Create filename with hash to avoid duplicates
            url_hash = hashlib.md5(thumbnail_url.encode()).hexdigest()[:8]
            extension = Path(urlparse(thumbnail_url).path).suffix or '.jpg'
            filename = f"{video_id}_{url_hash}{extension}"
            filepath = self.thumbnail_dir / filename
            
            # Skip if already downloaded
            if filepath.exists():
                return str(filepath)
            
            # Download the thumbnail
            response = requests.get(thumbnail_url, timeout=10, stream=True)
            response.raise_for_status()
            
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            logger.info(f"Downloaded thumbnail: {filename}")
            return str(filepath)
            
        except Exception as e:
            logger.warning(f"Failed to download thumbnail {thumbnail_url}: {e}")
            return thumbnail_url
    
    def _download_thumbnails_sync(self, df: pd.DataFrame) -> pd.DataFrame:
        """Download thumbnails synchronously for a DataFrame of videos"""
        if 'thumbnail_url' not in df.columns or 'id' not in df.columns:
            return df
        
        df = df.copy()
        for idx, row in df.iterrows():
            if row['thumbnail_url']:
                local_path = self._download_single_thumbnail(row['thumbnail_url'], row['id'])
                df.at[idx, 'thumbnail_local_path'] = local_path
        
        return df
    
    def get_trending_videos(self, timeframe: str = 'day') -> pd.DataFrame:
        """Get trending videos with timeframe support - Updated for 2025 BitChute"""
        try:
            # Use direct URLs instead of clicking elements
            if timeframe == 'week':
                url = self.url_patterns['trending_week']
            elif timeframe == 'month':
                url = self.url_patterns['trending_month']
            else:
                url = self.url_patterns['trending']
            
            if self.verbose:
                logger.info(f"Fetching trending videos for timeframe: {timeframe}")
                logger.info(f"Using URL: {url}")
            
            # Note: BitChute now requires login for trending categories
            # This method will get the main page content instead
            page_source = self._fetch_page(url)
            
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # Check if we're redirected to login
            if 'login' in soup.get_text().lower() or 'sign in' in soup.get_text().lower():
                logger.warning("BitChute trending requires login - falling back to homepage")
                # Fall back to homepage content
                page_source = self._fetch_page(self.base_url)
                soup = BeautifulSoup(page_source, 'html.parser')
            
            parser = SearchPageParser(soup, self.selectors)
            videos = parser.parse()
            
            # Limit to reasonable number (trending should be ~20 videos)
            videos = videos[:20] if len(videos) > 20 else videos
            
            # Convert to DataFrame
            data = [asdict(video) for video in videos]
            df = pd.DataFrame(data)
            
            if self.verbose:
                logger.info(f"Found {len(videos)} videos for {timeframe} trending")
            
            if self.download_thumbnails and not df.empty:
                df = self._download_thumbnails_sync(df)
            
            return df
            
        except Exception as e:
            logger.error(f"Failed to get trending videos for {timeframe}: {e}")
            return pd.DataFrame()
        finally:
            self.reset_webdriver()
    
    def get_popular_videos(self) -> pd.DataFrame:
        """Get popular videos from homepage"""
        try:
            page_source = self._fetch_page(self.base_url)
            
            soup = BeautifulSoup(page_source, 'html.parser')
            parser = SearchPageParser(soup, self.selectors)
            videos = parser.parse()
            
            data = [asdict(video) for video in videos]
            df = pd.DataFrame(data)
            
            if self.download_thumbnails and not df.empty:
                df = self._download_thumbnails_sync(df)
            
            return df
            
        except Exception as e:
            logger.error(f"Failed to get popular videos: {e}")
            return pd.DataFrame()
        finally:
            self.reset_webdriver()
    
    def get_channel_info(self, channel_id: str) -> Optional[ChannelData]:
        """Get detailed channel information"""
        try:
            url = self.url_patterns['channel'].format(channel_id)
            page_source = self._fetch_page(url, click_elements=['ABOUT'], scroll=False)
            
            soup = BeautifulSoup(page_source, 'html.parser')
            
            channel = ChannelData()
            channel.id = channel_id
            
            # Extract channel title
            name_elem = soup.find(class_='name')
            if name_elem:
                channel.title = name_elem.get_text().strip()
            
            # Extract description
            desc_elem = soup.find(id='channel-description')
            if desc_elem:
                channel.description = markdownify.markdownify(desc_elem.decode_contents())
            
            # Extract statistics from channel-about-details
            details_elem = soup.find(class_='channel-about-details')
            if details_elem:
                for p_elem in details_elem.find_all('p'):
                    text = p_elem.get_text().strip()
                    if 'videos' in text.lower():
                        try:
                            channel.video_count = int(text.split()[1])
                        except (IndexError, ValueError):
                            pass
                    elif 'subscribers' in text.lower():
                        channel.subscriber_count = text.split()[1]
                    elif 'created' in text.lower():
                        channel.created_at = text
            
            return channel
            
        except Exception as e:
            logger.error(f"Failed to get channel info for {channel_id}: {e}")
            return None
        finally:
            self.reset_webdriver()
    
    def _process_views(self, views_str: str) -> int:
        """Convert view count string to integer with enhanced parsing"""
        try:
            # Clean the string
            views = views_str.lower().replace(',', '').replace(' ', '').replace('views', '')
            
            # Handle different formats
            if 'k' in views:
                num = float(views.replace('k', ''))
                return int(num * 1000)
            elif 'm' in views:
                num = float(views.replace('m', ''))
                return int(num * 1000000)
            elif 'b' in views:
                num = float(views.replace('b', ''))
                return int(num * 1000000000)
            else:
                # Try to extract number directly
                import re
                numbers = re.findall(r'\d+', views)
                if numbers:
                    return int(numbers[0])
                return 0
        except (ValueError, AttributeError, IndexError):
            return 0
    
    def export_data(self, data: pd.DataFrame, filename: str, format: str = 'csv'):
        """Export data in various formats"""
        try:
            filepath = Path(filename)
            
            if format.lower() == 'csv':
                data.to_csv(filepath, index=False)
            elif format.lower() == 'json':
                data.to_json(filepath, orient='records', indent=2)
            elif format.lower() == 'excel':
                data.to_excel(filepath, index=False)
            elif format.lower() == 'parquet':
                data.to_parquet(filepath, index=False)
            else:
                raise ValueError(f"Unsupported format: {format}")
            
            logger.info(f"Data exported to {filepath}")
            
        except Exception as e:
            logger.error(f"Failed to export data: {e}")
            raise
    
    def validate_selectors(self, test_url: str = None) -> Dict[str, bool]:
        """Validate current selectors against a test page"""
        test_url = test_url or self.base_url
        results = {}
        
        try:
            page_source = self._fetch_page(test_url, scroll=False)
            soup = BeautifulSoup(page_source, 'html.parser')
            
            for element_type, selectors in self.selectors.selectors.items():
                found = False
                for selector in selectors:
                    try:
                        elements = soup.select(selector)
                        if elements:
                            found = True
                            break
                    except Exception:
                        continue
                results[element_type] = found
            
        except Exception as e:
            logger.error(f"Selector validation failed: {e}")
        finally:
            self.reset_webdriver()
        
        return results
    
    def update_selectors(self, new_selectors: Dict[str, List[str]]):
        """Update selector configuration"""
        for element_type, selectors in new_selectors.items():
            if element_type in self.selectors.selectors:
                self.selectors.selectors[element_type] = selectors
            else:
                logger.warning(f"Unknown element type: {element_type}")
    
    def get_all_videos(self) -> pd.DataFrame:
        """Get all videos"""
        try:
            url = self.url_patterns['all']
            page_source = self._fetch_page(url)
            
            soup = BeautifulSoup(page_source, 'html.parser')
            parser = SearchPageParser(soup, self.selectors)
            videos = parser.parse()
            
            data = [asdict(video) for video in videos]
            df = pd.DataFrame(data)
            
            if self.download_thumbnails and not df.empty:
                df = self._download_thumbnails_sync(df)
            
            return df
            
        except Exception as e:
            logger.error(f"Failed to get all videos: {e}")
            return pd.DataFrame()
        finally:
            self.reset_webdriver()

    def get_member_picked_videos(self) -> pd.DataFrame:
        """Get member picked videos"""
        try:
            url = self.url_patterns['member_picked']
            page_source = self._fetch_page(url)
            
            soup = BeautifulSoup(page_source, 'html.parser')
            parser = SearchPageParser(soup, self.selectors)
            videos = parser.parse()
            
            data = [asdict(video) for video in videos]
            df = pd.DataFrame(data)
            
            if self.download_thumbnails and not df.empty:
                df = self._download_thumbnails_sync(df)
            
            return df
            
        except Exception as e:
            logger.error(f"Failed to get member picked videos: {e}")
            return pd.DataFrame()
        finally:
            self.reset_webdriver()

    def get_shorts_videos(self) -> pd.DataFrame:
        """Get shorts videos"""
        try:
            url = self.url_patterns['shorts']
            page_source = self._fetch_page(url)
            
            soup = BeautifulSoup(page_source, 'html.parser')
            parser = SearchPageParser(soup, self.selectors)
            videos = parser.parse()
            
            data = [asdict(video) for video in videos]
            df = pd.DataFrame(data)
            
            if self.download_thumbnails and not df.empty:
                df = self._download_thumbnails_sync(df)
            
            return df
            
        except Exception as e:
            logger.error(f"Failed to get shorts videos: {e}")
            return pd.DataFrame()
        finally:
            self.reset_webdriver()

    def debug_page_info(self, url: str = None) -> dict:
        """Debug method to get detailed page information"""
        if not url:
            url = self.base_url
        
        try:
            page_source = self._fetch_page(url, scroll=False)
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # Get current URL from browser
            current_url = self.wd.current_url if self.wd else url
            
            # Count different container types
            q_cards = len(soup.select('.q-card'))
            video_cards = len(soup.select('.video-card'))
            video_results = len(soup.select('.video-result-container'))
            
            # Get page title
            title_elem = soup.find('title')
            title = title_elem.get_text().strip() if title_elem else "No title"
            
            # Look for trending-specific elements
            trending_links = soup.select('a[href*="trending"]')
            period_links = soup.select('a[href*="period="]')
            
            # Check for login requirement
            login_indicators = ['login', 'sign in', 'register', 'log in']
            page_text = soup.get_text().lower()
            requires_login = any(indicator in page_text for indicator in login_indicators)
            
            debug_info = {
                'requested_url': url,
                'actual_url': current_url,
                'page_title': title,
                'q_cards_found': q_cards,
                'video_cards_found': video_cards,
                'video_results_found': video_results,
                'trending_links_found': len(trending_links),
                'period_links_found': len(period_links),
                'page_source_length': len(page_source),
                'possibly_requires_login': requires_login
            }
            
            return debug_info
            
        except Exception as e:
            logger.error(f"Debug failed for {url}: {e}")
            return {'error': str(e)}
        finally:
            if self.wd:
                self.reset_webdriver()

    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensure cleanup"""
        self.reset_webdriver()




# Backward compatibility layer
class Crawler(EnhancedCrawler):
    """Backward compatible interface"""
    
    def __init__(self, headless=True, verbose=False, chrome_driver=None):
        super().__init__(headless=headless, verbose=verbose, chrome_driver=chrome_driver)
    
    
    def get_all_videos(self):
        """Get all videos from homepage (backward compatible)"""
        return super().get_all_videos()

    def get_member_picked_videos(self):
        """Get member picked videos"""
        return super().get_member_picked_videos()

    def get_shorts_videos(self):
        """Get shorts videos"""
        return super().get_shorts_videos()


    def get_trending_videos(self, timeframe='day'):
        """Backward compatible trending videos method with timeframe support"""
        return super().get_trending_videos(timeframe)
    
    def get_trending_videos_week(self):
        """Get trending videos for the week"""
        return self.get_trending_videos('week')
    
    def get_trending_videos_month(self):
        """Get trending videos for the month"""
        return self.get_trending_videos('month')
    
    def get_popular_videos(self):
        """Get popular/fresh videos (backward compatible)"""
        return super().get_popular_videos()
    
    def get_fresh_videos(self):
        """Alias for get_popular_videos (matches new UI naming)"""
        return self.get_popular_videos()
    
    def get_trending_tags(self):
        """Get trending tags (backward compatible)"""
        try:
            page_source = self._fetch_page(self.base_url, click_elements=['TRENDING'])
            soup = BeautifulSoup(page_source, 'html.parser')
            
            tags = []
            tag_elements = soup.select('.sidebar.tags li a')
            
            for i, tag_elem in enumerate(tag_elements, 1):
                tag_data = {
                    'rank': i,
                    'tag_name': tag_elem.get_text().strip(),
                    'tag_url': tag_elem.get('href', ''),
                    'scrape_time': str(int(datetime.utcnow().timestamp()))
                }
                tags.append(tag_data)
            
            return pd.DataFrame(tags)
            
        except Exception as e:
            logger.error(f"Failed to get trending tags: {e}")
            return pd.DataFrame()
        finally:
            self.reset_webdriver()
    
    def get_trending(self):
        """Get both trending videos and tags (backward compatible)"""
        videos = self.get_trending_videos()
        tags = self.get_trending_tags()
        return videos, tags
    
    def get_all_videos(self):
        """Get all videos from homepage (backward compatible)"""
        try:
            page_source = self._fetch_page(self.base_url, click_elements=['ALL'])
            soup = BeautifulSoup(page_source, 'html.parser')
            parser = SearchPageParser(soup, self.selectors)
            videos = parser.parse()
            
            data = [asdict(video) for video in videos]
            return pd.DataFrame(data)
            
        except Exception as e:
            logger.error(f"Failed to get all videos: {e}")
            return pd.DataFrame()
        finally:
            self.reset_webdriver()
    
    def get_recommended_channels(self, extended=True):
        """Get recommended channels (backward compatible)"""
        try:
            page_source = self._fetch_page(self.base_url, scroll=False)
            soup = BeautifulSoup(page_source, 'html.parser')
            
            channels = []
            carousel = soup.find(id='carousel')
            
            if carousel:
                channel_cards = carousel.find_all(class_='channel-card')
                
                for i, card in enumerate(channel_cards, 1):
                    try:
                        link_elem = card.find('a')
                        title_elem = card.find(class_='channel-card-title')
                        
                        if link_elem and title_elem:
                            channel_id = link_elem.get('href', '').split('/')[-2]
                            channel_name = title_elem.get_text().strip()
                            
                            channel_data = {
                                'rank': i,
                                'id': channel_id,
                                'name': channel_name,
                                'scrape_time': str(int(datetime.utcnow().timestamp()))
                            }
                            channels.append(channel_data)
                            
                    except Exception as e:
                        logger.warning(f"Failed to parse channel card {i}: {e}")
                        continue
            
            df = pd.DataFrame(channels)
            
            # If extended info is requested, get detailed channel information
            if extended and not df.empty:
                detailed_channels = []
                for _, row in df.iterrows():
                    channel_info = self.get_channel_info(row['id'])
                    if channel_info:
                        detailed_data = asdict(channel_info)
                        detailed_data['rank'] = row['rank']
                        detailed_channels.append(detailed_data)
                
                if detailed_channels:
                    df = pd.DataFrame(detailed_channels)
            
            return df
            
        except Exception as e:
            logger.error(f"Failed to get recommended channels: {e}")
            return pd.DataFrame()
        finally:
            self.reset_webdriver()
    
    def get_channels(self, channel_ids, get_channel_about=True, get_channel_videos=True):
        """Get channel information (backward compatible)"""
        if isinstance(channel_ids, str):
            channel_ids = [channel_ids]
        
        abouts = pd.DataFrame()
        videos = pd.DataFrame()
        
        for channel_id in (tqdm(channel_ids) if not self.verbose else channel_ids):
            try:
                if get_channel_about:
                    about_data = self.get_channel_info(channel_id)
                    if about_data:
                        about_df = pd.DataFrame([asdict(about_data)])
                        abouts = pd.concat([abouts, about_df], ignore_index=True)
                
                if get_channel_videos:
                    videos_df = self.get_channel_videos(channel_id)
                    videos = pd.concat([videos, videos_df], ignore_index=True)
                    
            except Exception as e:
                logger.error(f"Failed to process channel {channel_id}: {e}")
                continue
        
        return abouts, videos
    
    def get_channel_videos(self, channel_id: str, max_videos: Optional[int] = None) -> pd.DataFrame:
        """Get videos from a specific channel"""
        try:
            url = self.url_patterns['channel'].format(channel_id)
            page_source = self._fetch_page(url, click_elements=['VIDEOS'], max_items=max_videos)
            
            soup = BeautifulSoup(page_source, 'html.parser')
            
            videos = []
            video_containers = soup.find_all(class_='channel-videos-container')
            
            for i, container in enumerate(video_containers, 1):
                try:
                    video = VideoData()
                    video.channel_id = channel_id
                    
                    # Extract title and ID
                    title_elem = container.find(class_='channel-videos-title')
                    if title_elem and title_elem.find('a'):
                        video.title = title_elem.get_text().strip()
                        href = title_elem.find('a').get('href', '')
                        video.id = href.split('/')[-2] if href else ''
                    
                    # Extract description
                    desc_elem = container.find(class_='channel-videos-text')
                    if desc_elem:
                        video.description = markdownify.markdownify(desc_elem.decode_contents())
                    
                    # Extract duration
                    duration_elem = container.find(class_='video-duration')
                    if duration_elem:
                        video.duration = duration_elem.get_text().strip()
                    
                    # Extract views
                    views_elem = container.find(class_='video-views')
                    if views_elem:
                        views_text = views_elem.get_text().strip()
                        video.view_count = self._process_views(views_text)
                    
                    # Extract creation date
                    date_elem = container.find(class_='channel-videos-details')
                    if date_elem:
                        video.created_at = date_elem.get_text().strip()
                    
                    videos.append(video)
                    
                    if max_videos and len(videos) >= max_videos:
                        break
                        
                except Exception as e:
                    logger.warning(f"Failed to parse video container {i}: {e}")
                    continue
            
            # Convert to DataFrame
            data = [asdict(video) for video in videos]
            df = pd.DataFrame(data)
            
            if self.download_thumbnails and not df.empty:
                df = self._download_thumbnails_sync(df)
            
            return df
            
        except Exception as e:
            logger.error(f"Failed to get videos for channel {channel_id}: {e}")
            return pd.DataFrame()
        finally:
            self.reset_webdriver()
    
    def get_videos(self, video_ids):
        """Get video information (backward compatible)"""
        if isinstance(video_ids, str):
            video_ids = [video_ids]
        
        videos = []
        
        for video_id in (tqdm(video_ids) if not self.verbose else video_ids):
            try:
                video_data = self.get_video(video_id)
                if video_data:
                    videos.append(asdict(video_data))
            except Exception as e:
                logger.error(f"Failed to get video {video_id}: {e}")
                continue
        
        return pd.DataFrame(videos)


# Original function-style interface for backward compatibility
def process_views(views):
    """Legacy function for processing view counts"""
    crawler = Crawler()
    return crawler._process_views(str(views))