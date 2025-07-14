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