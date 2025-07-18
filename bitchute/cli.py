"""
BitChute Scraper CLI
"""

import argparse
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

try:
    from .core import BitChuteAPI, SensitivityLevel, SortOrder
    from .exceptions import BitChuteAPIError, ValidationError
    from .utils import DataExporter, DataAnalyzer, ContentFilter
except ImportError:
    try:
        from bitchute.core import BitChuteAPI, SensitivityLevel, SortOrder
        from bitchute.exceptions import BitChuteAPIError, ValidationError
        from bitchute.utils import DataExporter, DataAnalyzer, ContentFilter
    except ImportError:
        print("Error: BitChute API module not found. Please install the package properly.")
        sys.exit(1)


class CLIFormatter:
    """Format CLI output with colors and emojis"""
    
    # ANSI color codes
    COLORS = {
        'red': '\033[91m',
        'green': '\033[92m',
        'yellow': '\033[93m',
        'blue': '\033[94m',
        'purple': '\033[95m',
        'cyan': '\033[96m',
        'white': '\033[97m',
        'bold': '\033[1m',
        'end': '\033[0m'
    }
    
    @classmethod
    def success(cls, message: str) -> str:
        """Format success message"""
        return f"{cls.COLORS['green']}✅ {message}{cls.COLORS['end']}"
    
    @classmethod
    def error(cls, message: str) -> str:
        """Format error message"""
        return f"{cls.COLORS['red']}❌ {message}{cls.COLORS['end']}"
    
    @classmethod
    def warning(cls, message: str) -> str:
        """Format warning message"""
        return f"{cls.COLORS['yellow']}⚠️  {message}{cls.COLORS['end']}"
    
    @classmethod
    def info(cls, message: str) -> str:
        """Format info message"""
        return f"{cls.COLORS['blue']}ℹ️  {message}{cls.COLORS['end']}"
    
    @classmethod
    def bold(cls, message: str) -> str:
        """Format bold message"""
        return f"{cls.COLORS['bold']}{message}{cls.COLORS['end']}"


class CLIResultPrinter:
    """Print CLI results in a formatted way"""
    
    @staticmethod
    def print_video_results(df, title: str):
        """Print video results summary"""
        if df.empty:
            print(CLIFormatter.warning(f"No {title.lower()} found."))
            return
        
        print(f"\n📊 {CLIFormatter.bold(title)}:")
        print(f"   Total: {len(df):,} videos")
        
        if 'view_count' in df.columns:
            total_views = df['view_count'].sum()
            avg_views = df['view_count'].mean()
            print(f"   Total views: {total_views:,}")
            print(f"   Average views: {avg_views:,.0f}")
        
        if 'duration' in df.columns:
            # Calculate total duration
            total_seconds = 0
            for duration in df['duration'].dropna():
                try:
                    parts = str(duration).split(':')
                    if len(parts) == 2:
                        total_seconds += int(parts[0]) * 60 + int(parts[1])
                    elif len(parts) == 3:
                        total_seconds += int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
                except:
                    pass
            
            if total_seconds > 0:
                total_hours = total_seconds // 3600
                total_minutes = (total_seconds % 3600) // 60
                print(f"   Total duration: {total_hours}h {total_minutes}m")
        
        print(f"\n🔝 {CLIFormatter.bold('Top Results')}:")
        for i, (_, row) in enumerate(df.head(5).iterrows(), 1):
            title_text = row['title'][:60] + '...' if len(str(row['title'])) > 60 else row['title']
            
            details = []
            if 'view_count' in row and row['view_count']:
                details.append(f"{row['view_count']:,} views")
            if 'channel_name' in row and row['channel_name']:
                details.append(f"by {row['channel_name']}")
            
            detail_text = f" ({', '.join(details)})" if details else ""
            print(f"   {i}. {title_text}{detail_text}")
    
    @staticmethod
    def print_channel_results(df, title: str):
        """Print channel results summary"""
        if df.empty:
            print(CLIFormatter.warning(f"No {title.lower()} found."))
            return
        
        print(f"\n📊 {CLIFormatter.bold(title)}:")
        print(f"   Total: {len(df):,} channels")
        
        if 'video_count' in df.columns:
            total_videos = df['video_count'].sum()
            print(f"   Total videos: {total_videos:,}")
        
        print(f"\n🔝 {CLIFormatter.bold('Top Channels')}:")
        for i, (_, row) in enumerate(df.head(5).iterrows(), 1):
            name = row['name'][:50] + '...' if len(str(row['name'])) > 50 else row['name']
            
            details = []
            if 'video_count' in row and row['video_count']:
                details.append(f"{row['video_count']} videos")
            if 'subscriber_count' in row and row['subscriber_count']:
                details.append(f"{row['subscriber_count']} subscribers")
            
            detail_text = f" ({', '.join(details)})" if details else ""
            print(f"   {i}. {name}{detail_text}")
    
    @staticmethod
    def print_hashtag_results(df, title: str):
        """Print hashtag results summary"""
        if df.empty:
            print(CLIFormatter.warning(f"No {title.lower()} found."))
            return
        
        print(f"\n📊 {CLIFormatter.bold(title)}:")
        print(f"   Total: {len(df):,} hashtags")
        
        print(f"\n🏷️  {CLIFormatter.bold('Top Hashtags')}:")
        for i, (_, row) in enumerate(df.head(10).iterrows(), 1):
            name = row['name'] if row['name'].startswith('#') else f"#{row['name']}"
            print(f"   {i}. {name}")
    
    @staticmethod
    def print_analysis_results(analysis: Dict[str, Any]):
        """Print data analysis results"""
        print(f"\n📈 {CLIFormatter.bold('Data Analysis')}:")
        
        if 'total_videos' in analysis:
            print(f"   Total videos analyzed: {analysis['total_videos']:,}")
        
        if 'views' in analysis:
            views = analysis['views']
            print(f"   📺 View Statistics:")
            print(f"      Total: {views['total']:,}")
            print(f"      Average: {views['average']:,.0f}")
            print(f"      Median: {views['median']:,.0f}")
            print(f"      Range: {views['min']:,} - {views['max']:,}")
        
        if 'duration' in analysis:
            duration = analysis['duration']
            print(f"   ⏱️  Duration Statistics:")
            print(f"      Average: {duration['average_minutes']:.1f} minutes")
        
        if 'top_channels' in analysis:
            channels = analysis['top_channels']
            print(f"   🏆 Top Channels:")
            for channel, count in list(channels.items())[:5]:
                print(f"      {channel}: {count} videos")
        
        if 'top_hashtags' in analysis:
            hashtags = analysis['top_hashtags']
            print(f"   🏷️  Top Hashtags:")
            for hashtag, count in list(hashtags.items())[:5]:
                print(f"      {hashtag}: {count} occurrences")


class CLIDataManager:
    """Manage CLI data operations"""
    
    @staticmethod
    def save_data(df, filename: str, formats: List[str], verbose: bool = False):
        """Save data to file(s) with CLI feedback"""
        if df.empty:
            print(CLIFormatter.warning("No data to save."))
            return
        
        exporter = DataExporter()
        
        try:
            exported_files = exporter.export_data(df, filename, formats)
            
            for format_name, filepath in exported_files.items():
                file_size = Path(filepath).stat().st_size
                size_mb = file_size / (1024 * 1024)
                print(CLIFormatter.success(
                    f"Saved {format_name.upper()}: {filepath} ({size_mb:.2f} MB)"
                ))
                
        except Exception as e:
            print(CLIFormatter.error(f"Failed to save data: {e}"))
    
    @staticmethod
    def analyze_data(df, show_analysis: bool = False):
        """Analyze data and optionally print results"""
        if df.empty or not show_analysis:
            return
        
        try:
            analyzer = DataAnalyzer()
            analysis = analyzer.analyze_videos(df)
            
            if 'error' not in analysis:
                CLIResultPrinter.print_analysis_results(analysis)
            else:
                print(CLIFormatter.warning(f"Analysis failed: {analysis['error']}"))
                
        except Exception as e:
            print(CLIFormatter.warning(f"Analysis failed: {e}"))


def create_argument_parser() -> argparse.ArgumentParser:
    """Create and configure argument parser"""
    parser = argparse.ArgumentParser(
        description='BitChute API Scraper - Extract videos, channels, and hashtags',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s trending --timeframe day --limit 50 --format csv,json
  %(prog)s search "climate change" --limit 100 --sort views
  %(prog)s popular --analyze --format xlsx
  %(prog)s video CLrgZP4RWyly --counts --media
  %(prog)s hashtags --limit 30

For more information, visit: https://github.com/bumatic/bitchute-scraper
        """
    )
    
    # Global options
    parser.add_argument('--verbose', '-v', action='store_true', 
                       help='Enable verbose output')
    parser.add_argument('--format', '-f', default='csv',
                       help='Output formats: csv,json,xlsx,parquet (comma-separated)')
    parser.add_argument('--analyze', action='store_true',
                       help='Show data analysis')
    parser.add_argument('--timeout', type=int, default=30,
                       help='Request timeout in seconds (default: 30)')
    
    # Subcommands
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Trending videos
    trending = subparsers.add_parser('trending', help='Get trending videos')
    trending.add_argument('--timeframe', '-t', choices=['day', 'week', 'month'], 
                         default='day', help='Trending timeframe (default: day)')
    trending.add_argument('--limit', '-l', type=int, default=20, 
                         help='Number of videos (default: 20)')
    trending.add_argument('--offset', type=int, default=0,
                         help='Pagination offset (default: 0)')
    
    # Popular videos
    popular = subparsers.add_parser('popular', help='Get popular videos')
    popular.add_argument('--limit', '-l', type=int, default=30,
                        help='Number of videos (default: 30)')
    popular.add_argument('--offset', type=int, default=0,
                        help='Pagination offset (default: 0)')
    
    # Recent videos
    recent = subparsers.add_parser('recent', help='Get recent videos')
    recent.add_argument('--limit', '-l', type=int, default=30,
                       help='Number of videos (default: 30)')
    recent.add_argument('--pages', '-p', type=int, default=1,
                   help='Number of pages to fetch (default: 1)')

def main():
    """Main entry point for the CLI application"""
    try:
        # Parse arguments
        parser = create_argument_parser()
        args = parser.parse_args()
        
        # Handle case where no command is provided
        if not args.command:
            parser.print_help()
            return 0
        
        # Initialize API client
        api = BitChuteAPI(
            verbose=args.verbose,
            timeout=args.timeout
        )
        
        # Initialize utilities
        data_manager = CLIDataManager()
        
        # Parse output formats
        formats = [fmt.strip() for fmt in args.format.split(',')]
        
        # Execute command
        try:
            if args.command == 'trending':
                df = api.get_trending_videos(
                    timeframe=args.timeframe,
                    limit=args.limit,
                    include_details=True
                )
                CLIResultPrinter.print_video_results(df, f"Trending Videos ({args.timeframe})")
                
                if not df.empty:
                    data_manager.save_data(df, f'trending_{args.timeframe}', formats, args.verbose)
                    data_manager.analyze_data(df, args.analyze)
            
            elif args.command == 'popular':
                df = api.get_popular_videos(
                    limit=args.limit,
                    include_details=True
                )
                CLIResultPrinter.print_video_results(df, "Popular Videos")
                
                if not df.empty:
                    data_manager.save_data(df, 'popular_videos', formats, args.verbose)
                    data_manager.analyze_data(df, args.analyze)
            
            elif args.command == 'recent':
                # Handle pages parameter for recent videos
                total_limit = args.limit * args.pages if hasattr(args, 'pages') else args.limit
                df = api.get_recent_videos(
                    limit=total_limit,
                    include_details=True
                )
                CLIResultPrinter.print_video_results(df, "Recent Videos")
                
                if not df.empty:
                    data_manager.save_data(df, 'recent_videos', formats, args.verbose)
                    data_manager.analyze_data(df, args.analyze)
            
            elif args.command == 'search':
                if hasattr(args, 'query'):
                    df = api.search_videos(
                        query=args.query,
                        limit=args.limit,
                        sensitivity=getattr(args, 'sensitivity', 'normal'),
                        sort=getattr(args, 'sort', 'new'),
                        include_details=True
                    )
                    CLIResultPrinter.print_video_results(df, f"Search Results for '{args.query}'")
                    
                    if not df.empty:
                        safe_query = "".join(c for c in args.query if c.isalnum() or c in (' ', '_', '-')).rstrip()
                        data_manager.save_data(df, f'search_{safe_query}', formats, args.verbose)
                        data_manager.analyze_data(df, args.analyze)
                else:
                    print(CLIFormatter.error("Search query is required"))
                    return 1
            
            elif args.command == 'channels':
                if hasattr(args, 'query'):
                    df = api.search_channels(
                        query=args.query,
                        limit=args.limit,
                        sensitivity=getattr(args, 'sensitivity', 'normal'),
                        include_details=True
                    )
                    CLIResultPrinter.print_channel_results(df, f"Channel Search Results for '{args.query}'")
                    
                    if not df.empty:
                        safe_query = "".join(c for c in args.query if c.isalnum() or c in (' ', '_', '-')).rstrip()
                        data_manager.save_data(df, f'channels_{safe_query}', formats, args.verbose)
                else:
                    print(CLIFormatter.error("Search query is required for channel search"))
                    return 1
            
            elif args.command == 'hashtags':
                df = api.get_trending_hashtags(limit=args.limit)
                CLIResultPrinter.print_hashtag_results(df, "Trending Hashtags")
                
                if not df.empty:
                    data_manager.save_data(df, 'trending_hashtags', formats, args.verbose)
            
            elif args.command == 'video':
                if hasattr(args, 'video_id'):
                    df = api.get_video_info(
                        video_id=args.video_id,
                        include_counts=getattr(args, 'counts', True),
                        include_media=getattr(args, 'media', False)
                    )
                    
                    if not df.empty:
                        print(f"\n📹 {CLIFormatter.bold('Video Details')}:")
                        video = df.iloc[0]
                        print(f"   Title: {video['title']}")
                        print(f"   Channel: {video['channel_name']}")
                        print(f"   Views: {video['view_count']:,}")
                        print(f"   Duration: {video['duration']}")
                        print(f"   Upload Date: {video['upload_date']}")
                        
                        if video['like_count'] > 0 or video['dislike_count'] > 0:
                            total_reactions = video['like_count'] + video['dislike_count']
                            like_ratio = video['like_count'] / total_reactions if total_reactions > 0 else 0
                            print(f"   Likes: {video['like_count']:,} ({like_ratio:.1%})")
                            print(f"   Dislikes: {video['dislike_count']:,}")
                        
                        data_manager.save_data(df, f'video_{args.video_id}', formats, args.verbose)
                    else:
                        print(CLIFormatter.error(f"Video not found: {args.video_id}"))
                        return 1
                else:
                    print(CLIFormatter.error("Video ID is required"))
                    return 1
            
            else:
                print(CLIFormatter.error(f"Unknown command: {args.command}"))
                parser.print_help()
                return 1
                
        except BitChuteAPIError as e:
            print(CLIFormatter.error(f"API Error: {e}"))
            return 1
        except ValidationError as e:
            print(CLIFormatter.error(f"Validation Error: {e}"))
            return 1
        except KeyboardInterrupt:
            print(CLIFormatter.warning("\nOperation cancelled by user"))
            return 1
        except Exception as e:
            print(CLIFormatter.error(f"Unexpected error: {e}"))
            if args.verbose:
                import traceback
                traceback.print_exc()
            return 1
        
        print(CLIFormatter.success("Operation completed successfully!"))
        return 0
        
    except Exception as e:
        print(CLIFormatter.error(f"CLI Error: {e}"))
        return 1


if __name__ == "__main__":
    exit(main())