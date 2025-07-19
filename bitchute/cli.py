"""
BitChute Scraper Command Line Interface

Provides a comprehensive command-line interface for BitChute data collection
with support for all major platform features including trending videos,
search functionality, data export, and analysis.

This module implements a full-featured CLI with colored output, progress tracking,
and multiple export formats for easy integration with data workflows.

Example:
    Basic usage:
        $ bitchute trending --timeframe day --limit 50 --format csv
        $ bitchute search "climate change" --limit 100 --sort views
        $ bitchute popular --analyze --format xlsx

    Advanced usage:
        $ bitchute hashtags --limit 30
        $ bitchute video CLrgZP4RWyly --counts --media
        $ bitchute channels "news" --limit 20 --sensitivity normal
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
    """Formats CLI output with colors and status indicators.
    
    Provides consistent formatting for CLI messages including success,
    error, warning, and informational messages with ANSI color codes.
    
    Attributes:
        COLORS: Dictionary mapping color names to ANSI escape codes.
    """
    
    # ANSI color codes for terminal output
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
        """Format success message with green color and checkmark.
        
        Args:
            message: The success message to format.
            
        Returns:
            str: Formatted success message with color codes.
            
        Example:
            >>> print(CLIFormatter.success("Operation completed"))
        """
        return f"{cls.COLORS['green']}✅ {message}{cls.COLORS['end']}"
    
    @classmethod
    def error(cls, message: str) -> str:
        """Format error message with red color and error icon.
        
        Args:
            message: The error message to format.
            
        Returns:
            str: Formatted error message with color codes.
            
        Example:
            >>> print(CLIFormatter.error("Failed to connect"))
        """
        return f"{cls.COLORS['red']}❌ {message}{cls.COLORS['end']}"
    
    @classmethod
    def warning(cls, message: str) -> str:
        """Format warning message with yellow color and warning icon.
        
        Args:
            message: The warning message to format.
            
        Returns:
            str: Formatted warning message with color codes.
            
        Example:
            >>> print(CLIFormatter.warning("Rate limit approaching"))
        """
        return f"{cls.COLORS['yellow']}⚠️  {message}{cls.COLORS['end']}"
    
    @classmethod
    def info(cls, message: str) -> str:
        """Format informational message with blue color and info icon.
        
        Args:
            message: The info message to format.
            
        Returns:
            str: Formatted info message with color codes.
            
        Example:
            >>> print(CLIFormatter.info("Processing 100 videos"))
        """
        return f"{cls.COLORS['blue']}ℹ️  {message}{cls.COLORS['end']}"
    
    @classmethod
    def bold(cls, message: str) -> str:
        """Format message with bold text styling.
        
        Args:
            message: The message to format in bold.
            
        Returns:
            str: Bold formatted message.
            
        Example:
            >>> print(CLIFormatter.bold("Important Notice"))
        """
        return f"{cls.COLORS['bold']}{message}{cls.COLORS['end']}"


class CLIResultPrinter:
    """Prints CLI results in formatted tables and summaries.
    
    Provides consistent result presentation for different data types
    including videos, channels, and hashtags with statistics and
    top results display.
    """
    
    @staticmethod
    def print_video_results(df, title: str):
        """Print formatted video results with statistics.
        
        Displays video collection results including total count, view statistics,
        duration information, and top results in a formatted layout.
        
        Args:
            df: DataFrame containing video results.
            title: Display title for the results section.
            
        Example:
            >>> CLIResultPrinter.print_video_results(trending_df, "Trending Videos")
        """
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
            # Calculate total duration from duration strings
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
        """Print formatted channel results with statistics.
        
        Displays channel collection results including total count, video statistics,
        subscriber information, and top channels in a formatted layout.
        
        Args:
            df: DataFrame containing channel results.
            title: Display title for the results section.
            
        Example:
            >>> CLIResultPrinter.print_channel_results(channels_df, "Search Results")
        """
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
        """Print formatted hashtag results with ranking.
        
        Displays hashtag collection results including total count and
        top trending hashtags in ranked order.
        
        Args:
            df: DataFrame containing hashtag results.
            title: Display title for the results section.
            
        Example:
            >>> CLIResultPrinter.print_hashtag_results(hashtags_df, "Trending Hashtags")
        """
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
        """Print data analysis results with statistics.
        
        Displays comprehensive analysis results including view statistics,
        duration analysis, top channels, and hashtag information.
        
        Args:
            analysis: Dictionary containing analysis results with various metrics.
            
        Example:
            >>> analysis = {'total_videos': 100, 'views': {'total': 50000}}
            >>> CLIResultPrinter.print_analysis_results(analysis)
        """
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
    """Manages CLI data operations including saving and analysis.
    
    Handles data export operations and analysis with user feedback
    for command-line interface operations.
    """
    
    @staticmethod
    def save_data(df, filename: str, formats: List[str], verbose: bool = False):
        """Save DataFrame to specified formats with CLI feedback.
        
        Exports data to multiple file formats and provides user feedback
        on file locations and sizes.
        
        Args:
            df: DataFrame containing data to export.
            filename: Base filename without extension.
            formats: List of format strings (csv, json, xlsx, parquet).
            verbose: Whether to show detailed output.
            
        Example:
            >>> CLIDataManager.save_data(videos_df, "trending", ["csv", "json"])
        """
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
        """Analyze DataFrame and optionally print results.
        
        Performs comprehensive data analysis and displays results
        if analysis is requested by the user.
        
        Args:
            df: DataFrame containing data to analyze.
            show_analysis: Whether to display analysis results.
            
        Example:
            >>> CLIDataManager.analyze_data(videos_df, show_analysis=True)
        """
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
    """Create and configure the command-line argument parser.
    
    Sets up the complete argument parser with all subcommands, options,
    and help text for the BitChute CLI interface.
    
    Returns:
        argparse.ArgumentParser: Configured argument parser with all subcommands.
        
    Example:
        >>> parser = create_argument_parser()
        >>> args = parser.parse_args(['trending', '--limit', '50'])
    """
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
    
    # Trending videos command
    trending = subparsers.add_parser('trending', help='Get trending videos')
    trending.add_argument('--timeframe', '-t', choices=['day', 'week', 'month'], 
                         default='day', help='Trending timeframe (default: day)')
    trending.add_argument('--limit', '-l', type=int, default=20, 
                         help='Number of videos (default: 20)')
    trending.add_argument('--offset', type=int, default=0,
                         help='Pagination offset (default: 0)')
    
    # Popular videos command
    popular = subparsers.add_parser('popular', help='Get popular videos')
    popular.add_argument('--limit', '-l', type=int, default=30,
                        help='Number of videos (default: 30)')
    popular.add_argument('--offset', type=int, default=0,
                        help='Pagination offset (default: 0)')
    
    # Recent videos command
    recent = subparsers.add_parser('recent', help='Get recent videos')
    recent.add_argument('--limit', '-l', type=int, default=30,
                       help='Number of videos (default: 30)')
    recent.add_argument('--pages', '-p', type=int, default=1,
                   help='Number of pages to fetch (default: 1)')

    # Search videos command
    search = subparsers.add_parser('search', help='Search videos')
    search.add_argument('query', help='Search query string')
    search.add_argument('--limit', '-l', type=int, default=50,
                       help='Number of results (default: 50)')
    search.add_argument('--sensitivity', choices=['normal', 'nsfw', 'nsfl'],
                       default='normal', help='Content sensitivity (default: normal)')
    search.add_argument('--sort', choices=['new', 'old', 'views'],
                       default='new', help='Sort order (default: new)')
    
    # Search channels command
    channels = subparsers.add_parser('channels', help='Search channels')
    channels.add_argument('query', help='Search query string')
    channels.add_argument('--limit', '-l', type=int, default=50,
                         help='Number of results (default: 50)')
    channels.add_argument('--sensitivity', choices=['normal', 'nsfw', 'nsfl'],
                         default='normal', help='Content sensitivity (default: normal)')
    
    # Trending hashtags command
    hashtags = subparsers.add_parser('hashtags', help='Get trending hashtags')
    hashtags.add_argument('--limit', '-l', type=int, default=50,
                         help='Number of hashtags (default: 50)')
    
    # Individual video command
    video = subparsers.add_parser('video', help='Get video details')
    video.add_argument('video_id', help='Video ID to retrieve')
    video.add_argument('--counts', action='store_true',
                      help='Include like/dislike counts')
    video.add_argument('--media', action='store_true',
                      help='Include media URL')
    
    # Individual channel command
    channel = subparsers.add_parser('channel', help='Get channel details')
    channel.add_argument('channel_id', help='Channel ID to retrieve')
    
    # Channel videos command
    channel_videos = subparsers.add_parser('channel-videos', help='Get videos from channel')
    channel_videos.add_argument('channel_id', help='Channel ID')
    channel_videos.add_argument('--limit', '-l', type=int, default=50,
                               help='Number of videos (default: 50)')
    channel_videos.add_argument('--order', choices=['latest', 'popular', 'oldest'],
                               default='latest', help='Video order (default: latest)')
    
    return parser


def main():
    """Main entry point for the CLI application.
    
    Handles command-line argument parsing, API client initialization,
    command execution, and result presentation with error handling.
    
    Returns:
        int: Exit code (0 for success, 1 for error).
        
    Example:
        Command line usage:
            $ bitchute trending --limit 50
            $ python -m bitchute.cli search "bitcoin"
    """
    try:
        # Parse command-line arguments
        parser = create_argument_parser()
        args = parser.parse_args()
        
        # Handle case where no command is provided
        if not args.command:
            parser.print_help()
            return 0
        
        # Initialize API client with user settings
        api = BitChuteAPI(
            verbose=args.verbose,
            timeout=args.timeout
        )
        
        # Initialize data management utilities
        data_manager = CLIDataManager()
        
        # Parse output formats from comma-separated string
        formats = [fmt.strip() for fmt in args.format.split(',')]
        
        # Execute the requested command
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
                # Handle multiple pages for recent videos
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
                        # Create safe filename from query
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
                        # Create safe filename from query
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
            
            elif args.command == 'channel':
                if hasattr(args, 'channel_id'):
                    df = api.get_channel_info(channel_id=args.channel_id)
                    
                    if not df.empty:
                        print(f"\n📺 {CLIFormatter.bold('Channel Details')}:")
                        channel = df.iloc[0]
                        print(f"   Name: {channel['name']}")
                        print(f"   Videos: {channel['video_count']:,}")
                        print(f"   Subscribers: {channel['subscriber_count']}")
                        print(f"   Total Views: {channel['view_count']:,}")
                        print(f"   Created: {channel['created_date']}")
                        
                        data_manager.save_data(df, f'channel_{args.channel_id}', formats, args.verbose)
                    else:
                        print(CLIFormatter.error(f"Channel not found: {args.channel_id}"))
                        return 1
                else:
                    print(CLIFormatter.error("Channel ID is required"))
                    return 1
            
            elif args.command == 'channel-videos':
                if hasattr(args, 'channel_id'):
                    df = api.get_channel_videos(
                        channel_id=args.channel_id,
                        limit=args.limit,
                        order_by=getattr(args, 'order', 'latest'),
                        include_details=True
                    )
                    CLIResultPrinter.print_video_results(df, f"Videos from Channel")
                    
                    if not df.empty:
                        data_manager.save_data(df, f'channel_videos_{args.channel_id}', formats, args.verbose)
                        data_manager.analyze_data(df, args.analyze)
                else:
                    print(CLIFormatter.error("Channel ID is required"))
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
