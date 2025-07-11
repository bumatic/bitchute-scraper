#!/usr/bin/env python3
"""
Debug script to examine the actual HTML structure of Bitchute trending page
"""

import bitchute as bc
from bs4 import BeautifulSoup

def debug_html_structure():
    """Debug the actual HTML structure to find the right selectors"""
    
    crawler = bc.EnhancedCrawler(verbose=True)
    
    try:
        # Get the trending page
        trending_url = 'https://www.bitchute.com/trending/'
        page_source = crawler._fetch_page(trending_url, scroll=False)
        
        soup = BeautifulSoup(page_source, 'html.parser')
        
        print("=== DEBUGGING HTML STRUCTURE ===\n")
        
        # Look for various potential video containers
        selectors_to_try = [
            '.video-card',
            '.video-result-container', 
            '[data-video-id]',
            '.q-card',
            '.video-item',
            'article',
            '.media',
            '.content-item',
            '[href*="/video/"]'
        ]
        
        for selector in selectors_to_try:
            elements = soup.select(selector)
            print(f"Selector '{selector}': Found {len(elements)} elements")
            
            if elements and len(elements) > 0:
                print(f"  First element HTML (truncated):")
                element_html = str(elements[0])[:500]
                print(f"  {element_html}...")
                print()
        
        # Look for any links that contain "/video/" in href
        video_links = soup.select('a[href*="/video/"]')
        print(f"Found {len(video_links)} video links")
        
        if video_links:
            print("First few video links:")
            for i, link in enumerate(video_links[:3]):
                href = link.get('href', '')
                text = link.get_text().strip()
                print(f"  {i+1}. href='{href}', text='{text}'")
                print(f"     Parent: {link.parent.name} with classes: {link.parent.get('class', [])}")
        
        print("\n=== SAMPLE HTML STRUCTURE ===")
        # Get a sample of the page structure
        body = soup.find('body')
        if body:
            # Find all elements with classes that might contain videos
            all_elements = body.find_all(attrs={'class': True})
            class_counts = {}
            for elem in all_elements:
                for cls in elem.get('class', []):
                    if any(keyword in cls.lower() for keyword in ['video', 'card', 'item', 'content', 'media']):
                        class_counts[cls] = class_counts.get(cls, 0) + 1
            
            print("Classes that might contain video content:")
            for cls, count in sorted(class_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
                print(f"  .{cls}: {count} occurrences")
        
    except Exception as e:
        print(f"Error during debugging: {e}")
    finally:
        crawler.reset_webdriver()

if __name__ == "__main__":
    debug_html_structure()