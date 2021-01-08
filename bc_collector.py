import os
import time
import pandas as pd
import bitchute as bc
from datetime import datetime

def get_time():
    t = str(int(datetime.utcnow().timestamp()))
    return t

def check_dir(path):
    if not os.path.isdir(path):
        os.mkdir(path)

local_test = False

if local_test:
	b = bc.Crawler(headless=False)
	results_base = 'bitchute-results'
else:
	b = bc.Crawler()        
	results_base = '/var/marcus/bitchute-scraper/bitchute-results'

check_dir(results_base)

if local_test:
	print('GET POPULAR')
popular_path = os.path.join(results_base, 'popular-videos')
check_dir(popular_path)
rv, tags = b.get_recommended_videos(type='popular')
t = get_time()
rv.to_csv(os.path.join(popular_path, t+'.csv'), sep='\t', index=None)

if local_test:
	print('GET TRENDING')
trending_videos_path = os.path.join(results_base, 'trending-videos')
trending_tags_path = os.path.join(results_base, 'trending-tags')
check_dir(trending_videos_path)
check_dir(trending_tags_path)
rv, tags = b.get_recommended_videos(type='trending')
t = get_time()
rv.to_csv(os.path.join(trending_videos_path, t+'.csv'), sep='\t', index=None)
tags.to_csv(os.path.join(trending_tags_path, t+'.csv'), sep='\t', index=None)

if local_test:
	print('GET ALL VIDEOS')
all_path = os.path.join(results_base, 'all-videos')
check_dir(all_path)
rv, tags = b.get_recommended_videos(type='all')
t = get_time()
rv.to_csv(os.path.join(all_path, t+'.csv'), sep='\t', index=None)

if local_test:
	print('GET RECOMMENDED CHANNELS')
recommended_channels_path = os.path.join(results_base, 'recommended-channels')
check_dir(recommended_channels_path)
rc = b.get_recommended_channels(extended=False)
t = get_time()
rc.to_csv(os.path.join(recommended_channels_path, t+'.csv'), sep='\t', index=None)

b.reset_webdriver()