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

import time
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from urllib.parse import urljoin
import requests
from pathlib import Path
import hashlib

import markdownify
import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
from datetime import datetime
from retrying import retry

# Configure base logging
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
    
    # Enhanced fields
    type: str = ""          # "trending", "popular", "search", etc.
    subtype: str = ""       # "day", "week", "month", etc.
    rank: int = 0           # 1, 2, 3, etc.
    video_url: str = ""     # Full BitChute URL

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


class Crawler:
    """Clean, focused BitChute scraper"""
    
    def __init__(self, headless: bool = True, verbose: bool = False, 
                 chrome_driver: Optional[str] = None):
        
        # Configure logging based on verbose setting
        if verbose:
            logging.basicConfig(level=logging.INFO)
            # Keep WebDriver Manager logs when verbose
            logging.getLogger('WDM').setLevel(logging.INFO)
        else:
            logging.basicConfig(level=logging.WARNING)
            # Suppress WebDriver Manager logs when not verbose
            logging.getLogger('WDM').setLevel(logging.WARNING)
            # Also suppress selenium logs
            logging.getLogger('selenium').setLevel(logging.WARNING)
            logging.getLogger('urllib3').setLevel(logging.WARNING)
        
        self.options = Options()
        if headless:
            self.options.add_argument('--headless=new')
        
        # Chrome options for better compatibility
        self.options.add_argument('--disable-dev-shm-usage')
        self.options.add_argument('--no-sandbox')
        self.options.add_argument('--disable-extensions')
        self.options.add_argument('--disable-gpu')
        self.options.add_argument('--window-size=1920,1080')
        self.options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        
        # Suppress Chrome logs when not verbose
        if not verbose:
            self.options.add_argument('--log-level=3')  # Suppress Chrome logs
            self.options.add_experimental_option('excludeSwitches', ['enable-logging'])
            self.options.add_experimental_option('useAutomationExtension', False)
        
        self.chrome_driver = chrome_driver
        self.wd = None
        self.verbose = verbose
        
        # URLs
        self.base_url = 'https://www.bitchute.com/'
        self.trending_url = 'https://www.bitchute.com/trending/'
        
        # Rate limiting
        self.last_request_time = 0
        self.min_delay = 1.0
    
    def create_webdriver(self):
        """Create WebDriver instance"""
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
            
            self.wd.implicitly_wait(10)
            self.wd.set_page_load_timeout(30)
            
            if self.verbose:
                logger.info("WebDriver created successfully")
            
        except Exception as e:
            logger.error(f"Failed to create WebDriver: {e}")
            raise
    
    def reset_webdriver(self):
        """Close WebDriver safely"""
        if self.wd:
            try:
                self.wd.quit()
            except Exception as e:
                if self.verbose:
                    logger.warning(f"Error closing WebDriver: {e}")
            finally:
                self.wd = None
    
    def _respect_rate_limit(self):
        """Rate limiting"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.min_delay:
            sleep_time = self.min_delay - time_since_last
            if self.verbose:
                logger.info(f"Rate limiting: sleeping for {sleep_time:.2f} seconds")
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    @retry(stop_max_attempt_number=3, wait_fixed=2000)
    def _fetch_page(self, url: str, wait_for_element: str = None, click_element: str = None) -> str:
        """Fetch page with optional element interaction"""
        
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
            
            # Handle any popups
            self._handle_popups()
            
            # Wait for specific element if requested
            if wait_for_element:
                WebDriverWait(self.wd, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, wait_for_element))
                )
            
            # Click element if requested
            if click_element:
                self._click_element_safe(click_element)
            
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
        """Handle common popups"""
        try:
            # Handle dismiss button
            dismiss_buttons = self.wd.find_elements(By.PARTIAL_LINK_TEXT, "Dismiss")
            for button in dismiss_buttons:
                if button.is_displayed():
                    button.click()
                    time.sleep(1)
                    break
        except Exception:
            pass
        
        try:
            # Handle sensitivity warning
            elements = self.wd.find_elements(By.PARTIAL_LINK_TEXT, "Some videos are not shown")
            for element in elements:
                if element.is_displayed():
                    element.click()
                    time.sleep(2)
                    break
        except Exception:
            pass
    
    def _click_element_safe(self, element_text: str):
        """Click element by text safely"""
        try:
            wait = WebDriverWait(self.wd, 10)
            element = wait.until(
                EC.element_to_be_clickable((By.PARTIAL_LINK_TEXT, element_text))
            )
            element.click()
            time.sleep(2)
            if self.verbose:
                logger.info(f"Clicked element: {element_text}")
        except TimeoutException:
            if self.verbose:
                logger.warning(f"Element with text '{element_text}' not found or not clickable")
        except Exception as e:
            if self.verbose:
                logger.warning(f"Error clicking element '{element_text}': {e}")
    
    def _parse_videos_from_soup(self, soup: BeautifulSoup, video_type: str = None, video_subtype: str = None) -> List[VideoData]:
        """Parse videos from BeautifulSoup object with improved title extraction"""
        videos = []
        
        # Look for video cards
        video_containers = soup.select('.q-card')
        
        if self.verbose:
            logger.info(f"Found {len(video_containers)} video containers")
        
        for i, container in enumerate(video_containers, 1):
            try:
                video = VideoData()
                
                # Add type, subtype, and rank
                video.type = video_type or "unknown"
                video.subtype = video_subtype
                video.rank = i
                
                # Extract video ID and URL from main video link
                main_video_link = container.select_one('a[href*="/video/"]')
                if main_video_link:
                    href = main_video_link.get('href', '')
                    if href:
                        # Extract video ID (e.g., "/video/dqoDDpLoQuL2" -> "dqoDDpLoQuL2")
                        video.id = href.split('/')[-1]
                        # Add full video URL
                        video.video_url = f"https://www.bitchute.com{href}" if href.startswith('/') else href
                
                # Improved title extraction strategy
                title_found = False
                
                # Strategy 1: Try to get title from the main video link text
                if main_video_link and not title_found:
                    title_text = main_video_link.get_text().strip()
                    if title_text and len(title_text) > 10 and 'visibility' not in title_text.lower():
                        video.title = title_text
                        title_found = True
                        if self.verbose:
                            logger.debug(f"Title from main link: {title_text}")
                
                # Strategy 2: Look for title in nested elements of the video link
                if not title_found and main_video_link:
                    # Check if there are nested elements inside the link
                    nested_elements = main_video_link.find_all(['span', 'div', 'p'])
                    for elem in nested_elements:
                        title_text = elem.get_text().strip()
                        if title_text and len(title_text) > 10 and 'visibility' not in title_text.lower():
                            video.title = title_text
                            title_found = True
                            if self.verbose:
                                logger.debug(f"Title from nested element: {title_text}")
                            break
                
                # Strategy 3: Look in .q-item__section--main but be more selective
                if not title_found:
                    main_section = container.select_one('.q-item__section--main')
                    if main_section:
                        labels = main_section.select('.q-item__label')
                        
                        # Try to find the label that looks like a title (longest, no "visibility")
                        for label in labels:
                            label_text = label.get_text().strip()
                            if (label_text and 
                                len(label_text) > 10 and 
                                'visibility' not in label_text.lower() and
                                not label_text.replace(',', '').replace('.', '').replace(':', '').isdigit()):
                                video.title = label_text
                                title_found = True
                                if self.verbose:
                                    logger.debug(f"Title from main section label: {label_text}")
                                break
                
                # Strategy 4: Look for any element with a title-like structure
                if not title_found:
                    # Look for elements that might contain titles
                    title_candidates = container.select('a[href*="/video/"] *')
                    for candidate in title_candidates:
                        title_text = candidate.get_text().strip()
                        if (title_text and 
                            len(title_text) > 15 and 
                            'visibility' not in title_text.lower() and
                            not title_text.replace(',', '').replace('.', '').replace(':', '').isdigit()):
                            video.title = title_text
                            title_found = True
                            if self.verbose:
                                logger.debug(f"Title from candidate element: {title_text}")
                            break
                
                # Log if title extraction failed
                if not title_found and self.verbose:
                    logger.warning(f"Could not extract title for video {i}, ID: {video.id}")
                    # Debug: show what we found
                    main_section = container.select_one('.q-item__section--main')
                    if main_section:
                        labels = main_section.select('.q-item__label')
                        logger.debug(f"Available labels: {[l.get_text().strip() for l in labels]}")
                
                # Extract channel information from .q-item__section--main labels
                main_section = container.select_one('.q-item__section--main')
                if main_section:
                    labels = main_section.select('.q-item__label')
                    
                    # Usually: 1st label = title, 2nd label = channel, 3rd label = time
                    if len(labels) >= 2:
                        channel_text = labels[1].get_text().strip()
                        if channel_text and 'visibility' not in channel_text.lower():
                            video.channel_name = channel_text
                    
                    if len(labels) >= 3:
                        time_text = labels[2].get_text().strip()
                        if time_text and any(word in time_text.lower() for word in ['ago', 'day', 'hour', 'minute', 'week', 'month', 'year']):
                            video.created_at = time_text
                
                # Extract channel ID from channel link
                channel_link = container.select_one('a[href*="/channel/"]')
                if channel_link:
                    channel_href = channel_link.get('href', '')
                    if channel_href:
                        video.channel_id = channel_href.split('/')[-1]
                
                # Extract view count from bottom left
                views_elem = container.select_one('.absolute-bottom-left .text-caption')
                if views_elem:
                    views_text = views_elem.get_text().strip()
                    video.view_count = self._parse_view_count(views_text)
                
                # Extract duration from bottom right
                duration_elem = container.select_one('.absolute-bottom-right .text-caption')
                if duration_elem:
                    video.duration = duration_elem.get_text().strip()
                
                # Extract thumbnail URL
                thumbnail_elem = container.select_one('.q-img__image')
                if thumbnail_elem:
                    video.thumbnail_url = thumbnail_elem.get('src', '')
                
                # Only add video if we have essential data
                if video.id or video.title:
                    videos.append(video)
                else:
                    if self.verbose:
                        logger.warning(f"Skipping video {i} - no ID or title found")
                        
            except Exception as e:
                if self.verbose:
                    logger.warning(f"Failed to parse video container {i}: {e}")
                continue
        
        if self.verbose:
            logger.info(f"Successfully parsed {len(videos)} videos")
        
        return videos
    
    def _parse_view_count(self, views_str: str) -> int:
        """Parse view count string to integer"""
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
    
    def _enhance_video_data(self, videos: List[VideoData]) -> List[VideoData]:
        """Visit each video page to collect detailed information - IMPROVED VERSION"""
        enhanced_videos = []
        
        if self.verbose:
            logger.info(f"Enhanced mode: collecting detailed data for {len(videos)} videos...")
            logger.info("This will take longer as we visit each video page individually...")
        
        for i, video in enumerate(videos, 1):
            try:
                if self.verbose:
                    logger.info(f"Enhancing video {i}/{len(videos)}: {video.id} - '{video.title[:50]}...'")
                
                # Get enhanced data
                enhanced_video = self._get_detailed_video_data(video)
                enhanced_videos.append(enhanced_video)
                
                # IMPROVED RATE LIMITING: Longer delays between requests
                if i < len(videos):  # Don't sleep after the last video
                    sleep_time = self.min_delay * 2  # Double the normal delay
                    if self.verbose:
                        logger.debug(f"Waiting {sleep_time}s before next video...")
                    time.sleep(sleep_time)
                    
            except Exception as e:
                if self.verbose:
                    logger.warning(f"Failed to enhance video {video.id}: {e}")
                # Add the original video data if enhancement fails
                enhanced_videos.append(video)
                continue
        
        if self.verbose:
            logger.info(f"Enhanced data collection complete. Processed {len(enhanced_videos)} videos.")
        
        return enhanced_videos
    
    def _get_detailed_video_data(self, video: VideoData) -> VideoData:
        """Get detailed data for a single video by visiting its page - FIXED VERSION"""
        if not video.id:
            return video
        
        try:
            video_url = f"{self.base_url}video/{video.id}/"
            
            if self.verbose:
                logger.debug(f'Fetching video page: {video_url}')
            
            # Navigate to video page
            self.wd.get(video_url)
            
            # ENHANCED WAITING: Wait for multiple key elements to ensure page is fully loaded
            wait = WebDriverWait(self.wd, 15)  # Increased timeout
            
            try:
                # Wait for the video title to be present (key indicator page loaded)
                wait.until(EC.presence_of_element_located((By.ID, "video-title")))
                
                # Also wait for the video statistics section
                wait.until(EC.presence_of_element_located((By.CLASS_NAME, "video-statistics")))
                
                # Wait a bit more for any dynamic content to load
                time.sleep(2)
                
            except TimeoutException:
                if self.verbose:
                    logger.warning(f"Timeout waiting for video page elements to load: {video_url}")
                # Try to continue anyway, might still get some data
            
            # Additional check: ensure we're on the right page
            current_url = self.wd.current_url
            if video.id not in current_url:
                if self.verbose:
                    logger.warning(f"URL mismatch. Expected {video.id}, got {current_url}")
                return video
            
            # Get page source after ensuring it's loaded
            soup = BeautifulSoup(self.wd.page_source, 'html.parser')
            
            # Verify we have the expected content
            if not soup.find(id='video-title'):
                if self.verbose:
                    logger.warning(f"Video title not found on page, page may not be fully loaded: {video_url}")
                return video
            
            # Extract detailed information
            enhanced_video = self._parse_video_page(soup, video)
            
            return enhanced_video
            
        except Exception as e:
            if self.verbose:
                logger.warning(f"Failed to get detailed data for video {video.id}: {e}")
            return video
    
    def _parse_video_page(self, soup: BeautifulSoup, base_video: VideoData) -> VideoData:
        """Parse detailed video information from video page - IMPROVED VERSION"""
        video = base_video  # Start with existing data
        
        try:
            # DEBUGGING: Log what elements we find
            if self.verbose:
                title_elem = soup.find(id='video-title')
                views_elem = soup.find(id='video-view-count')
                desc_elem = soup.find(id='video-description')
                logger.debug(f"Page parsing - Title: {'✓' if title_elem else '✗'}, "
                            f"Views: {'✓' if views_elem else '✗'}, "
                            f"Description: {'✓' if desc_elem else '✗'}")
            
            # Extract title (if not already set or if different)
            title_elem = soup.find(id='video-title')
            if title_elem:
                page_title = title_elem.get_text().strip()
                if page_title and (not video.title or len(page_title) > len(video.title)):
                    video.title = page_title
                    if self.verbose:
                        logger.debug(f"Updated title: {page_title}")
            
            # Extract view count (more accurate from video page)
            views_elem = soup.find(id='video-view-count')
            if views_elem:
                views_text = views_elem.get_text().strip()
                if views_text and views_text != "":
                    new_view_count = self._parse_view_count(views_text)
                    if new_view_count > 0:  # Only update if we got a valid count
                        video.view_count = new_view_count
                        if self.verbose:
                            logger.debug(f"Updated view count: {new_view_count}")
            
            # Extract like/dislike counts with better error handling
            like_elem = soup.find(id='video-like-count')
            if like_elem:
                try:
                    like_text = like_elem.get_text().strip()
                    if like_text and like_text.replace(',', '').isdigit():
                        video.like_count = int(like_text.replace(',', ''))
                        if self.verbose:
                            logger.debug(f"Like count: {video.like_count}")
                except (ValueError, AttributeError):
                    pass
            
            dislike_elem = soup.find(id='video-dislike-count')
            if dislike_elem:
                try:
                    dislike_text = dislike_elem.get_text().strip()
                    if dislike_text and dislike_text.replace(',', '').isdigit():
                        video.dislike_count = int(dislike_text.replace(',', ''))
                        if self.verbose:
                            logger.debug(f"Dislike count: {video.dislike_count}")
                except (ValueError, AttributeError):
                    pass
            
            # Extract description with better handling
            desc_elem = soup.find(id='video-description')
            if desc_elem:
                try:
                    # Get the description content
                    desc_content = desc_elem.decode_contents()
                    if desc_content and desc_content.strip():
                        # Convert HTML to markdown for better readability
                        video.description = markdownify.markdownify(desc_content).strip()
                        
                        # Extract links from description
                        links = []
                        for a in desc_elem.find_all('a'):
                            href = a.get('href')
                            if href and href.startswith('http'):
                                links.append(href)
                        video.description_links = links
                        
                        if self.verbose:
                            logger.debug(f"Description length: {len(video.description)} chars, Links: {len(links)}")
                except Exception as e:
                    if self.verbose:
                        logger.debug(f"Error parsing description: {e}")
            
            # Extract hashtags with better handling
            hashtag_elem = soup.find(id='video-hashtags')
            if hashtag_elem:
                try:
                    hashtags = []
                    for li in hashtag_elem.find_all('li'):
                        tag_text = li.get_text().strip()
                        if tag_text:
                            hashtags.append(tag_text)
                    if hashtags:
                        video.hashtags = hashtags
                        if self.verbose:
                            logger.debug(f"Hashtags: {hashtags}")
                except Exception as e:
                    if self.verbose:
                        logger.debug(f"Error parsing hashtags: {e}")
            
            # Extract category and sensitivity from the details table
            detail_table = soup.find('table', class_='video-detail-list')
            if detail_table:
                try:
                    for row in detail_table.find_all('tr'):
                        cells = row.find_all('td')
                        if len(cells) >= 2:
                            label = cells[0].get_text().strip().lower()
                            value = cells[1].get_text().strip()
                            
                            if 'category' in label and value:
                                video.category = value
                                if self.verbose:
                                    logger.debug(f"Category: {value}")
                            elif 'sensitivity' in label and value:
                                video.sensitivity = value
                                if self.verbose:
                                    logger.debug(f"Sensitivity: {value}")
                except Exception as e:
                    if self.verbose:
                        logger.debug(f"Error parsing details table: {e}")
            
            # Extract better thumbnail URL
            video_player = soup.find('video', id='player')
            if video_player and video_player.get('poster'):
                poster_url = video_player.get('poster')
                if poster_url and poster_url.startswith('http'):
                    video.thumbnail_url = poster_url
                    if self.verbose:
                        logger.debug(f"Updated thumbnail URL")
            
            # Extract better channel information
            channel_banner = soup.find(class_='channel-banner')
            if channel_banner:
                try:
                    # Channel name
                    channel_name_elem = channel_banner.find(class_='name')
                    if channel_name_elem:
                        name_link = channel_name_elem.find('a')
                        if name_link:
                            if not video.channel_name:  # Only update if not already set
                                video.channel_name = name_link.get_text().strip()
                            if not video.channel_id:  # Extract channel ID
                                href = name_link.get('href', '')
                                if href:
                                    video.channel_id = href.split('/')[-2]
                except Exception as e:
                    if self.verbose:
                        logger.debug(f"Error parsing channel info: {e}")
            
            # Extract publish date
            publish_elem = soup.find(class_='video-publish-date')
            if publish_elem and not video.created_at:
                try:
                    publish_text = publish_elem.get_text().strip()
                    if publish_text:
                        video.created_at = publish_text
                        if self.verbose:
                            logger.debug(f"Publish date: {publish_text}")
                except Exception as e:
                    if self.verbose:
                        logger.debug(f"Error parsing publish date: {e}")
            
            return video
            
        except Exception as e:
            if self.verbose:
                logger.warning(f"Error parsing video page for {video.id}: {e}")
            return video
    
    def get_trending_videos(self, timeframe: str = 'day', enhanced: bool = False) -> pd.DataFrame:
        """Get trending videos with optional enhanced data collection"""
        try:
            if timeframe == 'day':
                page_source = self._fetch_page(
                    self.trending_url, 
                    wait_for_element='.q-card'
                )
            elif timeframe == 'week':
                page_source = self._fetch_page(
                    self.trending_url, 
                    wait_for_element='.q-card',
                    click_element='WEEK'
                )
            elif timeframe == 'month':
                page_source = self._fetch_page(
                    self.trending_url, 
                    wait_for_element='.q-card',
                    click_element='MONTH'
                )
            else:
                raise ValueError(f"Invalid timeframe: {timeframe}. Use 'day', 'week', or 'month'")
            
            soup = BeautifulSoup(page_source, 'html.parser')
            videos = self._parse_videos_from_soup(soup, video_type="trending", video_subtype=timeframe)
            
            # Enhanced data collection - visit each video page
            if enhanced:
                if self.verbose:
                    logger.info(f"Enhanced mode: collecting detailed data for {len(videos)} videos...")
                videos = self._enhance_video_data(videos)
            
            # Convert to DataFrame
            data = [asdict(video) for video in videos]
            df = pd.DataFrame(data)
            
            if self.verbose:
                logger.info(f"Found {len(videos)} trending videos for {timeframe}")
            
            return df
            
        except Exception as e:
            logger.error(f"Failed to get trending videos for {timeframe}: {e}")
            return pd.DataFrame()
        finally:
            self.reset_webdriver()
    
    def get_popular_videos(self, enhanced: bool = False) -> pd.DataFrame:
        """Get popular videos with optional enhanced data collection"""
        try:
            page_source = self._fetch_page(
                self.base_url, 
                wait_for_element='.q-card'
            )
            
            soup = BeautifulSoup(page_source, 'html.parser')
            videos = self._parse_videos_from_soup(soup, video_type="popular")
            
            if enhanced:
                if self.verbose:
                    logger.info(f"Enhanced mode: collecting detailed data for {len(videos)} videos...")
                videos = self._enhance_video_data(videos)
            
            data = [asdict(video) for video in videos]
            df = pd.DataFrame(data)
            
            if self.verbose:
                logger.info(f"Found {len(videos)} popular videos")
            
            return df
            
        except Exception as e:
            logger.error(f"Failed to get popular videos: {e}")
            return pd.DataFrame()
        finally:
            self.reset_webdriver()
    
    def get_all_videos(self, enhanced: bool = False) -> pd.DataFrame:
        """Get all videos with optional enhanced data collection"""
        try:
            page_source = self._fetch_page(
                self.base_url, 
                wait_for_element='.q-card',
                click_element='ALL'
            )
            
            soup = BeautifulSoup(page_source, 'html.parser')
            videos = self._parse_videos_from_soup(soup, video_type="all")
            
            if enhanced:
                if self.verbose:
                    logger.info(f"Enhanced mode: collecting detailed data for {len(videos)} videos...")
                videos = self._enhance_video_data(videos)
            
            data = [asdict(video) for video in videos]
            df = pd.DataFrame(data)
            
            if self.verbose:
                logger.info(f"Found {len(videos)} all videos")
            
            return df
            
        except Exception as e:
            logger.error(f"Failed to get all videos: {e}")
            return pd.DataFrame()
        finally:
            self.reset_webdriver()
    
    def get_member_picked_videos(self, enhanced: bool = False) -> pd.DataFrame:
        """Get member picked videos with optional enhanced data collection"""
        try:
            page_source = self._fetch_page(
                f"{self.base_url}memberpicked/", 
                wait_for_element='.q-card'
            )
            
            soup = BeautifulSoup(page_source, 'html.parser')
            videos = self._parse_videos_from_soup(soup, video_type="member_picked")
            
            if enhanced:
                if self.verbose:
                    logger.info(f"Enhanced mode: collecting detailed data for {len(videos)} videos...")
                videos = self._enhance_video_data(videos)
            
            data = [asdict(video) for video in videos]
            df = pd.DataFrame(data)
            
            if self.verbose:
                logger.info(f"Found {len(videos)} member picked videos")
            
            return df
            
        except Exception as e:
            logger.error(f"Failed to get member picked videos: {e}")
            return pd.DataFrame()
        finally:
            self.reset_webdriver()
    
    def get_shorts_videos(self, enhanced: bool = False) -> pd.DataFrame:
        """Get shorts videos with optional enhanced data collection"""
        try:
            page_source = self._fetch_page(
                f"{self.base_url}shorts/", 
                wait_for_element='.q-card'
            )
            
            soup = BeautifulSoup(page_source, 'html.parser')
            videos = self._parse_videos_from_soup(soup, video_type="shorts")
            
            if enhanced:
                if self.verbose:
                    logger.info(f"Enhanced mode: collecting detailed data for {len(videos)} videos...")
                videos = self._enhance_video_data(videos)
            
            data = [asdict(video) for video in videos]
            df = pd.DataFrame(data)
            
            if self.verbose:
                logger.info(f"Found {len(videos)} shorts videos")
            
            return df
            
        except Exception as e:
            logger.error(f"Failed to get shorts videos: {e}")
            return pd.DataFrame()
        finally:
            self.reset_webdriver()
    
    def search(self, query: str, max_results: int = 100, enhanced: bool = False) -> pd.DataFrame:
        """Search for videos with optional enhanced data collection"""
        try:
            search_url = f"{self.base_url}search/?query={query}&kind=video"
            page_source = self._fetch_page(
                search_url, 
                wait_for_element='.q-card'
            )
            
            soup = BeautifulSoup(page_source, 'html.parser')
            videos = self._parse_videos_from_soup(soup, video_type="search")
            
            # Limit results if requested
            if max_results and len(videos) > max_results:
                videos = videos[:max_results]
            
            if enhanced:
                if self.verbose:
                    logger.info(f"Enhanced mode: collecting detailed data for {len(videos)} videos...")
                videos = self._enhance_video_data(videos)
            
            data = [asdict(video) for video in videos]
            df = pd.DataFrame(data)
            
            if self.verbose:
                logger.info(f"Found {len(videos)} search results for '{query}'")
            
            return df
            
        except Exception as e:
            logger.error(f"Search failed for query '{query}': {e}")
            return pd.DataFrame()
        finally:
            self.reset_webdriver()
    
    def get_trending_tags(self) -> pd.DataFrame:
        """Get trending tags"""
        try:
            page_source = self._fetch_page(
                self.trending_url, 
                wait_for_element='.q-card'
            )
            
            soup = BeautifulSoup(page_source, 'html.parser')
            
            tags = []
            # Look for hashtag links
            tag_elements = soup.select('a[href*="/hashtag/"]')
            
            for i, tag_elem in enumerate(tag_elements, 1):
                try:
                    tag_data = {
                        'rank': i,
                        'tag_name': tag_elem.get_text().strip(),
                        'tag_url': tag_elem.get('href', ''),
                        'scrape_time': str(int(datetime.utcnow().timestamp()))
                    }
                    tags.append(tag_data)
                except Exception:
                    continue
            
            df = pd.DataFrame(tags)
            
            if self.verbose:
                logger.info(f"Found {len(tags)} trending tags")
            
            return df
            
        except Exception as e:
            logger.error(f"Failed to get trending tags: {e}")
            return pd.DataFrame()
        finally:
            self.reset_webdriver()
    
    def get_trending(self, timeframe: str = 'day', enhanced: bool = False) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Get both trending videos and tags"""
        videos = self.get_trending_videos(timeframe, enhanced)
        tags = self.get_trending_tags()
        return videos, tags
    
    # Backward compatibility methods
    def get_trending_videos_week(self, enhanced: bool = False) -> pd.DataFrame:
        """Get trending videos for the week"""
        return self.get_trending_videos('week', enhanced)
    
    def get_trending_videos_month(self, enhanced: bool = False) -> pd.DataFrame:
        """Get trending videos for the month"""
        return self.get_trending_videos('month', enhanced)
    
    def get_fresh_videos(self, enhanced: bool = False) -> pd.DataFrame:
        """Alias for get_popular_videos"""
        return self.get_popular_videos(enhanced)
    
    def get_video(self, video_id: str) -> Optional[VideoData]:
        """Get detailed video information"""
        try:
            video_url = f"{self.base_url}video/{video_id}/"
            page_source = self._fetch_page(video_url)
            
            soup = BeautifulSoup(page_source, 'html.parser')
            
            video = VideoData()
            video.id = video_id
            video.video_url = video_url
            video.type = "individual"
            
            # Extract title
            title_elem = soup.find(id='video-title')
            if title_elem:
                video.title = title_elem.get_text().strip()
            
            # Extract view count
            views_elem = soup.find(id='video-view-count')
            if views_elem:
                video.view_count = self._parse_view_count(views_elem.get_text().strip())
            
            # Extract like/dislike counts
            like_elem = soup.find(id='video-like-count')
            if like_elem:
                try:
                    video.like_count = int(like_elem.get_text().strip() or 0)
                except ValueError:
                    video.like_count = 0
            
            dislike_elem = soup.find(id='video-dislike-count')
            if dislike_elem:
                try:
                    video.dislike_count = int(dislike_elem.get_text().strip() or 0)
                except ValueError:
                    video.dislike_count = 0
            
            # Extract description
            desc_elem = soup.find(id='video-description')
            if desc_elem:
                video.description = markdownify.markdownify(desc_elem.decode_contents())
                video.description_links = [a.get('href') for a in desc_elem.find_all('a') if a.get('href')]
            
            # Extract hashtags
            hashtag_elem = soup.find(id='video-hashtags')
            if hashtag_elem:
                video.hashtags = [tag.get_text().strip() for tag in hashtag_elem.find_all('li')]
            
            # Extract thumbnail
            video_elem = soup.find('video', id='player')
            if video_elem and video_elem.get('poster'):
                video.thumbnail_url = video_elem.get('poster')
            
            # Extract channel info
            channel_banner = soup.find(class_='channel-banner')
            if channel_banner:
                channel_name_elem = channel_banner.find(class_='name')
                if channel_name_elem and channel_name_elem.find('a'):
                    video.channel_name = channel_name_elem.get_text().strip()
                    video.channel_id = channel_name_elem.find('a').get('href', '').split('/')[-2]
            
            # Extract category and sensitivity
            detail_table = soup.find('table', class_='video-detail-list')
            if detail_table:
                for row in detail_table.find_all('tr'):
                    cells = row.find_all('td')
                    if len(cells) >= 2:
                        label = cells[0].get_text().strip().lower()
                        value = cells[1].get_text().strip()
                        
                        if 'category' in label:
                            video.category = value
                        elif 'sensitivity' in label:
                            video.sensitivity = value
            
            return video
            
        except Exception as e:
            logger.error(f"Failed to get video {video_id}: {e}")
            return None
        finally:
            self.reset_webdriver()
    
    def get_channel_info(self, channel_id: str) -> Optional[ChannelData]:
        """Get detailed channel information"""
        try:
            url = f"{self.base_url}channel/{channel_id}/"
            page_source = self._fetch_page(url, click_element='ABOUT')
            
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
    
    def get_channels(self, channel_ids, get_channel_about=True, get_channel_videos=True):
        """Get channel information (backward compatible)"""
        if isinstance(channel_ids, str):
            channel_ids = [channel_ids]
        
        abouts = pd.DataFrame()
        videos = pd.DataFrame()
        
        for channel_id in channel_ids:
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
            url = f"{self.base_url}channel/{channel_id}/"
            page_source = self._fetch_page(url, click_element='VIDEOS')
            
            soup = BeautifulSoup(page_source, 'html.parser')
            
            videos = []
            video_containers = soup.find_all(class_='channel-videos-container')
            
            for i, container in enumerate(video_containers, 1):
                try:
                    video = VideoData()
                    video.channel_id = channel_id
                    video.type = "channel"
                    video.rank = i
                    
                    # Extract title and ID
                    title_elem = container.find(class_='channel-videos-title')
                    if title_elem and title_elem.find('a'):
                        video.title = title_elem.get_text().strip()
                        href = title_elem.find('a').get('href', '')
                        video.id = href.split('/')[-2] if href else ''
                        video.video_url = f"https://www.bitchute.com{href}" if href else ''
                    
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
                        video.view_count = self._parse_view_count(views_text)
                    
                    # Extract creation date
                    date_elem = container.find(class_='channel-videos-details')
                    if date_elem:
                        video.created_at = date_elem.get_text().strip()
                    
                    videos.append(video)
                    
                    if max_videos and len(videos) >= max_videos:
                        break
                        
                except Exception as e:
                    if self.verbose:
                        logger.warning(f"Failed to parse video container {i}: {e}")
                    continue
            
            # Convert to DataFrame
            data = [asdict(video) for video in videos]
            df = pd.DataFrame(data)
            
            if self.verbose:
                logger.info(f"Found {len(videos)} videos for channel {channel_id}")
            
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
        
        for video_id in video_ids:
            try:
                video_data = self.get_video(video_id)
                if video_data:
                    videos.append(asdict(video_data))
            except Exception as e:
                logger.error(f"Failed to get video {video_id}: {e}")
                continue
        
        return pd.DataFrame(videos)
    
    def get_recommended_channels(self, extended=True):
        """Get recommended channels (backward compatible)"""
        try:
            page_source = self._fetch_page(self.base_url)
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
                        if self.verbose:
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
    
    def debug_page_info(self, url: str = None) -> dict:
        """Debug method to inspect page structure"""
        if not url:
            url = self.base_url
        
        try:
            page_source = self._fetch_page(url, wait_for_element='.q-card')
            soup = BeautifulSoup(page_source, 'html.parser')
            
            current_url = self.wd.current_url if self.wd else url
            
            # Count elements
            q_cards = len(soup.select('.q-card'))
            video_cards = len(soup.select('.video-card'))
            hashtag_links = len(soup.select('a[href*="/hashtag/"]'))
            
            # Get page title
            title_elem = soup.find('title')
            title = title_elem.get_text().strip() if title_elem else "No title"
            
            debug_info = {
                'requested_url': url,
                'actual_url': current_url,
                'page_title': title,
                'q_cards_found': q_cards,
                'video_cards_found': video_cards,
                'hashtag_links_found': hashtag_links,
                'page_source_length': len(page_source)
            }
            
            return debug_info
            
        except Exception as e:
            logger.error(f"Debug failed for {url}: {e}")
            return {'error': str(e)}
        finally:
            self.reset_webdriver()
    
    def debug_single_video_enhancement(self, video_id: str) -> dict:
        """Debug method to test enhanced data collection on a single video"""
        
        print(f"🔍 Debugging enhanced collection for video: {video_id}")
        print("="*60)
        
        try:
            # Create a basic VideoData object
            basic_video = VideoData()
            basic_video.id = video_id
            basic_video.title = "Test Video"
            
            # Test the enhancement process
            print("1. Navigating to video page...")
            enhanced_video = self._get_detailed_video_data(basic_video)
            
            print("2. Checking what data was collected:")
            print(f"   Title: {'✓' if enhanced_video.title else '✗'} {enhanced_video.title[:50]}...")
            print(f"   Description: {'✓' if enhanced_video.description else '✗'} ({len(enhanced_video.description)} chars)")
            print(f"   View count: {'✓' if enhanced_video.view_count > 0 else '✗'} {enhanced_video.view_count:,}")
            print(f"   Like count: {'✓' if enhanced_video.like_count > 0 else '✗'} {enhanced_video.like_count}")
            print(f"   Hashtags: {'✓' if enhanced_video.hashtags else '✗'} {len(enhanced_video.hashtags)} tags")
            print(f"   Category: {'✓' if enhanced_video.category else '✗'} {enhanced_video.category}")
            print(f"   Sensitivity: {'✓' if enhanced_video.sensitivity else '✗'} {enhanced_video.sensitivity}")
            
            return {
                'success': True,
                'video_data': enhanced_video,
                'has_description': bool(enhanced_video.description),
                'has_hashtags': bool(enhanced_video.hashtags),
                'has_category': bool(enhanced_video.category)
            }
            
        except Exception as e:
            print(f"❌ Error: {e}")
            return {'success': False, 'error': str(e)}
        finally:
            self.reset_webdriver()


    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.reset_webdriver()

# Legacy function for backward compatibility
def process_views(views):
    """Legacy function for processing view counts"""
    crawler = Crawler()
    return crawler._parse_view_count(str(views))