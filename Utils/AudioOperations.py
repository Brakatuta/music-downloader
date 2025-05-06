import os
from . import FileOperations
import subprocess
import eyed3

FFMPEG_INSTANCE = None

def setup_mobile_ffmpeg():
    global FFMPEG_INSTANCE
    
    """Check if MobileFFmpeg is available on Android."""
    if platform == 'android':
        from jnius import autoclass
        try:
            FFmpegKit = autoclass('com.arthenica.ffmpegkit.FFmpegKit')
            print("MobileFFmpeg is available!")
            FFMPEG_INSTANCE = FFmpegKit
        except Exception as e:
            print("Error: MobileFFmpeg is not available!")
            print(e)

def convert_quality_level_to_ffmpeg_valid_string(quality_level):
    quality_strings = {
        "low-quality": '8', 
        "normal-quality": '4', 
        "high-quality": '0'
    }
    return quality_strings[quality_level]

def convert_to_mp3(input_file, output_file, quality_level=0):
    """
    Convert a .webm or .mp4 file to .mp3 format using FFmpeg.
    Uses MobileFFmpeg on Android and subprocess on other platforms.
    """
    if not os.path.exists(input_file):
        raise FileNotFoundError(f"Input file {input_file} does not exist.")

    if not output_file.endswith('.mp3'):
        raise ValueError("Output file must have a .mp3 extension.")

    ffmpeg_convert_quality = convert_quality_level_to_ffmpeg_valid_string(quality_level)

    if platform == 'android':
        if FFMPEG_INSTANCE is None:
             print("Error: FFMPEG_INSTANCE is not initialized!")
             
        # Format command properly
        command_str = f"-i \"{input_file}\" -vn -acodec libmp3lame -q:a {ffmpeg_convert_quality} -y \"{output_file}\""
        
        # Execute the command
        try:
            FFMPEG_INSTANCE.execute(command_str)
        except Exception as e:
            pass
        
        if os.path.exists(output_file):
            print(f"MobileFFmpeg Conversion successful! MP3 saved as: {output_file}")
        else:
            print(f"Error during conversion with MobileFFmpeg: {e}")
    else:
        import imageio_ffmpeg
        ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
        command = [ffmpeg_path, "-i", input_file, "-vn", "-acodec", "libmp3lame", "-q:a", ffmpeg_convert_quality, "-y", output_file]
        try:
            subprocess.run(command, check=True)
            print(f"Conversion successful! MP3 saved as: {output_file}")
        except subprocess.CalledProcessError as e:
            print(f"Error during conversion: {e}")

def add_meta_tags_to_audiofile(quality_level, video_file, title, artist, album_cover=None):
    new_file_path = FileOperations.change_file_extension(video_file, ".mp3")
    convert_to_mp3(video_file, new_file_path, quality_level)
    os.remove(video_file)  # Remove original video file after conversion
    
    audiofile = eyed3.load(new_file_path)
    audiofile.initTag()
    audiofile.tag.title = title
    audiofile.tag.artist = artist
    if album_cover is not None:
        audiofile.tag.images.set(3, open(album_cover, 'rb').read(), 'image/jpeg')
        audiofile.tag.save(version=eyed3.id3.ID3_V2_3)

def get_infos_from_mp3(file_path, temp_image_save_path, album_cover=True):
    data : dict = {
        "artist" : None,
        "title" : None,
        "album_cover_path" : None
    }
    
    def second_artist_and_title_extraction_method2():
        # get the atist name and title from file name instead
        splitted_file_name = file_path.split("\\")[-1].split(" - ")
        data["artist"] = splitted_file_name[1].replace(".mp3", "")
        data["title"] = splitted_file_name[0]
    
    try:
        audiofile = eyed3.load(file_path)
        if not audiofile or not audiofile.tag:
            print("No tag found in the MP3 file: ", file_path)
            second_artist_and_title_extraction_method2()
        else:
            # default method
            data["artist"] = audiofile.tag.artist
            data["title"] = audiofile.tag.title
    except Exception as e:
        print(f"Error extracting artist and title via eyed3. Trying diffrent method: {e}")
        second_artist_and_title_extraction_method2()
        return None
    
    if album_cover == False:
        return data
    
    try:
        # Check if there are any images in the tag
        if not audiofile.tag.images:
            print("No cover art found in the MP3 file: ", file_path)
            return None
        
        for image in audiofile.tag.images:
            image_file = open(temp_image_save_path, "wb")
            image_file.write(image.image_data)
            image_file.close()
            data["album_cover_path"] = temp_image_save_path
            break
            
    except Exception as e:
        print(f"Error extracting cover art: {e}")
        return None
    
    return data