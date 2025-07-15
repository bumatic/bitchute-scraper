def benchmark_details_fetching():
    """Benchmark the performance improvement"""
    import time
    
    api = BitChuteAPI(verbose=True)
    
    print("Benchmarking video details fetching...")
    print("=" * 50)
    
    # Test with 20 videos
    test_limit = 20
    
    # Test 1: Without details
    start = time.time()
    videos_no_details = api.get_trending_videos('day', limit=test_limit, include_details=False)
    time_no_details = time.time() - start
    
    print(f"Without details: {time_no_details:.2f} seconds ({len(videos_no_details)} videos)")
    
    # Test 2: With details (optimized)
    start = time.time()
    videos_with_details = api.get_trending_videos_optimized('day', limit=test_limit, include_details=True)
    time_with_details = time.time() - start
    
    print(f"With details (optimized): {time_with_details:.2f} seconds ({len(videos_with_details)} videos)")
    
    # Calculate improvement
    if time_no_details > 0:
        overhead = ((time_with_details - time_no_details) / time_no_details) * 100
        print(f"Overhead for details: {overhead:.1f}%")
    
    print("\nSample video with details:")
    if not videos_with_details.empty:
        sample = videos_with_details.iloc[0]
        print(f"Title: {sample['title']}")
        print(f"Views: {sample['view_count']:,}")
        print(f"Likes: {sample['like_count']:,}")
        print(f"Dislikes: {sample['dislike_count']:,}")


if __name__ == "__main__":
    benchmark_details_fetching()