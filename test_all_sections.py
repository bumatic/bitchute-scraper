#!/usr/bin/env python3
"""
Test script to verify all video sections work correctly
"""

import bitchute as bc

def test_all_sections():
    """Test all available video sections"""
    
    print("=== TESTING ALL BITCHUTE SECTIONS ===\n")
    
    # Initialize crawler
    crawler = bc.Crawler(verbose=False)
    
    # Test cases: (method_name, description)
    test_cases = [
        # Trending with timeframes
        (lambda: crawler.get_trending_videos('day'), "Trending (Day)"),
        (lambda: crawler.get_trending_videos('week'), "Trending (Week)"), 
        (lambda: crawler.get_trending_videos('month'), "Trending (Month)"),
        
        # Other sections
        (crawler.get_popular_videos, "Popular/Fresh"),
        (crawler.get_all_videos, "All Videos"),
        (crawler.get_member_picked_videos, "Member Picked"),
        (crawler.get_shorts_videos, "Shorts"),
        
        # Test new method names
        (crawler.get_fresh_videos, "Fresh (alias)"),
        (crawler.get_trending_videos_week, "Trending Week (method)"),
        (crawler.get_trending_videos_month, "Trending Month (method)"),
    ]
    
    results = {}
    
    for method, description in test_cases:
        print(f"Testing: {description}...")
        
        try:
            videos = method()
            
            if isinstance(videos, tuple):  # Handle methods that return (videos, tags)
                videos = videos[0]
            
            count = len(videos) if not videos.empty else 0
            
            if count > 0:
                # Check if data is properly extracted
                has_titles = videos['title'].notna().sum()
                has_channels = videos['channel_name'].notna().sum()
                has_views = videos['view_count'].sum()
                
                print(f"  ✅ Success: {count} videos found")
                print(f"     - Titles: {has_titles}/{count}")
                print(f"     - Channels: {has_channels}/{count}")
                print(f"     - Total views: {has_views:,}")
                
                # Show first video as sample
                if not videos.empty:
                    first_video = videos.iloc[0]
                    print(f"     - Sample: '{first_video['title'][:50]}...' by {first_video['channel_name']}")
                
                results[description] = f"✅ {count} videos"
            else:
                print(f"  ⚠️  No videos found")
                results[description] = "⚠️ No videos"
                
        except Exception as e:
            print(f"  ❌ Error: {e}")
            results[description] = f"❌ Error: {str(e)[:50]}..."
        
        print()
    
    # Summary
    print("=== SUMMARY ===")
    for section, result in results.items():
        print(f"{section}: {result}")
    
    print(f"\nTotal sections tested: {len(test_cases)}")
    success_count = sum(1 for r in results.values() if r.startswith("✅"))
    print(f"Successful: {success_count}/{len(test_cases)}")

if __name__ == "__main__":
    test_all_sections()