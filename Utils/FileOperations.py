import os
import shutil
import re

def count_files(directory):
    return len([f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))])

def sanitize_filename(filename):
    # Windows reserved characters are < > : " / \ | ? *
    sanitised_filename = re.sub(r'[<>:/\\|?*]', '_', filename)
    sanitised_filename = re.sub(r'["„“]', "'", sanitised_filename)
    return sanitised_filename

def clear_folder(folder_path):
    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        if os.path.isfile(file_path) or os.path.islink(file_path):
            os.remove(file_path)
        elif os.path.isdir(file_path):
            shutil.rmtree(file_path)

def remove_artifacts(file_path, artifact_file_types):
    # for file_type in artifact_file_types:
    #     for filename in os.listdir(file_path):
    #         if filename.endswith(file_type):
    #             file_path = os.path.join(file_path, filename)
    #             os.remove(file_path)
    pass

def change_file_extension(file_path, new_extension):
    new_file_path = os.path.splitext(file_path)[0] + new_extension
    return new_file_path


def get_files_in_order(directory):
    try:
        # List files in the directory and sort them alphabetically
        files = sorted(
            [os.path.join(directory, f) for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]
        )
        return files
    except FileNotFoundError:
        print(f"Directory '{directory}' not found.")
        return []
