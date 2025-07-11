#!/usr/bin/env python3
"""
Debug script to see what labels are being found in q-item__section
"""

import bitchute as bc
from bs4 import BeautifulSoup

def debug_label_extraction():
    """Debug what labels are actually found"""
    
    crawler = bc.EnhancedCrawler(verbose=True)
    
    try:
        # Get the trending page
        trending_url = 'https://www.bitchute.com/trending/'
        page_source = crawler._fetch_page(trending_url, scroll=False)
        
        soup = BeautifulSoup(page_source, 'html.parser')
        
        print("=== DEBUGGING LABEL EXTRACTION ===\n")
        
        # Look at the first few video cards
        video_containers = soup.select('.q-card')[:3]  # Just first 3
        
        for i, container in enumerate(video_containers, 1):
            print(f"=== VIDEO CARD {i} ===")
            
            # Check video ID extraction
            video_link = container.select_one('a[href*="/video/"]')
            if video_link:
                href = video_link.get('href', '')
                video_id = href.split('/')[-1] if href else 'No ID'
                print(f"Video ID: {video_id}")
            
            # Check all q-item__section elements
            sections = container.select('.q-item__section')
            print(f"Found {len(sections)} .q-item__section elements")
            
            for j, section in enumerate(sections):
                print(f"  Section {j+1}:")
                print(f"    Classes: {section.get('class', [])}")
                
                labels = section.select('.q-item__label')
                print(f"    Found {len(labels)} .q-item__label elements:")
                
                for k, label in enumerate(labels):
                    text = label.get_text().strip()
                    classes = label.get('class', [])
                    print(f"      Label {k+1}: '{text}' (classes: {classes})")
            
            # Check views and duration
            views_elem = container.select_one('.absolute-bottom-left .text-caption')
            if views_elem:
                print(f"Views: '{views_elem.get_text().strip()}'")
            else:
                print("Views: Not found")
            
            duration_elem = container.select_one('.absolute-bottom-right .text-caption')
            if duration_elem:
                print(f"Duration: '{duration_elem.get_text().strip()}'")
            else:
                print("Duration: Not found")
            
            print()
        
    except Exception as e:
        print(f"Error during debugging: {e}")
    finally:
        crawler.reset_webdriver()

if __name__ == "__main__":
    debug_label_extraction()