import os
import time
import requests
import threading
import io
import zipfile

import streamlit as st

import spotipy

from Utils.pytubefix import YouTube

from Utils import SSLCertHelper
from Utils import Proxy
from Utils import Threaded
from Utils import FileOperations
from Utils import AudioOperations
from Utils import spoptifyAPI
from Utils import Filters
from Utils.YTSearch import YoutubeSearch

SSLCertHelper.set_default_ssl_context()

sp : spotipy.Spotify

DEFAULT_SPOTIFY_CLIENT_ID : str = "b311200a3cc24de296ab17294a0e207f"
DEFAULT_SPOTIFY_CLIENT_SECRET : str = "13f43cc9bc3844deae7a2f778b6845f1"

YOUTUBE_BASELINK : str = "https://www.youtube.com/watch?v="

MAXAMOUNT_THREADS : int = os.cpu_count() * 2
MAXAMOUNT_YT_VIDEOS_TO_SEARCH : int = 32
MAXAMOUNT_RETRIES : int = 10
MAXAMOUNT_YT_VIDEOS_TO_SEARCH : int = 32

thread_pool : Threaded.ThreadPool = Threaded.set_up_thread_pool(MAXAMOUNT_THREADS, MAXAMOUNT_RETRIES)

spotify_url = ""
prioritize_lyrics = False
add_additional_audio_infos = False
download_quality_level = 2

use_proxies = False
amount_download_retries = 4
amount_threads = int(os.cpu_count() / 2)
amount_function_retries = 4
search_queue_size = 25

# Dwonload Retrying Queue
retry_downloads_queue : list = [
    # (infos, retry count)
]

# Variables
download_canceled : bool = False
audios_to_download : int = 0
failed_downloads : int = 0
downloaded_audios : int = 0

yt_verfied : bool = False

if 'download_ready' not in st.session_state:
    st.session_state.download_ready = False
if 'zip_buffer' not in st.session_state:
    st.session_state.zip_buffer = None

def create_zip_buffer(download_path):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(download_path):
            for file in files:
                print(file)
                full_path = os.path.join(root, file)
                arcname = os.path.relpath(full_path, start=download_path)
                print("ZIPPING:", full_path)
                zipf.write(full_path, arcname)
    buffer.seek(0)
    return buffer

def set_up_thread_pool():
    global thread_pool
    thread_pool = Threaded.set_up_thread_pool(amount_threads, amount_function_retries)

def download_async_wrapper(spotify_link, download_path):
    thread = threading.Thread(target=download_playlist_audios, args=(spotify_link, download_path))
    thread.start()

def submit_spotify_client_id_and_secret(client_id: str, client_secret : str):
    if client_id == "" and client_secret == "":
        print("Using default spotify credentials. Not recommended!")
        global sp
        informations : list = spoptifyAPI.validate_spotify_credentials(DEFAULT_SPOTIFY_CLIENT_ID, DEFAULT_SPOTIFY_CLIENT_SECRET)
        sp = informations[1]
        return True
    
    if client_id != DEFAULT_SPOTIFY_CLIENT_ID and client_secret != DEFAULT_SPOTIFY_CLIENT_SECRET:
        success : bool = load_spotify(client_id, client_secret)
        return success

def load_spotify(client_id: str, client_secret : str):
    global sp
    informations : list = spoptifyAPI.validate_spotify_credentials(client_id, client_secret)
    if informations[0] == True:
        sp = informations[1]
        return True
    else:
        return False

def get_spotify_playlist_tracks(playlist_link) -> list:
    results = sp.playlist_tracks(playlist_link)
    tracks = results['items']
    while results['next']:
        results = sp.next(results)
        tracks.extend(results['items'])
    track_info : list = [(track['track']['name'], track['track']['artists'], int(track['track']['duration_ms'] / 1000), track['track']['album']['images'][0]['url']) for track in tracks]
    return track_info

def get_youtube_video(track_title, artist_name, duration) -> str | None:
    if download_canceled:
        return
    
    max_duration : int = duration * 1.5
    min_duration : int = duration * 0.75
    
    search_query : str = f"{artist_name} - {track_title}"
    search_results : dict = YoutubeSearch(search_query, max_results=search_queue_size, proxy=use_proxies).get_results()
    results : list = []

    for _index, video_infos in enumerate(search_results):
        __video_author : str = video_infos['author']
        __video_title : str = video_infos['title']
        
        full_spotify_title : str = f"{artist_name} {track_title}"
        video_title : str = Filters.format_video_title(__video_author, __video_title, full_spotify_title)
        
        video_views : int = video_infos['views']
        video_duration : int = video_infos['duration_in_seconds']
        
        similarity : float = Filters.song_title_similiraty_ratio(full_spotify_title, video_title)

        # help to exclude non-music videos
        if similarity > 0.15 and Filters.video_title_contains_yt_music_markers(video_title, prioritize_lyrics):
            similarity += 0.25
        
        # exclude too short or too long videos and boost videos close to the actual duration
        if video_duration < min_duration or video_duration > max_duration:
            similarity = 0
        elif abs(video_duration - duration) <= 10 and similarity > 0.15:
            similarity += 0.35 * (duration / video_duration)
        
        # exclude trailers
        if Filters.video_is_trailer(video_title):
            similarity = 0
        
        similarity *= float(video_views)

        results.append([similarity, video_duration, video_title, video_views, YOUTUBE_BASELINK + video_infos['id']])
    
    # sort results after similarity ratio
    results = sorted(results, key=lambda x: x[0], reverse=True)
    
    # for result in results:
    #     print(result)

    return results[0][4]

def get_yt_object(video_link) -> YouTube | None:
    if use_proxies:
        yt = YouTube(url=video_link, use_po_token=True, proxies=Proxy.get_random_proxy())
    else:
        yt = YouTube(url=video_link, use_po_token=True)
    return yt

def download_audio_from_youtube(download_path, title, artist, duration, album_cover_url, queue_index) -> None:
    global downloaded_audios
    global failed_downloads
    global retry_downloads_queue

    if download_canceled:
        return

    update_console_log(f"Searching for '{title}' by '{artist}' on YouTube...\n")
                            
    youtube_link : str | None = get_youtube_video(title, artist, duration)
    if youtube_link != None:
        update_console_log(f"Found YouTube link: {youtube_link}\n")
        try:
            yt = get_yt_object(youtube_link)

            update_console_log(f"Title: {yt.title}\n")
            update_console_log(f"Views: {yt.views}\n")

            audio_streams : dict = Filters.get_desired_quality_audiostreams(download_quality_level, yt.streams)
            for audio_quality in audio_streams.keys():
                audio_stream = audio_streams[audio_quality]
                audio_file_mp4 = audio_stream.download(download_path)
                if len(audio_streams) == 1:
                    new_file_name = FileOperations.sanitize_filename(f"{title} - {artist}")
                else:
                    new_file_name = FileOperations.sanitize_filename(f"{title} - {artist} - {audio_quality}")
                new_file = audio_file_mp4.replace(os.path.basename(audio_file_mp4), new_file_name)
                if add_additional_audio_infos:
                    new_file += os.path.splitext(audio_file_mp4)[1]
                    print(new_file)
                    os.rename(audio_file_mp4, new_file)
                    temp_picture_path = os.path.join(os.path.dirname(__file__), "app_images/mp3_thumbnail_images_cache/" + FileOperations.sanitize_filename(f"{title} - {artist}") + ".jpg")
                    cover_image_data = requests.get(album_cover_url).content
                    if type(cover_image_data) == bytes:
                        f = open(temp_picture_path,'wb') 
                        f.write(cover_image_data) 
                        f.close()
                    else:
                        temp_picture_path = None
                        update_console_log(f"An error occurred: No cover art found for '{title}' by '{artist}'\n")
                    AudioOperations.add_meta_tags_to_audiofile(audio_quality, new_file, title, artist, temp_picture_path)
                else:
                    os.rename(audio_file_mp4, new_file + ".mp3")
            downloaded_audios += 1
            update_console_log(f"Download completed! | '{title}' by '{artist}'\n")
            update_console_log(f"{max(audios_to_download - downloaded_audios - failed_downloads, 0)} downloads remaining.\n")
            retry_downloads_queue[queue_index][5] = True
            if retry_downloads_queue[queue_index][4] > 0:
                update_console_log(f"Success retrying to download '{title}' by '{artist}'\n")
        except Exception as e:
            update_console_log(f"An error occurred: {e}\n")
            print(f"An error occurred: {e}\n")
            failed_downloads += 1
    else:
        update_console_log(f"No suitable YouTube video found for '{title}' by '{artist}'\n")
        print(f"No suitable YouTube video found for '{title}' by '{artist}'\n")
        failed_downloads += 1

def retry_download(download_path) -> None:
    try:
        global retry_downloads_queue
        needed_success_rate : int = len(retry_downloads_queue)
        success_rate : int = 0
        for index, values in enumerate(retry_downloads_queue):
            values[4] += 1
            title, artist, duration, album_cover, _, success, _ = values
        
            if success:
                success_rate += 1
            else:
                if values[4] <= amount_download_retries:
                    update_console_log(f"Retrying to download '{title}' by '{artist}'\n")
                    thread_pool.submit(download_audio_from_youtube, (download_path, title , artist, duration, album_cover, index))
                else:
                    update_console_log(f"Download retry count exceeded for '{title}' by '{artist}'\n")
                    success_rate += 1
        thread_pool.join()
    
        if success_rate == needed_success_rate: 
            update_console_log(f"Process complete!\n")
        else:
            retry_download(download_path)
    except Exception as e:
        update_console_log(f"A fatal error occurred during download retry: {e}\n")
        print(f"A fatal error occurred during download retry: {e}\n")

def download_playlist_audios(spotify_link, download_path) -> None:
    try:
        spotify_link_type : str | None = spoptifyAPI.get_spotify_link_type(spotify_link)
        track_info = None
        
        if spotify_link_type == "playlist":
            track_info = get_spotify_playlist_tracks(spotify_link)
        elif spotify_link_type == "song":
            song_info = sp.track(spotify_link)
            track_info = [(
                song_info['name'], 
                song_info['artists'],
                int(song_info['duration_ms'] / 1000), # convert to seconds
                song_info['album']['images'][0]['url']
            )]
        else:
            update_console_log(f"'{spotify_link}' is not a valid spotify link!\n")
        if track_info != None:
            global audios_to_download
            global downloaded_audios
            global retry_downloads_queue

            audios_to_download = len(track_info)

            for title, artists, duration, album_cover in track_info:
                index : int = max(len(retry_downloads_queue), 0)

                if download_canceled:
                    return
                
                artist : str = ""
                for artist_info in artists:
                    artist += artist_info['name'] + ", "
                artist = artist.rstrip(artist[-1])
                artist = artist.rstrip(artist[-1])
                test_file_name = FileOperations.sanitize_filename(f"{title} - {artist}.mp3")

                if os.path.exists(os.path.join(download_path, test_file_name)):
                    update_console_log(f"Track '{title}' by '{artist}' already downloaded. Skipping Track.\n")
                    retry_downloads_queue.append([title, artist, duration, album_cover, 0, True, index])
                    downloaded_audios += 1
                else:
                    retry_downloads_queue.append([title, artist, duration, album_cover, 0, False, index])
                    thread_pool.submit(download_audio_from_youtube, (download_path, title, artist, duration, album_cover, index))
            thread_pool.join()
        update_console_log(f"Successfully downloaded {downloaded_audios} / {audios_to_download} audio files.\n")
        if amount_download_retries > 0:
            if failed_downloads == 0:
                update_console_log(f"Process complete!\n")
            else:
                retry_download(download_path)
        else:
            update_console_log(f"Process complete!\n")
    except Exception as e:
        update_console_log(f"An error occurred during download: {e}\n")
        print(f"An error occurred during download: {e}\n")
    finally:
        print("Download process complete!")

def update_console_log(text):
    print(text)

def __ui():
    global spotify_url, prioritize_lyrics, add_additional_audio_infos, download_quality_level, use_proxies
    global amount_download_retries, amount_threads, amount_function_retries, search_queue_size

    st.title("Music Downloader")

    spotify_link = st.text_input("Enter Spotify Song/Playlist Url", placeholder="Song/Playlist Url")

    st.write("")
    st.write("<div style='text-align: center; '>Set your download and audio settings. 'All Qualities' will download all available audio qualities</div>", unsafe_allow_html=True)

    if spotify_link:
        spotify_url = spotify_link

        # search = YoutubeSearch(spotify_link, 20, proxy=True)
        
        # sorted_search = sorted(search.get_results(), key=lambda x: x['views'], reverse=True)
        
        # for result in sorted_search:
        #     st.write(result["title"], " | ", result["author"], " | ", result["views"], " | ", result["duration"])
    
    st.write("")

    row1 = st.columns(2)

    with row1[0]:
        audio_quality_menu = st.selectbox("Select Audio Quality", ("Low Quality", "Normal Quality", "High Quality", "All Qualities"), index=1)
        if audio_quality_menu == "Low Quality":
            download_quality_level = 1
        elif audio_quality_menu == "Normal Quality":
            download_quality_level = 2
        elif audio_quality_menu == "High Quality":
            download_quality_level = 3
        elif audio_quality_menu == "All Qualities":
            download_quality_level = 4
        
        prioritize_lyrics_toggle = st.toggle("Prioritize Lyrics")
        if prioritize_lyrics_toggle:
            prioritize_lyrics = True
        else:
            prioritize_lyrics = False
        
        add_cover_art_and_artist_infos_toggle = st.toggle("Add Cover Art and Artist Info")
        if add_cover_art_and_artist_infos_toggle:
            add_additional_audio_infos = True
        else:
            add_additional_audio_infos = False
        
        proxy_toggle = st.toggle("Use Proxies when downloading")
        if proxy_toggle:
            use_proxies = True
        else:
            use_proxies = False
        
        st.write("Input your Spotify Client ID and Secret, you can get them [here](https://developer.spotify.com/dashboard/applications)")
        st.write("It is recommended to use your own ID and Secret")

        client_id = st.text_input("Spotify Client ID", placeholder="Client Id")
        client_secret = st.text_input("Spotify Client Secret", placeholder="Client Secret")

        sub_row1 = st.columns([0.3, 0.7])

        with sub_row1[0]:
            submit_button = st.button("Submit")
            if submit_button:
                success = submit_spotify_client_id_and_secret(client_id, client_secret)
                
                with sub_row1[1]:
                    if success:
                        st.success("✅ Spotify Account verified!")
                        st.markdown("<style>div[data-testid='stAlertContainer'] { height: 40px; }</style>", unsafe_allow_html=True)
                        st.markdown("<style>div[data-testid='stAlertContentSuccess'] { line-height: 0.5; }</style>", unsafe_allow_html=True)
                    else:
                        st.error("❌ Id or Secret invalid!")
                        st.markdown("<style>div[data-testid='stAlertContainer'] { height: 40px; }</style>", unsafe_allow_html=True)
                        st.markdown("<style>div[data-testid='stAlertContentError'] { line-height: 0.5; }</style>", unsafe_allow_html=True)
                        time.sleep(2)
                        st.rerun()

    with row1[1]:
        amount_download_retries = st.slider("Amount of Download Retries", key="download_retries_slider", min_value=0, max_value=MAXAMOUNT_RETRIES, value=amount_download_retries)
        amount_threads = st.slider("Amount of Threads", min_value=0, key="threads_slider", max_value=MAXAMOUNT_THREADS, value=amount_threads)
        amount_function_retries = st.slider("Amount of Function Retries", key="function_retries_slider", min_value=0, max_value=MAXAMOUNT_RETRIES, value=amount_function_retries)
        search_queue_size = st.slider("Search Queue Size", key="yt_search_queue_size_slider", min_value=0, max_value=MAXAMOUNT_YT_VIDEOS_TO_SEARCH, value=search_queue_size)
    
    temp_downloads_dir = os.path.join(os.getcwd(), "temp_data/temp_downloads")
    os.makedirs(temp_downloads_dir, exist_ok=True)
    download_path = temp_downloads_dir

    if spotify_url:
        download_button = st.button("Start Download")
        if download_button:
            st.session_state.download_ready = False
            download_async_wrapper(spotify_url, download_path)

        check_button = st.button("Check Download Status")
        if check_button:
            if downloaded_audios == downloaded_audios:
                print("checked data")
                st.session_state.download_ready = True
                st.session_state.zip_buffer = create_zip_buffer(download_path) 

        if st.session_state.download_ready:
            st.success("Download ready!")
            st.download_button(
                label="Download All Files",
                data=st.session_state.zip_buffer,
                file_name="music_downloads.zip",
                mime="application/zip"
            )

            #clear temp downloads
            for filename in os.listdir(temp_downloads_dir):
                file_path = os.path.join(temp_downloads_dir, filename)
                os.remove(file_path)
    
def __main():
    st.set_page_config(
        page_title="Music Downloader",
        page_icon="👋",
    )

    submit_spotify_client_id_and_secret("", "")

    __ui()

__main()

#streamlit run main.py