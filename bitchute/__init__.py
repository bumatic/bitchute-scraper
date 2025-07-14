"""
BitChute API Scraper
Modern Python package for scraping BitChute using official API endpoints
"""

from .bitchute import BitChuteAPI, Video, Channel, Hashtag, TokenManager

__version__ = "2.0.0"
__author__ = "Marcus Burkhardt"
__email__ = "marcus.burkhardt@gmail.com"
__description__ = "A package to scrape BitChute platform recommendations."

__all__ = [
    'BitChuteAPI',
    'Video', 
    'Channel',
    'Hashtag',
    'TokenManager'
]