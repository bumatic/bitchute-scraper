import os
import time
import pandas as pd
import bitchute as bc
from datetime import datetime

def get_time():
    #dt = datetime.fromtimestamp(time.time())
    #t = str(dt.year)+'-'+str(dt.month)+'-'+str(dt.day)+' '+str(dt.hour)+'h'+str(dt.minute)+'m'+str(dt.second)+'s'
    t = str(time.time())
    return t

def check_dir(path):
    if not os.path.isdir(path):
        os.mkdir(path)

b = bc.Crawler()        

results_base = '/var/marcus/bitchute-scraper/bitchute-results'
check_dir(results_base)

popular_path = os.path.join(results_base, 'popular-videos')
check_dir(popular_path)
rv, tags = b.get_recommended_videos(type='popular')
t = get_time()
rv.to_csv(os.path.join(popular_path, t+'.csv'), sep='\t', index=None)

trending_videos_path = os.path.join(results_base, 'trending-videos')
trending_tags_path = os.path.join(results_base, 'trending-tags')
check_dir(trending_videos_path)
check_dir(trending_tags_path)
rv, tags = b.get_recommended_videos(type='trending')
t = get_time()
rv.to_csv(os.path.join(trending_videos_path, t+'.csv'), sep='\t', index=None)
tags.to_csv(os.path.join(trending_tags_path, t+'.csv'), sep='\t', index=None)

all_path = os.path.join(results_base, 'all-videos')
check_dir(all_path)
rv, tags = b.get_recommended_videos(type='all')
t = get_time()
rv.to_csv(os.path.join(all_path, t+'.csv'), sep='\t', index=None)

recommended_channels_path = os.path.join(results_base, 'recommended-channels')
check_dir(recommended_channels_path)
rc = b.get_recommended_channels(extended=False)
t = get_time()
rc.to_csv(os.path.join(recommended_channels_path, t+'.csv'), sep='\t', index=None)
