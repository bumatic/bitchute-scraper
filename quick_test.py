#!/usr/bin/env python3
"""
Quick test script to verify the trending videos functionality
"""

import bitchute as bc

def test_trending_simple():
    """Test trending videos with minimal setup"""
    print("Testing trending videos...")
    
    # Create crawler
    b = bc.Crawler(verbose=True)
    
    try:
        # Get trending videos
        trending_videos = b.get_trending_videos()
        
        print(f"Success! Found {len(trending_videos)} trending videos")
        
        if not trending_videos.empty:
            print("\nFirst few videos:")
            print(trending_videos[['title', 'channel_name', 'view_count']].head(3))
        else:
            print("No videos found - checking page content...")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        b.reset_webdriver()

def test_direct_url():
    """Test by directly accessing trending URL"""
    print("\nTesting direct URL access...")
    
    from bitchute.bitchute import EnhancedCrawler
    
    crawler = EnhancedCrawler(verbose=True)
    
    try:
        # Test direct URL access
        trending_url = 'https://www.bitchute.com/trending/'
        page_source = crawler._fetch_page(trending_url, scroll=False)
        
        print(f"Page loaded successfully. Content length: {len(page_source)} characters")
        
        # Check if we can find any video-related content
        if 'video' in page_source.lower():
            print("✓ Found video-related content")
        else:
            print("✗ No video content found")
            
    except Exception as e:
        print(f"Error with direct URL: {e}")
    finally:
        crawler.reset_webdriver()

if __name__ == "__main__":
    test_trending_simple()
    test_direct_url()