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

import requests
import json
from typing import Dict, Any, Optional

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
        """Get detailed data for a single video by visiting its page - UPDATED VERSION"""
        if not video.id:
            return video
        
        try:
            video_url = f"{self.base_url}video/{video.id}/"
            
            if self.verbose:
                logger.debug(f'Fetching video page: {video_url}')
            
            # Ensure we have a webdriver instance
            if not self.wd:
                if self.verbose:
                    logger.debug("Creating WebDriver instance for video page access...")
                self.create_webdriver()
                if not self.wd:
                    raise Exception("Failed to create WebDriver instance")
            
            # Navigate to video page
            self.wd.get(video_url)
            
            # Wait for page to load with updated selectors
            wait = WebDriverWait(self.wd, 15)
            
            try:
                # Wait for the main content area to load
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".bc-text-break, .q-item__label")))
                
                # Give extra time for dynamic content and "Show more" functionality
                time.sleep(3)
                
                # Try to click "Show more" button if present to expand description
                try:
                    show_more_buttons = self.wd.find_elements(By.XPATH, "//div[contains(text(), 'Show more')]")
                    for button in show_more_buttons:
                        if button.is_displayed() and button.is_enabled():
                            self.wd.execute_script("arguments[0].click();", button)
                            time.sleep(1)  # Wait for content to expand
                            if self.verbose:
                                logger.debug("Clicked 'Show more' button to expand description")
                            break
                except Exception as e:
                    if self.verbose:
                        logger.debug(f"No 'Show more' button found or couldn't click: {e}")
                
            except TimeoutException:
                if self.verbose:
                    logger.warning(f"Timeout waiting for page elements to load: {video_url}")
                # Continue anyway
            
            # Additional check: ensure we're on the right page
            current_url = self.wd.current_url
            if video.id not in current_url:
                if self.verbose:
                    logger.warning(f"URL mismatch. Expected {video.id}, got {current_url}")
                return video
            
            # Get page source after ensuring it's loaded and expanded
            page_source = self.wd.page_source
            if not page_source:
                if self.verbose:
                    logger.warning(f"No page source retrieved for {video_url}")
                return video
            
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # Use the updated parsing method
            enhanced_video = self._parse_video_page(soup, video)
            
            return enhanced_video
            
        except Exception as e:
            if self.verbose:
                logger.warning(f"Failed to get detailed data for video {video.id}: {e}")
            return video

    
    def _parse_video_page(self, soup: BeautifulSoup, base_video: VideoData) -> VideoData:
        """Parse detailed video information from video page - UPDATED FOR CURRENT BITCHUTE"""
        video = base_video  # Start with existing data
        
        try:
            if self.verbose:
                logger.debug(f"Parsing video page for {video.id}")
            
            # 1. Extract title from the responsive font element
            title_elem = soup.select_one('.bc-text-break.bc-responsive-font')
            if title_elem:
                try:
                    page_title = title_elem.get_text().strip()
                    if page_title:
                        video.title = page_title
                        if self.verbose:
                            logger.debug(f"Extracted title: {page_title}")
                except Exception as e:
                    if self.verbose:
                        logger.debug(f"Error extracting title: {e}")
            
            # 2. Extract view count and publish time from subtitle element
            view_time_elem = soup.select_one('.q-item__label.text-subtitle1')
            if view_time_elem:
                try:
                    view_time_text = view_time_elem.get_text().strip()
                    if self.verbose:
                        logger.debug(f"View/time text: {view_time_text}")
                    
                    # Extract view count (pattern: "2466 Views -")
                    import re
                    view_match = re.search(r'(\d+(?:,\d+)*)\s*Views', view_time_text)
                    if view_match:
                        view_count_str = view_match.group(1).replace(',', '')
                        video.view_count = int(view_count_str)
                        if self.verbose:
                            logger.debug(f"Extracted view count: {video.view_count}")
                    
                    # Extract publish time (pattern: "11 hours ago")
                    time_match = re.search(r'(\d+\s+(?:hours?|days?|weeks?|months?|years?)\s+ago)', view_time_text)
                    if time_match:
                        video.created_at = time_match.group(1)
                        if self.verbose:
                            logger.debug(f"Extracted publish time: {video.created_at}")
                            
                except Exception as e:
                    if self.verbose:
                        logger.debug(f"Error extracting view/time data: {e}")
            
            # 3. Extract channel information
            channel_link = soup.select_one('a[href*="/channel/"]')
            if channel_link:
                try:
                    # Extract channel ID from URL
                    channel_href = channel_link.get('href', '')
                    if channel_href:
                        # Pattern: /channel/kCBxN1oEVOa0
                        channel_id = channel_href.split('/channel/')[-1].rstrip('/')
                        if channel_id:
                            video.channel_id = channel_id
                            if self.verbose:
                                logger.debug(f"Extracted channel ID: {channel_id}")
                    
                    # Extract channel name from the ellipsis text-subtitle1 element within channel link
                    channel_name_elem = channel_link.select_one('.q-item__label.ellipsis.text-subtitle1')
                    if channel_name_elem:
                        channel_name = channel_name_elem.get_text().strip()
                        if channel_name:
                            video.channel_name = channel_name
                            if self.verbose:
                                logger.debug(f"Extracted channel name: {channel_name}")
                                
                except Exception as e:
                    if self.verbose:
                        logger.debug(f"Error extracting channel info: {e}")
            
            # 4. Extract subscriber count
            subscriber_elem = soup.select_one('.q-item__label--caption')
            if subscriber_elem:
                try:
                    subscriber_text = subscriber_elem.get_text().strip()
                    # Pattern: "22.1K Subscribers"
                    if 'subscribers' in subscriber_text.lower():
                        # Extract the number part for potential processing
                        import re
                        sub_match = re.search(r'([\d.]+[KMB]?)\s*Subscribers', subscriber_text, re.IGNORECASE)
                        if sub_match:
                            # Store as string to preserve formatting (22.1K)
                            video.channel_name += f" ({sub_match.group(1)} subscribers)"
                            if self.verbose:
                                logger.debug(f"Extracted subscriber info: {sub_match.group(1)}")
                except Exception as e:
                    if self.verbose:
                        logger.debug(f"Error extracting subscriber count: {e}")
            
            # 5. Extract like and dislike counts
            try:
                # Like button with thumb_up icon
                like_button = soup.select_one('button:has(i[aria-label="thumb_up"], i:contains("thumb_up"))')
                if not like_button:
                    # Alternative: look for button containing thumb_up text
                    like_buttons = soup.select('button')
                    for btn in like_buttons:
                        if 'thumb_up' in str(btn) and 'text-green' in btn.get('class', []):
                            like_button = btn
                            break
                
                if like_button:
                    like_span = like_button.select_one('span.block')
                    if like_span:
                        like_text = like_span.get_text().strip()
                        if like_text.isdigit():
                            video.like_count = int(like_text)
                            if self.verbose:
                                logger.debug(f"Extracted like count: {video.like_count}")
                
                # Dislike button with thumb_down icon
                dislike_button = soup.select_one('button:has(i[aria-label="thumb_down"], i:contains("thumb_down"))')
                if not dislike_button:
                    # Alternative: look for button containing thumb_down text
                    dislike_buttons = soup.select('button')
                    for btn in dislike_buttons:
                        if 'thumb_down' in str(btn) and 'text-red' in btn.get('class', []):
                            dislike_button = btn
                            break
                
                if dislike_button:
                    dislike_span = dislike_button.select_one('span.block')
                    if dislike_span:
                        dislike_text = dislike_span.get_text().strip()
                        if dislike_text.isdigit():
                            video.dislike_count = int(dislike_text)
                            if self.verbose:
                                logger.debug(f"Extracted dislike count: {video.dislike_count}")
                                
            except Exception as e:
                if self.verbose:
                    logger.debug(f"Error extracting like/dislike counts: {e}")
            
            # 6. Extract sensitivity information
            try:
                sensitivity_elem = soup.select_one('.q-item__label.text-subtitle1:contains("Sensitivity")')
                if not sensitivity_elem:
                    # Look for any element containing "Sensitivity -"
                    for elem in soup.select('.q-item__label'):
                        if 'sensitivity' in elem.get_text().lower():
                            sensitivity_elem = elem
                            break
                
                if sensitivity_elem:
                    sensitivity_text = sensitivity_elem.get_text().strip()
                    # Pattern: "Sensitivity - Normal (BBFC 12)"
                    if 'sensitivity' in sensitivity_text.lower():
                        # Extract everything after "Sensitivity -"
                        parts = sensitivity_text.split(' - ', 1)
                        if len(parts) > 1:
                            video.sensitivity = parts[1].strip()
                            if self.verbose:
                                logger.debug(f"Extracted sensitivity: {video.sensitivity}")
                                
            except Exception as e:
                if self.verbose:
                    logger.debug(f"Error extracting sensitivity: {e}")
            
            # 7. Extract description from bc-description element
            try:
                desc_elem = soup.select_one('.bc-description')
                if desc_elem:
                    # Get all text content
                    desc_text = desc_elem.get_text().strip()
                    if desc_text:
                        video.description = desc_text
                        if self.verbose:
                            logger.debug(f"Extracted description: {len(desc_text)} characters")
                    
                    # Extract links from description
                    links = []
                    for link in desc_elem.select('a[href]'):
                        href = link.get('href')
                        if href and href.startswith('http'):
                            links.append(href)
                    
                    if links:
                        video.description_links = links
                        if self.verbose:
                            logger.debug(f"Extracted {len(links)} description links")
                            
            except Exception as e:
                if self.verbose:
                    logger.debug(f"Error extracting description: {e}")
            
            # 8. Extract hashtags (if present)
            try:
                # Look for hashtag links in the area after view count
                hashtag_area = soup.select('a[href*="/hashtag/"]')
                hashtags = []
                
                for hashtag_link in hashtag_area:
                    try:
                        # Extract hashtag content
                        hashtag_content = hashtag_link.select_one('.q-chip__content')
                        if hashtag_content:
                            hashtag_text = hashtag_content.get_text().strip()
                            if hashtag_text:
                                hashtags.append(f"#{hashtag_text}")
                    except Exception:
                        continue
                
                if hashtags:
                    video.hashtags = hashtags
                    if self.verbose:
                        logger.debug(f"Extracted hashtags: {hashtags}")
                        
            except Exception as e:
                if self.verbose:
                    logger.debug(f"Error extracting hashtags: {e}")
            
            # 9. Extract thumbnail from video iframe or meta tags
            try:
                # Try iframe first
                iframe = soup.select_one('iframe[src*="embed"]')
                if iframe:
                    iframe_src = iframe.get('src', '')
                    if iframe_src and 'embed' in iframe_src:
                        # Try to construct thumbnail URL from embed URL
                        # Pattern: https://www.bitchute.com/api/beta9/embed/6OJw7KjHQ27o
                        video_id_match = re.search(r'/embed/([^/?]+)', iframe_src)
                        if video_id_match:
                            extracted_video_id = video_id_match.group(1)
                            # Update video ID if not already set
                            if not video.id:
                                video.id = extracted_video_id
                            # Construct thumbnail URL (common pattern for video thumbnails)
                            video.thumbnail_url = f"https://static-3.bitchute.com/live/cover_images/{extracted_video_id[:12]}/{extracted_video_id}_640x360.jpg"
                            if self.verbose:
                                logger.debug(f"Constructed thumbnail URL from iframe")
                
                # Fallback to meta og:image
                if not video.thumbnail_url:
                    meta_image = soup.select_one('meta[property="og:image"]')
                    if meta_image:
                        thumbnail_url = meta_image.get('content', '')
                        if thumbnail_url and thumbnail_url.startswith('http'):
                            video.thumbnail_url = thumbnail_url
                            if self.verbose:
                                logger.debug(f"Extracted thumbnail from meta tag")
                                
            except Exception as e:
                if self.verbose:
                    logger.debug(f"Error extracting thumbnail: {e}")
            
            # 10. Extract video duration from iframe or other sources
            try:
                iframe = soup.select_one('iframe[src*="embed"]')
                if iframe:
                    iframe_src = iframe.get('src', '')
                    # Look for duration parameter in iframe src
                    duration_match = re.search(r'duration=([^&]+)', iframe_src)
                    if duration_match:
                        video.duration = duration_match.group(1)
                        if self.verbose:
                            logger.debug(f"Extracted duration: {video.duration}")
                            
            except Exception as e:
                if self.verbose:
                    logger.debug(f"Error extracting duration: {e}")
            
            if self.verbose:
                logger.debug(f"Video parsing complete for {video.id}")
                logger.debug(f"Final data - Title: {bool(video.title)}, Views: {video.view_count}, "
                            f"Likes: {video.like_count}, Description: {len(video.description) if video.description else 0} chars")
            
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
        """Debug method to test enhanced data collection on a single video - FIXED VERSION"""
        
        print(f"🔍 Debugging enhanced collection for video: {video_id}")
        print("="*60)
        
        try:
            # CRITICAL FIX: Ensure WebDriver is created before any operations
            if not self.wd:
                print("1. Creating WebDriver instance...")
                self.create_webdriver()
                if not self.wd:
                    return {'success': False, 'error': 'Failed to create WebDriver'}
                print("   ✓ WebDriver created successfully")
            else:
                print("1. Using existing WebDriver instance...")
            
            # Create a basic VideoData object
            basic_video = VideoData()
            basic_video.id = video_id
            basic_video.title = "Test Video"
            
            # Test the enhancement process
            print("2. Navigating to video page...")
            enhanced_video = self._get_detailed_video_data(basic_video)
            
            print("3. Checking what data was collected:")
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
            # Clean up WebDriver
            self.reset_webdriver()

    def diagnose_video_page_html(self, video_id: str) -> dict:
        """Diagnostic method to capture and analyze the current HTML structure"""
        
        print(f"🔍 Analyzing HTML structure for video: {video_id}")
        print("="*60)
        
        try:
            # Ensure WebDriver is created
            if not self.wd:
                self.create_webdriver()
                if not self.wd:
                    return {'success': False, 'error': 'Failed to create WebDriver'}
            
            video_url = f"{self.base_url}video/{video_id}/"
            print(f"Navigating to: {video_url}")
            
            # Navigate to video page
            self.wd.get(video_url)
            time.sleep(5)  # Give page time to fully load
            
            # Get page source
            page_source = self.wd.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # Collect diagnostic information
            diagnostic_info = {
                'success': True,
                'current_url': self.wd.current_url,
                'page_title': soup.find('title').get_text() if soup.find('title') else 'No title',
                'page_source_length': len(page_source)
            }
            
            print(f"Current URL: {diagnostic_info['current_url']}")
            print(f"Page title: {diagnostic_info['page_title']}")
            print(f"Page source length: {diagnostic_info['page_source_length']} characters")
            
            # Look for video title in various possible locations
            print("\n📍 Searching for video title...")
            title_selectors = [
                {'name': 'ID: video-title', 'selector': '#video-title'},
                {'name': 'Class: page-title', 'selector': '.page-title'},
                {'name': 'H1 tags', 'selector': 'h1'},
                {'name': 'Title in metadata', 'selector': 'meta[property="og:title"]'},
                {'name': 'Any element with "title" class', 'selector': '.title'},
            ]
            
            for selector_info in title_selectors:
                elements = soup.select(selector_info['selector'])
                if elements:
                    for i, elem in enumerate(elements[:3]):  # Show first 3 matches
                        if selector_info['selector'].startswith('meta'):
                            content = elem.get('content', 'No content')
                        else:
                            content = elem.get_text().strip()
                        print(f"   ✓ {selector_info['name']} [{i+1}]: {content[:100]}...")
                else:
                    print(f"   ✗ {selector_info['name']}: Not found")
            
            # Look for view count in various locations
            print("\n📍 Searching for view count...")
            view_selectors = [
                {'name': 'ID: video-view-count', 'selector': '#video-view-count'},
                {'name': 'Class: video-statistics', 'selector': '.video-statistics'},
                {'name': 'Text containing "views"', 'selector': None},  # Special case
                {'name': 'Any stats section', 'selector': '.stats, .statistics, .view-count'},
            ]
            
            for selector_info in view_selectors:
                if selector_info['selector']:
                    elements = soup.select(selector_info['selector'])
                    if elements:
                        for i, elem in enumerate(elements[:2]):
                            content = elem.get_text().strip()
                            print(f"   ✓ {selector_info['name']} [{i+1}]: {content[:100]}...")
                    else:
                        print(f"   ✗ {selector_info['name']}: Not found")
                else:
                    # Special case: search for text containing "views"
                    view_text_elements = soup.find_all(text=lambda text: text and 'view' in text.lower())
                    if view_text_elements:
                        for i, text in enumerate(view_text_elements[:3]):
                            print(f"   ✓ {selector_info['name']} [{i+1}]: {text.strip()[:100]}...")
                    else:
                        print(f"   ✗ {selector_info['name']}: Not found")
            
            # Look for description
            print("\n📍 Searching for description...")
            desc_selectors = [
                {'name': 'ID: video-description', 'selector': '#video-description'},
                {'name': 'Class: video-detail-text', 'selector': '.video-detail-text'},
                {'name': 'Class: description', 'selector': '.description'},
                {'name': 'Meta description', 'selector': 'meta[name="description"]'},
            ]
            
            for selector_info in desc_selectors:
                if selector_info['selector'].startswith('meta'):
                    elements = soup.select(selector_info['selector'])
                    if elements:
                        content = elements[0].get('content', 'No content')
                        print(f"   ✓ {selector_info['name']}: {content[:100]}...")
                    else:
                        print(f"   ✗ {selector_info['name']}: Not found")
                else:
                    elements = soup.select(selector_info['selector'])
                    if elements:
                        content = elements[0].get_text().strip()
                        print(f"   ✓ {selector_info['name']}: {content[:100]}...")
                    else:
                        print(f"   ✗ {selector_info['name']}: Not found")
            
            # Look for like/dislike counts
            print("\n📍 Searching for like/dislike counts...")
            like_selectors = [
                {'name': 'ID: video-like-count', 'selector': '#video-like-count'},
                {'name': 'ID: video-dislike-count', 'selector': '#video-dislike-count'},
                {'name': 'Classes with "like"', 'selector': '.like, .thumbs-up'},
                {'name': 'Classes with "dislike"', 'selector': '.dislike, .thumbs-down'},
            ]
            
            for selector_info in like_selectors:
                elements = soup.select(selector_info['selector'])
                if elements:
                    for i, elem in enumerate(elements[:2]):
                        content = elem.get_text().strip()
                        print(f"   ✓ {selector_info['name']} [{i+1}]: {content[:50]}...")
                else:
                    print(f"   ✗ {selector_info['name']}: Not found")
            
            # Save a snippet of the HTML around key areas for manual inspection
            print("\n📍 HTML snippets for manual inspection...")
            
            # Try to find the main content area
            main_content = soup.find('main') or soup.find('body')
            if main_content:
                # Save the first 2000 characters of the main content
                main_html = str(main_content)[:2000]
                diagnostic_info['main_content_snippet'] = main_html
                print(f"   Main content snippet saved ({len(main_html)} chars)")
            
            # Look for any obvious video-related sections
            video_sections = soup.find_all(['div', 'section'], class_=lambda x: x and any(
                keyword in x.lower() for keyword in ['video', 'player', 'content', 'main']
            ))
            
            if video_sections:
                print(f"   Found {len(video_sections)} potential video-related sections")
                diagnostic_info['video_sections_found'] = len(video_sections)
            
            return diagnostic_info
            
        except Exception as e:
            print(f"❌ Diagnostic failed: {e}")
            return {'success': False, 'error': str(e)}
        finally:
            self.reset_webdriver()

    def _get_video_data_via_api(self, video_id: str) -> Optional[Dict[Any, Any]]:
        """Get video data directly from BitChute's API endpoint"""
        
        api_url = "https://api.bitchute.com/api/beta9/video"
        
        headers = {
            'accept': 'application/json, text/plain, */*',
            'accept-language': 'en-US,en;q=0.9',
            'content-type': 'application/json',
            'origin': 'https://www.bitchute.com',
            'referer': 'https://www.bitchute.com/',
            'sec-ch-ua': '"Not)A;Brand";v="8", "Chromium";v="138", "Google Chrome";v="138"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"macOS"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-site',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36'
        }
        
        payload = {"video_id": video_id}
        
        try:
            if self.verbose:
                logger.debug(f"Making API request for video {video_id}")
            
            response = requests.post(
                api_url, 
                headers=headers, 
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                api_data = response.json()
                if self.verbose:
                    logger.debug(f"API response received: {len(str(api_data))} characters")
                return api_data
            else:
                if self.verbose:
                    logger.warning(f"API request failed with status {response.status_code}")
                return None
                
        except requests.RequestException as e:
            if self.verbose:
                logger.warning(f"API request exception: {e}")
            return None
        except json.JSONDecodeError as e:
            if self.verbose:
                logger.warning(f"API response JSON decode error: {e}")
            return None

    def _parse_api_response(self, api_data: Dict[Any, Any], base_video: VideoData) -> VideoData:
        """Parse video data from API response into VideoData object"""
        
        video = base_video
        
        try:
            if self.verbose:
                logger.debug(f"Parsing API response for video {video.id}")
                logger.debug(f"API data keys: {list(api_data.keys()) if api_data else 'None'}")
            
            if not api_data:
                return video
            
            # Map API fields to VideoData fields
            # Note: We'll need to discover the actual field names from the API response
            
            # Title
            if 'title' in api_data:
                video.title = api_data['title']
            elif 'name' in api_data:
                video.title = api_data['name']
            
            # View count
            if 'view_count' in api_data:
                video.view_count = int(api_data['view_count']) if api_data['view_count'] else 0
            elif 'views' in api_data:
                video.view_count = int(api_data['views']) if api_data['views'] else 0
            
            # Like/Dislike counts
            if 'like_count' in api_data:
                video.like_count = int(api_data['like_count']) if api_data['like_count'] else 0
            elif 'likes' in api_data:
                video.like_count = int(api_data['likes']) if api_data['likes'] else 0
                
            if 'dislike_count' in api_data:
                video.dislike_count = int(api_data['dislike_count']) if api_data['dislike_count'] else 0
            elif 'dislikes' in api_data:
                video.dislike_count = int(api_data['dislikes']) if api_data['dislikes'] else 0
            
            # Description
            if 'description' in api_data:
                video.description = api_data['description'] or ""
            
            # Duration
            if 'duration' in api_data:
                video.duration = api_data['duration'] or ""
            elif 'length' in api_data:
                video.duration = api_data['length'] or ""
            
            # Channel information
            if 'channel' in api_data:
                channel_data = api_data['channel']
                if isinstance(channel_data, dict):
                    video.channel_name = channel_data.get('name', video.channel_name)
                    video.channel_id = channel_data.get('id', video.channel_id)
            elif 'uploader' in api_data:
                uploader_data = api_data['uploader']
                if isinstance(uploader_data, dict):
                    video.channel_name = uploader_data.get('name', video.channel_name)
                    video.channel_id = uploader_data.get('id', video.channel_id)
            
            # Thumbnail
            if 'thumbnail' in api_data:
                video.thumbnail_url = api_data['thumbnail'] or ""
            elif 'poster' in api_data:
                video.thumbnail_url = api_data['poster'] or ""
            elif 'image' in api_data:
                video.thumbnail_url = api_data['image'] or ""
            
            # Created date
            if 'created_at' in api_data:
                video.created_at = api_data['created_at'] or ""
            elif 'upload_date' in api_data:
                video.created_at = api_data['upload_date'] or ""
            elif 'published' in api_data:
                video.created_at = api_data['published'] or ""
            
            # Hashtags
            if 'hashtags' in api_data:
                hashtags = api_data['hashtags']
                if isinstance(hashtags, list):
                    video.hashtags = [f"#{tag}" if not tag.startswith('#') else tag for tag in hashtags]
            elif 'tags' in api_data:
                tags = api_data['tags']
                if isinstance(tags, list):
                    video.hashtags = [f"#{tag}" if not tag.startswith('#') else tag for tag in tags]
            
            # Category
            if 'category' in api_data:
                video.category = api_data['category'] or ""
            
            # Sensitivity
            if 'sensitivity' in api_data:
                video.sensitivity = api_data['sensitivity'] or ""
            elif 'rating' in api_data:
                video.sensitivity = api_data['rating'] or ""
            
            if self.verbose:
                logger.debug(f"API parsing complete for {video.id}")
            
            return video
            
        except Exception as e:
            if self.verbose:
                logger.warning(f"Error parsing API response for {video.id}: {e}")
            return video

    def _get_detailed_video_data_api(self, video: VideoData) -> VideoData:
        """Get detailed video data using API instead of HTML parsing"""
        
        if not video.id:
            return video
        
        try:
            if self.verbose:
                logger.debug(f"Fetching video data via API for {video.id}")
            
            # Get data from API
            api_data = self._get_video_data_via_api(video.id)
            
            if api_data:
                # Parse API response
                enhanced_video = self._parse_api_response(api_data, video)
                return enhanced_video
            else:
                if self.verbose:
                    logger.warning(f"No API data received for {video.id}, falling back to HTML parsing")
                # Fallback to HTML parsing if API fails
                return self._get_detailed_video_data_html_fallback(video)
                
        except Exception as e:
            if self.verbose:
                logger.warning(f"API method failed for {video.id}: {e}, falling back to HTML parsing")
            # Fallback to HTML parsing if API method fails completely
            return self._get_detailed_video_data_html_fallback(video)

    def _get_detailed_video_data_html_fallback(self, video: VideoData) -> VideoData:
        """Fallback to HTML parsing if API fails"""
        # This would be your existing HTML parsing method
        # Renamed to avoid conflicts
        try:
            return self._get_detailed_video_data_original(video)
        except Exception as e:
            if self.verbose:
                logger.warning(f"HTML fallback also failed for {video.id}: {e}")
            return video

    def debug_api_response(self, video_id: str) -> dict:
        """Debug method to see what the API returns"""
        
        print(f"🔍 Testing API endpoint for video: {video_id}")
        print("="*60)
        
        try:
            api_data = self._get_video_data_via_api(video_id)
            
            if api_data:
                print("✅ API request successful!")
                print(f"📊 Response data:")
                
                # Pretty print the API response
                print(json.dumps(api_data, indent=2, ensure_ascii=False))
                
                # Test parsing
                basic_video = VideoData(id=video_id)
                parsed_video = self._parse_api_response(api_data, basic_video)
                
                print(f"\n📋 Parsed data:")
                print(f"   Title: {parsed_video.title}")
                print(f"   Views: {parsed_video.view_count:,}")
                print(f"   Likes: {parsed_video.like_count}")
                print(f"   Dislikes: {parsed_video.dislike_count}")
                print(f"   Description: {len(parsed_video.description)} chars")
                print(f"   Duration: {parsed_video.duration}")
                print(f"   Channel: {parsed_video.channel_name}")
                print(f"   Hashtags: {len(parsed_video.hashtags)} tags")
                
                return {
                    'success': True,
                    'api_data': api_data,
                    'parsed_video': parsed_video,
                    'api_keys': list(api_data.keys()) if isinstance(api_data, dict) else []
                }
            else:
                print("❌ API request failed")
                return {'success': False, 'error': 'No data received from API'}
                
        except Exception as e:
            print(f"❌ Error: {e}")
            return {'success': False, 'error': str(e)}

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