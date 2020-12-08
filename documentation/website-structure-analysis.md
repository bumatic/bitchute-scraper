# Bitcute 

## Homepage

The Bitchute homepage contains video listings of popular, trending and all videos as well as a carousel of recommended channels. The trending homepage also contains trending tags.

### Recommended Channels Carousel

```html
<div id="carousel" class="row overflow-hidden mt5">
    <div class="hidden-md hidden-lg hidden-xl">
        <div class="col-md-3 col-sm-6">
            <div class="channel-card">
                <a href="/channel/hourofthetruth/" class="spa">
                    <img class="img-responsive lazyload hidden-xs hidden-sm" src="/static/v128/images/loading_medium.png" data-src="https://static-3.bitchute.com/live/channel_images/YJv5vljU41Mh/0cUsbUtgJ6HyxITj02J6PNxq_medium.jpg" onerror="this.src='/static/v128/images/blank_medium.png';this.onerror='';" alt="channel image">
                    <img class="img-responsive lazyload hidden-md hidden-lg" src="/static/v128/images/loading_large.png" data-src="https://static-3.bitchute.com/live/channel_images/YJv5vljU41Mh/0cUsbUtgJ6HyxITj02J6PNxq_large.jpg" onerror="this.src='/static/v128/images/blank_large.png';this.onerror='';" alt="channel image">
                    <img class="img-responsive play-overlay" src="/static/v128/images/play-button.png" alt="play">
                    <div class="channel-card-bottom-shadow"></div>
                    <div class="channel-card-title">HourOfTheTruth</div>
                </a>
            </div>
        </div>
        <div class="col-md-3 col-sm-6">
            <div class="channel-card">
                <a href="/channel/truthvideos1984/" class="spa">
                    <img class="img-responsive lazyload hidden-xs hidden-sm" src="/static/v128/images/loading_medium.png" data-src="https://static-3.bitchute.com/live/channel_images/Whuei2DGmgBn/jRvRo7l17RjRV4qHZapxGUXJ_medium.jpg" onerror="this.src='/static/v128/images/blank_medium.png';this.onerror='';" alt="channel image">
                    <img class="img-responsive lazyload hidden-md hidden-lg" src="/static/v128/images/loading_large.png" data-src="https://static-3.bitchute.com/live/channel_images/Whuei2DGmgBn/jRvRo7l17RjRV4qHZapxGUXJ_large.jpg" onerror="this.src='/static/v128/images/blank_large.png';this.onerror='';" alt="channel image">
                    <img class="img-responsive play-overlay" src="/static/v128/images/play-button.png" alt="play">
                    <div class="channel-card-bottom-shadow"></div>
                    <div class="channel-card-title">TruthVideos1984</div>
                </a>                
            </div>
        </div>
        <div class="col-md-3 col-sm-6">
            <div class="channel-card">
                ...
            </div>
        </div>
        <div class="col-md-3 col-sm-6">
            <div class="channel-card">
                ...
            </div>
        </div>
    </div>
    
    <div id="channel-list" class="carousel slide hidden-xs hidden-sm" data-ride="carousel">
        <ol class="carousel-indicators">
            <li data-target="#channel-list" data-slide-to="0" class="active"></li>
            <li data-target="#channel-list" data-slide-to="1"></li>
            <li data-target="#channel-list" data-slide-to="2"></li>
            <li data-target="#channel-list" data-slide-to="3"></li>
            <li data-target="#channel-list" data-slide-to="4"></li>
        </ol>
        <div class="carousel-inner">
            <div class="item active">
                <div class="col-md-3 col-sm-6">
                    <div class="channel-card">
                        <a href="/channel/hourofthetruth/" class="spa">
                            <img class="img-responsive lazyload hidden-xs hidden-sm" src="/static/v128/images/loading_medium.png" data-src="https://static-3.bitchute.com/live/channel_images/YJv5vljU41Mh/0cUsbUtgJ6HyxITj02J6PNxq_medium.jpg" onerror="this.src='/static/v128/images/blank_medium.png';this.onerror='';" alt="channel image">
                            <img class="img-responsive lazyload hidden-md hidden-lg" src="/static/v128/images/loading_large.png" data-src="https://static-3.bitchute.com/live/channel_images/YJv5vljU41Mh/0cUsbUtgJ6HyxITj02J6PNxq_large.jpg" onerror="this.src='/static/v128/images/blank_large.png';this.onerror='';" alt="channel image">
                            <img class="img-responsive play-overlay" src="/static/v128/images/play-button.png" alt="play">
                            <div class="channel-card-bottom-shadow"></div>
                            <div class="channel-card-title">HourOfTheTruth</div>
                        </a>
                    </div>
                </div>
                <div class="col-md-3 col-sm-6">
                    <div class="channel-card">
                        ...               
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>
```


### Video Entity HTML Markup

```html
<div class="video-card">
    <a href="/video/gTGBNp1q7ghp/" class="spa">
        <div class="video-card-image">
            <img class="img-responsive lazyload" src="/static/v128/images/loading_320x180.png" data-src="https://static-3.bitchute.com/live/cover_images/gzFCj8AuSWgp/KYKAH3yP8I8L1oTWectzjPmi_320x180.jpg" onerror="this.src='/static/v128/images/blank_320x180.png';this.onerror='';" alt="video image">
            <img class="img-responsive play-overlay" src="/static/v128/images/play-button.png" alt="play">
            <span class="video-views"><i class="far fa-eye"></i> 200</span>
            <span class="video-duration">40:09</span>
        </div>
    </a>
    <span class="action-button playlist-watch-later" data-video="gTGBNp1q7ghp" data-toggle="tooltip" data-placement="bottom" title="Watch later">
        <span class="active fa-layers"><i class="fal fa-square"></i><i class="fas fa-clock" data-fa-transform="shrink-6"></i></span>
        <span class="fa-layers hidden"><i class="fal fa-square"></i><i class="fas fa-check" data-fa-transform="shrink-6"></i></span>
    </span>
    <div class="video-card-text">
        <p class="video-card-title"><a href="/video/gTGBNp1q7ghp/" class="spa">The VIRUS EXPOSED! - HOW We Got Here &amp; WHY We Need To FIGHT NOW! (FULL 2020 Documentary)</a></p>
        <p class="video-card-channel"><a href="/channel/worldalternativemedia/" class="spa">World Alternative Media</a></p>
        <p class="video-card-published">6 minutes ago</p>
    </div>
    <span class="video-card-id hidden">gTGBNp1q7ghp</span>
</div>
```


### The trending page does not just contain a video list, but also trending tags

```html
<div class="sidebar tags">
    <h1 class="sidebar-heading">Trending Tags</h1>
    <div id="hashtag-tab-content" class="tab-content">
        <div class="tab-pane active">
            <ul class="list-inline list-unstyled">
                <li><a href="/hashtag/trump">#trump</a></li>
                <li><a href="/hashtag/nwo">#nwo</a></li>
                <li><a href="/hashtag/covid">#covid</a></li>
                <li><a href="/hashtag/plandemic">#plandemic</a></li>
                <li><a href="/hashtag/voterfraud">#voterfraud</a></li>
                <li><a href="/hashtag/maga">#maga</a></li>
                <li><a href="/hashtag/music">#music</a></li>
                <li><a href="/hashtag/covid19">#covid19</a></li>
                <li><a href="/hashtag/comedy">#comedy</a></li>
                <li><a href="/hashtag/gaming">#gaming</a></li>
                <li><a href="/hashtag/coronavirus">#coronavirus</a></li>
                <li><a href="/hashtag/qanon">#qanon</a></li>
                <li><a href="/hashtag/election2020">#election2020</a></li>
                <li><a href="/hashtag/covid-19">#covid-19</a></li>
                <li><a href="/hashtag/biden">#biden</a></li>
                <li><a href="/hashtag/anime">#anime</a></li>
                <li><a href="/hashtag/election">#election</a></li>
                <li><a href="/hashtag/letsplay">#letsplay</a></li>
                <li><a href="/hashtag/jesus">#jesus</a></li>
                <li><a href="/hashtag/flatearth">#flatearth</a></li>
                <li><a href="/hashtag/uk">#uk</a></li>
                <li><a href="/hashtag/freespeech">#freespeech</a></li>
                <li><a href="/hashtag/americafirst">#americafirst</a></li>
                <li><a href="/hashtag/videogames">#videogames</a></li>
                <li><a href="/hashtag/thanksgiving">#thanksgiving</a></li>
                <li><a href="/hashtag/vaccine">#vaccine</a></li>
                <li><a href="/hashtag/freedom">#freedom</a></li>
                <li><a href="/hashtag/censorship">#censorship</a></li>
                <li><a href="/hashtag/deepstate">#deepstate</a></li>
                <li><a href="/hashtag/france">#france</a></li>
                <li><a href="/hashtag/freemasons">#freemasons</a></li>
                <li><a href="/hashtag/nintendo">#nintendo</a></li>
                <li><a href="/hashtag/wwg1wga">#wwg1wga</a></li>
                <li><a href="/hashtag/blm">#blm</a></li>
                <li><a href="/hashtag/joebiden">#joebiden</a></li>
                <li><a href="/hashtag/antifa">#antifa</a></li>
                <li><a href="/hashtag/infowars">#infowars</a></li>
                <li><a href="/hashtag/iran">#iran</a></li>
                <li><a href="/hashtag/youtube">#youtube</a></li>
                <li><a href="/hashtag/london">#london</a></li>
            </ul>
        </div>
    </div>
</div>
```


## Single Video Page

Data Points:

- title
- id (link)
- creator
- creator subscribers count
- Category
- Sensitivity 
- view count
- like count
- dislike count

```html
<div id="page-bar" class="row">
    <div class="col-xs-12">
        <h1 id="video-title" class="page-title">Must Watch: Prof Dolores Cahill Speaks at Freedom Rally in Dublin</h1>
    </div>
</div>
<div id="page-detail" class="row">
    <div class="col-xs-12">
        <div class="tab-scroll-outer">
            <div class="tab-scroll-inner">
                <ul class="nav nav-tabs nav-tabs-list">
                    <li class="active"><a data-toggle="tab" href="#video-watch">Watch</a></li>
                </ul>
            </div>
        <div class="tab-scroll-left"><i class="fas fa-chevron-left"></i></div>
        <div class="tab-scroll-right"><i class="fas fa-chevron-right"></i></div>
    </div>
    <div class="tab-content">
        <div class="tab-pane active" id="video-watch">
        <div class="row">
            <div class="col-xs-12 col-sm-8 col-md-9 video-container">
                <div class="row">
                    <div class="col-xs-12">
                        <div class="wrapper">
                            <video id="player" ratio="16x9" width="100%" poster="https://static-3.bitchute.com/live/cover_images/hybM74uIHJKf/DR1QuEZecY39_640x360.jpg" onplay="$('#loader-container').fadeOut('slow');" controls>
                                <source src="https://seed305.bitchute.com/hybM74uIHJKf/DR1QuEZecY39.mp4" type="video/mp4" />
                            </video>
                    <div id="autoplay-details" class="hidden">
                    <div class="title">Next video playing soon</div>
                    <div class="timer"><div class="spinner"><div class="pie"></div></div><div class="filler pie"></div><div class="mask"></div></div>
                    <div class="dismiss">Click to cancel</div>
                </div>
                <div id="autoplay-paused" class="hidden">
                    <div class="title">Autoplay has been paused</div>
                    <div class="icon"><i class="fas fa-play"></i></div>
                    <div class="continue">Click to watch next video</div>
                </div>
            </div>
        </div>
    </div>
    <div class="row">
        <div class="col-xs-12">
            <div class="video-information">
                <div class="row">
                    <div class="col-sm-6 col-xs-12">
                        <div class="video-statistics">
                            <i class="far fa-eye fa-fw"></i><span id="video-view-count"><i class="fas fa-spinner fa-pulse fa-fw"></i></span>
                            <a id="video-like" class="video-like" onclick="authShowModal('/video/DR1QuEZecY39/');" data-toggle="tooltip" data-placement="bottom" title="I like this">
                                <i class="action-icon far fa-thumbs-up fa-fw"></i>
                                <span id="video-like-count"><i class="fas fa-spinner fa-pulse fa-fw"></i></span>
                            </a>
                            <a id="video-dislike" class="video-dislike" onclick="authShowModal('/video/DR1QuEZecY39/');" data-toggle="tooltip" data-placement="bottom" title="I dislike this">
                                <i class="action-icon far fa-thumbs-down fa-fw"></i>
                                <span id="video-dislike-count"><i class="fas fa-spinner fa-pulse fa-fw"></i></span>
                            </a>
                        </div>
                    </div>
                    <div class="col-sm-6 col-xs-12">
                        <div class="video-actions">
                            <div class="action-list text-right">
                                <a onclick="authShowModal('/video/DR1QuEZecY39/');" data-toggle="tooltip" data-placement="bottom" title="Favorites"><i class="action-icon fas fa-star fa-fw"></i></a>
                                <a onclick="authShowModal('/video/DR1QuEZecY39/');" data-toggle="tooltip" data-placement="bottom" title="Watch Later"><i class="action-icon fas fa-clock fa-fw"></i></a>
                                <a onclick="authShowModal('/video/DR1QuEZecY39/');" data-toggle="tooltip" data-placement="bottom" title="Add to Playlist"><i class="action-icon fas fa-list fa-fw"></i></a>
                                <a onclick="authShowModal('/video/DR1QuEZecY39/');" data-toggle="tooltip" data-placement="bottom" title="Flag Video"><i class="action-icon fas fa-flag fa-fw"></i></a>
                                <a class="sharing-drop" data-toggle="tooltip" data-placement="bottom" title="Share"><i class="action-icon fas fa-share-alt fa-fw"></i></a>
                            </div>
                            <div class="sharing-bar text-right">
                                <a href="https://www.facebook.com/sharer/sharer.php?u=https%3A//www.bitchute.com/video/DR1QuEZecY39/" target="_blank" rel="noopener noreferrer" aria-label="Share on Facebook" data-toggle="tooltip" data-placement="bottom" title="Share on Facebook"><i class="action-icon fab fa-facebook fa-fw"></i></a>
                                <a href="https://twitter.com/share?text=Must%20Watch%3A%20Prof%20Dolores%20Cahill%20Speaks%20at%20Freedom%20Rally%20in%20Dublin&url=https%3A//www.bitchute.com/video/DR1QuEZecY39/&via=BitChute" target="_blank" rel="noopener noreferrer" aria-label="Share on Twitter" data-toggle="tooltip" data-placement="bottom" title="Share on Twitter"><i class="action-icon fab fa-twitter fa-fw"></i></a>
                                <a href="https://reddit.com/submit?url=https%3A//www.bitchute.com/video/DR1QuEZecY39/&title=Must%20Watch%3A%20Prof%20Dolores%20Cahill%20Speaks%20at%20Freedom%20Rally%20in%20Dublin" target="_blank" rel="noopener noreferrer" aria-label="Share on Reddit" data-toggle="tooltip" data-placement="bottom" title="Share on Reddit"><i class="action-icon fab fa-reddit fa-fw"></i></a>
                                <a href="https://voat.co/submit?linkpost=true&url=https%3A//www.bitchute.com/video/DR1QuEZecY39/&title=Must%20Watch%3A%20Prof%20Dolores%20Cahill%20Speaks%20at%20Freedom%20Rally%20in%20Dublin" target="_blank" rel="noopener noreferrer" aria-label="Share on Voat" data-toggle="tooltip" data-placement="bottom" title="Share on Voat"><i class="action-icon fas fa-play fa-fw fa-rotate-270"></i></a>
                                <a href="javascript:showShareModal();" aria-label="Share via Clipboard" data-toggle="tooltip" data-placement="bottom" title="Share via Clipboard"><i class="action-icon fas fa-clipboard fa-fw"></i></a>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    <div class="row">
        <div class="col-xs-12">
            <div class="video-publish-date">
                First published at 18:42 UTC on November 29th, 2020.
            </div>
            <span id="video-hashtags" class="tags">
                <ul class="list-inline list-unstyled">
                </ul>
            </span>
            <div class="channel-banner">
                <div class="backdrop"></div>
                <div class="image-container">
                    <a href="/channel/computingforever/" class="spa">
                        <img class="image lazyload" src="/static/v128/images/loading_small.png" data-src="https://static-3.bitchute.com/live/channel_images/hybM74uIHJKf/tURpVYQXDpchaTe1ayiBv3LV_small.jpg" onerror="this.src='/static/v128/images/blank_small.png';this.onerror='';" alt="channel image">
                    </a>
                </div>
                <div class="details">
<p class="name"><a href="/channel/computingforever/" class="spa">Computing Forever</a></p>
<p class="owner"><a href="/profile/ldxZ8WGbPGJJ/" class="spa">Computing Forever</a></p>
<p class="subscribers"><i class="fas fa-users fa-fw"></i> <span id="subscriber_count"><i class="fas fa-spinner fa-pulse"></i></span> subscribers</p>
</div>
<div class="actions">
<div class="subscriber margins">
<span class="creator-monetization" data-toggle="tooltip" data-placement="bottom" title="Tip or Pledge">
<i class="action-icon fas fa-usd-circle fa-fw fa-lg remove faa-vertical animated hidden" id="on-usd-id" data-fa-transform="down-1"></i>
<i class="action-icon fas fa-usd-circle fa-fw fa-lg" id="off-usd-id" data-fa-transform="down-1"></i>
</span>
<button class="btn btn-danger" onclick="authShowModal('');">Subscribe</button>
<span class="notify-button" onclick="authShowModal('');"><i class="fas fa-bell-slash fa-fw fa-lg"></i></span>
</div>
</div>
</div>
<div id="video-description" class="video-detail-text">
<div class="teaser"><p>This was recorded at the Irish Freedom Party&#x27;s Freedom Rally at Custom House Quay, Dublin on Saturday 28th of November 2020.</p></div>
<span class="more hidden"><i class="fal fa-plus-square fa-fw" data-fa-transform="up-0.5"></i> MORE</span>
<div class="full hidden"><p>This was recorded at the Irish Freedom Party&#x27;s Freedom Rally at Custom House Quay, Dublin on Saturday 28th of November 2020.</p></div>
<span class="less hidden"><i class="fal fa-minus-square fa-fw" data-fa-transform="up-0.5"></i> LESS</span>
</div>
<table class="video-detail-list">
<tr><td>Category</td><td><a href="/category/news/" class="spa">News &amp; Politics</a></td></tr>
<tr><td>Sensitivity</td><td><a href="https://support.bitchute.com/policy/guidelines/#content-sensitivity" target="_blank" rel="noopener noreferrer">Normal - Content that is suitable for ages 16 and over</a></td></tr>
</table>
</div>
</div>

```


### Playing next and Related Videos

```html
<div class="sidebar-video">
    <div class="sidebar-next text-center">
        <h2 class="sidebar-heading">Playing Next<span data-toggle="tooltip" data-placement="bottom" title="Currently watching videos from Computing Forever. The next video has been automatically selected from this channel."><i class="fal fa-question-circle fa-fw" data-fa-transform="shrink-4"></i></span></h2>
        <label class="sidebar-autoplay switch" data-toggle="tooltip" data-placement="bottom" title="Play next video automatically">
            <input id="autoplay-toggle" type="checkbox" checked />
            <div class="slider"></div>
        </label>
        <div class="video-card">
            <a href="/video/dWrcn2XK1Fc/" class="spa">
                <div class="video-card-image">
                    <img class="img-responsive lazyload" src="/static/v128/images/loading_320x180.png" data-src="https://static-3.bitchute.com/live/cover_images/hybM74uIHJKf/dWrcn2XK1Fc_320x180.jpg" onerror="this.src='/static/v128/images/blank_320x180.png';this.onerror='';" alt="video image">
                    <img class="img-responsive play-overlay" src="/static/v128/images/play-button.png" alt="play">
                    <span class="video-views"><i class="far fa-eye"></i> 2566</span>
                    <span class="video-duration">14:49</span>
                </div>
            </a>
            <div class="video-card-text">
                <p class="video-card-title"><a href="/video/dWrcn2XK1Fc/" class="spa">Michael Leahy Discusses Ireland’s Proposed Hate Speech and Hate Crime Laws</a></p>
                <p class="video-card-channel"><a href="/channel/computingforever/" class="spa">Computing Forever</a></p>
                <p class="video-card-published">7 hours ago</p>
            </div>
        </div>
    </div>
    

    <div class="sidebar-recent text-center">
        <h2 class="sidebar-heading">Related Videos<span data-toggle="tooltip" data-placement="bottom" title="Related videos have been selected from Computing Forever, the parent channel for this video"><i class="fal fa-question-circle fa-fw" data-fa-transform="shrink-4"></i></span></h2>
        
        <div class="video-card">
            <a href="/video/nu0g7jrPSME/" class="spa">
                <div class="video-card-image">
                    <img class="img-responsive lazyload" src="/static/v128/images/loading_320x180.png" data-src="https://static-3.bitchute.com/live/cover_images/hybM74uIHJKf/nu0g7jrPSME_320x180.jpg" onerror="this.src='/static/v128/images/blank_320x180.png';this.onerror='';" alt="video image">
                    <img class="img-responsive play-overlay" src="/static/v128/images/play-button.png" alt="play">
                    <span class="video-views"><i class="far fa-eye"></i> 10.5K</span>
                    <span class="video-duration">20:48</span>
                </div>
            </a>
            <div class="video-card-text">
                <p class="video-card-title"><a href="/video/nu0g7jrPSME/" class="spa">How is This a Thing? 26th of November 2020</a></p>
                <p class="video-card-published">3 days, 1 hour ago</p>
            </div>
        </div>
        
        <div class="video-card">
            ...
        </div>
    </div>
</div>
```

Comments are loaded via Javascript and need a different handling.

## Channel Page

### About

Link: ```https://www.bitchute.com/channel/CHANNELID/#channel-about```

Data points: 

- Profile link
- Date created
- Video count
- Subscriber count
- View count
- Category
- Website Link
- Twitter Link
- YouTube Link
- Description


```html
<div class="tab-pane" id="channel-about">
    <div class="row">
        <div class="col-md-3 col-sm-4 col-xs-12 channel-about-container">
            <img id="fileupload-medium-icon-2" class="img-responsive lazyload hidden-xs hidden-sm" src="/static/v128/images/loading_medium.png" data-src="https://static-3.bitchute.com/live/channel_images/y1dtuC7TDmPY/lSO7KckmNmL5LmJilOurn4wK_medium.jpg" onerror="this.src='/static/v128/images/blank_medium.png';this.onerror='';" alt="Channel Image">
            <img id="fileupload-large-icon-2" class="img-responsive lazyload hidden-md hidden-lg" src="/static/v128/images/loading_large.png" data-src="https://static-3.bitchute.com/live/channel_images/y1dtuC7TDmPY/lSO7KckmNmL5LmJilOurn4wK_large.jpg" onerror="this.src='/static/v128/images/blank_large.png';this.onerror='';" alt="Channel Image">
            <div class="channel-about-details">
                <p>Created 3 years, 1 month ago.</p>
                <p><span><i class="fas fa-video fa-fw"></i> <span>249 videos</span></span></p>
                <p><span><i class="fas fa-users fa-fw"></i> <span id="about-subscriber-count"><i class="fas fa-spinner fa-pulse fa-fw"></i></span></span></p>
                <p><span><i class="fas fa-eye fa-fw"></i> <span id="about-view-count"><i class="fas fa-spinner fa-pulse fa-fw"></i></span></span></p>
                <p>Category <span class=""><a href="/category/education/" class="spa">Education</a></span></p>
            </div>
        </div>
        <div id="channel-description" class="col-md-9 col-sm-8 col-xs-12">
            <p>Live life under your terms... and go your own way.<br>I hope you enjoy my videos.</p>
            <p>- huMAN.</p>
        </div>
    </div>
</div>
```


### Videos

Link: ```https://www.bitchute.com/channel/Tb8OhoNNm41W/#channel-videos```

Data Points per video:

- Video published date
- Video title
- id (link)
- Video description (with a lot of links)
- Video view count
- Video duration

```html
<div class="channel-videos-list">
    <div class="channel-videos-container">
        <div class="row">
            <div class="col-md-5 col-sm-6 text-center">
                <div class="channel-videos-image-container">
                    <a href="/video/NLezfyx93CA/" class="spa">
                        <div class="channel-videos-image">
                            <img class="img-responsive lazyload" src="/static/v128/images/loading_640x360.png" data-src="https://static-3.bitchute.com/live/cover_images/y1dtuC7TDmPY/NLezfyx93CA_640x360.jpg" onerror="this.src='/static/v128/images/blank_640x360.png';this.onerror='';" alt="video image">
                            <img class="img-responsive play-overlay" src="/static/v128/images/play-button.png" alt="play">
                            <span class="video-views"><i class="far fa-eye"></i> 101</span>
                            <span class="video-duration">5:15</span>
                        </div>
                    </a>
                </div>
            </div>
            <div class="col-md-7 col-sm-6">
                <div class="channel-videos-text-container">
                    <div class="channel-videos-details text-right hidden-xs">
                        <span>Dec 03, 2020</span>
                    </div>
                    <div class="channel-videos-title">
                        <a href="/video/NLezfyx93CA/" class="spa">Why women love men with money - ( it&#x27;s not what you think )</a>
                    </div>
                    <div class="channel-videos-text">
                        <p>Women generally love a man with money. Sure. We know that. It’s disappointing, but it’s old news... But, aside from getting resources, why does money excite a woman so much as a THING?</p>
                        <p>------------------------------------------<br>▶️ VIDEO TIMESTAMPS:</p>
                        <p>00:00 - Intro<br>00:22 - Don’t believe the hype<br>01:21 - Why money though?<br>01:45 - Women’s contradictions<br>02:18 - THIS is the reason why...<br>02:32 - SECURITY and CHAOS<br>04:37 - Subscribe, Share, Like, Comment and Support</p>
                        <p>⚪ DONATE / SUPPORT:<br>------------------------------------------<br>◾ PAYPAL: <a href="https://www.paypal.me/huMANMGTOW" rel="nofollow">https://www.paypal.me/huMANMGTOW</a><br>◾ PATREON: <a href="https://www.patreon.com/huMAN_onPatreon" rel="nofollow">https://www.patreon.com/huMAN_onPatreon</a></p>
                        <p>⚪ CONNECT:<br>------------------------------------------<br>◾ EMAIL: <a href="/cdn-cgi/l/email-protection#31525e5f455052455c4359445c505f71565c50585d1f525e5c"><span class="__cf_email__" data-cfemail="5f3c30312b3e3c2b322d372a323e311f38323e3633713c3032">[email&#160;protected]</span></a><br>◾ INSTAGRAM: <a href="https://www.instagram.com/human_oninsta/" rel="nofollow">https://www.instagram.com/human_oninsta/</a><br>◾ BLOG: <a href="https://humanspage.blogspot.com/" rel="nofollow">https://humanspage.blogspot.com/</a><br>◾ DISCORD: <a href="https://discord.gg/BmyjPAz" rel="nofollow">https://discord.gg/BmyjPAz</a></p>
                        <p>⚪ CONTENT:<br>------------------------------------------<br>◾ BITCHUTE: <a href="https://www.bitchute.com/channel/huMAN_on_bitchute" rel="nofollow">https://www.bitchute.com/channel/huMAN_on_bitchute</a><br>◾ MUSIC: <a href="https://www.youtube.com/channel/UCChjo_fASARO4kRtWpAg6Yw" rel="nofollow">https://www.youtube.com/channel/UCChjo_fASARO4kRtWpAg6Yw</a></p>
                        <p>⚪ PODCAST:<br>------------------------------------------<br>◾ ANCHOR: <a href="https://anchor.fm/mrhuman" rel="nofollow">https://anchor.fm/mrhuman</a><br>(and most other podcast feeds)</p>
                        <p>=============================<br>USED IN THIS VIDEO<br>=============================</p>
                        <p>◼️ GEAR USED:</p>
                        <p>CAMERA: Canon eos-R.<br>LENS: Canon 50mm f/1.4<br>LIGHTS: 1x softbox, 1x Yongnuo RBG light<br>POST-PRODUCTION: Premier Pro CC</p>
                        <p>◼️ Words, production, music, video &amp; graphics: Copyright © huMAN</p>
                        <p>-----------------------------------------<br>#women #money #contradiction</p>
                    </div>
                    <div class="channel-videos-details text-left hidden-sm hidden-md hidden-lg hidden-xl">
                        <span>Dec 03, 2020</span>
                    </div>
                </div>
            </div>
        </div>
    </div>
    <div class="channel-videos-container">
        ...
    </div>
    <div class="channel-videos-container">
        ...
    </div>
</div>
```

### Most viewed

Data Points: 

- Video title
- Video published duration
- Video view count
- Video title
- Id (link)

```html
<div class="sidebar">
    <div class="sidebar-video">
        <h1 class="sidebar-heading">Most Viewed</h1>
        <div class="video-card">
            <a href="/video/JWr8bKgJ8IM/" class="spa">
                <div class="video-card-image">
                    <img class="img-responsive lazyload" src="/static/v128/images/loading_320x180.png" data-src="https://static-3.bitchute.com/live/cover_images/y1dtuC7TDmPY/JWr8bKgJ8IM_320x180.jpg" onerror="this.src='/static/v128/images/blank_320x180.png';this.onerror='';" alt="video image">
                    <img class="img-responsive play-overlay" src="/static/v128/images/play-button.png" alt="play">
                    <span class="video-views"><i class="far fa-eye"></i> 1524</span>
                    <span class="video-duration">12:33</span>
                </div>
            </a>
            <div class="video-card-text">
                <p class="video-card-title"><a href="/video/JWr8bKgJ8IM/" class="spa">The push to make you fragile</a></p>
                <p class="video-card-published">1 year, 5 months ago</p>
            </div>
        </div>
    <div class="video-card">
    ...
    </div>
    <div class="video-card">
    ...
    </div>
</div>
```

