import re
from . import SSLCertHelper
from . import Proxy
from . import markers

from .pytubefix import YouTube

SSLCertHelper.set_default_ssl_context()

YT_MUSIC_MARKERS_ALL = []
YT_MUSIC_LYRICS_MARKERS_ALL = []
YT_MOVIE_TRAILER_MARKERS = []

for __markers in markers.markers["YT_MUSIC_MARKERS"].values():
    for marker in __markers:
        YT_MUSIC_MARKERS_ALL.append(marker)

for __markers in markers.markers["YT_LYRICS_MARKERS"].values():
    for marker in __markers:
        YT_MUSIC_LYRICS_MARKERS_ALL.append(marker)

for __markers in markers.markers["YT_MOVIE_TRAILER_MARKERS"].values():
    for marker in __markers:
        YT_MOVIE_TRAILER_MARKERS.append(marker)
        
def format_video_title(video_author, video_title, full_spotify_title) -> str:
    video_author_check : str = str.lower(video_author.replace(" ", ""))
    video_title_check : str = str.lower(video_title.replace(" ", ""))[:(video_title.find("-") - 2)]
    
    if not "-" in video_title and not video_title_check in video_author_check:
        video_title = video_author + " " + video_title
    
    return video_title

def video_title_contains_yt_music_markers(video_title, priorise_lyrics_videos):
    desired_marker = YT_MUSIC_MARKERS_ALL
    
    if priorise_lyrics_videos:
        desired_marker = YT_MUSIC_LYRICS_MARKERS_ALL
    
    for marker in desired_marker:
        if str.lower(marker) in str.lower(video_title):
            return True
    return False

def video_is_trailer(video_title):
    for marker in YT_MOVIE_TRAILER_MARKERS:
        if str.lower(marker) in str.lower(video_title):
            return True
    return False

def song_title_similiraty_ratio(str1 : str, str2 : str):
    characters_to_exclude = " !@#$%^&*()_+-_,/><[]{}"
    
    for marker in YT_MUSIC_MARKERS_ALL or marker in YT_MUSIC_LYRICS_MARKERS_ALL:
        found_position = str2.find(marker)
        if found_position > -1:
            str2 = str2.replace(marker, "")
            
    str1_words = [word.lower() for word in str1.split()]
    str2_words = [word.lower() for word in str2.split()]
    amount_words_str2 = 0
    
    for word in str2_words:
        if not word in characters_to_exclude:
            amount_words_str2 += 1
    matching_words = 0
    
    for word in str1_words:
        if not word in characters_to_exclude:
            if word in str2_words:
                matching_words += 1
            else:
                matching_words -= 1
    
    matching_words_ratio = matching_words / amount_words_str2
    length_ratio = len(str1) / len(str2)
    simlarity = matching_words_ratio * length_ratio
    
    return simlarity

def get_desired_quality_audiostreams(download_quality_level, youtube_link, use_proxy = False):
    if use_proxy == True:
        proxy = Proxy.get_random_proxy()
        print("Getting streams with proxy: ", proxy)
        streams = YouTube(youtube_link, proxies=proxy).streams.filter(only_audio=True)
    else:
        streams = YouTube(youtube_link).streams.filter(only_audio=True)
        
    sorted_streams = {}

    for stream in streams:
        abr_match = re.search(r"abr=\"([^\"]+)\"", str(stream))
        if abr_match:
            abr_value = abr_match.group(1)
            abr_value = re.findall(r'\d+', abr_value)[0]
            sorted_streams[int(abr_value)] = stream

    sorted_streams = sorted(sorted_streams.items(), key=lambda x: x[0])

    low_quality_stream = sorted_streams[0][1]
    normal_quality_stream = sorted_streams[round(len(sorted_streams) / 3) - 1][1]
    high_quality_stream = sorted_streams[len(sorted_streams) - 1][1]

    if download_quality_level == 1:
        return {"low-quality": low_quality_stream}
    elif download_quality_level == 2:
        return {"normal-quality": normal_quality_stream}
    elif download_quality_level == 3:
        return {"high-quality":high_quality_stream}
    elif download_quality_level == 4:
        return {
            "low-quality": low_quality_stream,
            "normal-quality": normal_quality_stream,
            "high-quality": high_quality_stream
        }