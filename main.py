import os
import requests # type: ignore
from urllib.parse import urlparse, urljoin

def get_unique_filename(output_folder, filename):
    """
    Check if the filename exists in the output folder.
    If it does, add a unique number suffix to avoid overwriting.
    """
    base, extension = os.path.splitext(filename)
    counter = 1
    unique_filename = filename
    
    while os.path.exists(os.path.join(output_folder, unique_filename)):
        unique_filename = f"{base}_{counter}{extension}"
        counter += 1
    
    return unique_filename

def download_m3u8_file(m3u8_url, folder):
    # Create the folder if it doesn't exist
    if not os.path.exists(folder):
        os.makedirs(folder)

    # Get the filename from the URL
    m3u8_filename = os.path.join(folder, m3u8_url.split('/')[-1])

    try:
        print(f"Downloading .m3u8 file from {m3u8_url}...")

        # Send a GET request to download the .m3u8 file
        response = requests.get(m3u8_url)
        response.raise_for_status()

        # Write the content to the .m3u8 file
        with open(m3u8_filename, 'wb') as file:
            file.write(response.content)

        print(f".m3u8 file saved as {m3u8_filename}")
        return m3u8_filename

    except Exception as e:
        print(f"Failed to download .m3u8 file: {e}")
        return None

def extract_ts_urls_from_m3u8(m3u8_filename, base_url, output_txt):
    try:
        # Read the .m3u8 file to extract .ts URLs
        ts_urls = []
        with open(m3u8_filename, 'r') as file:
            for line in file:
                line = line.strip()
                if line and line.endswith('.ts'):  # Look for .ts URLs
                    # If the .ts URL is relative, join it with the base URL
                    if not line.startswith('http'):
                        full_url = urljoin(base_url, line)
                    else:
                        full_url = line

                    ts_urls.append(full_url)

        # Save the .ts URLs to a .txt file
        with open(output_txt, 'w') as txt_file:
            for url in ts_urls:
                txt_file.write(url + '\n')

        print(f"Extracted {len(ts_urls)} .ts URLs and saved them to {output_txt}")
        return ts_urls

    except Exception as e:
        print(f"Failed to extract .ts URLs: {e}")
        return None

def get_base_url(m3u8_url):
    parsed_url = urlparse(m3u8_url)
    base_path = '/'.join(parsed_url.path.split('/')[:-1]) + '/'
    return parsed_url.scheme + '://' + parsed_url.netloc + base_path

def download_ts_files(ts_urls, folder):
    os.makedirs(folder, exist_ok=True)
    for url in ts_urls:
        try:
            filename = os.path.join(folder, os.path.basename(url))
            print(f"Downloading {filename}...")
            response = requests.get(url, stream=True)
            response.raise_for_status()
            
            with open(filename, 'wb') as file:
                for chunk in response.iter_content(chunk_size=8192):
                    file.write(chunk)
            
            print(f"Downloaded {filename} successfully.")
        except Exception as e:
            print(f"Failed to download {url}: {e}")

def create_ffmpeg_file_list(ts_urls, folder):
    list_file_path = os.path.join(folder, "file_list.txt")
    with open(list_file_path, 'w') as file:
        for url in ts_urls:
            # Extract only the local filename without the folder path
            local_filename = os.path.basename(url)
            file.write(f"file '{local_filename}'\n")
    print(f"Created FFmpeg file list at {list_file_path}")
    return list_file_path

def combine_ts_files_ffmpeg(file_list_path, output_file):
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    os.system(f"ffmpeg -f concat -safe 0 -i \"{file_list_path}\" -c copy \"{output_file}\"")
    print(f"Combined .ts files into {output_file}")

def cleanup_ts_files(ts_folder):
    for ts_file in os.listdir(ts_folder):
        if ts_file.endswith('.ts'):
            os.remove(os.path.join(ts_folder, ts_file))
    print("All .ts files have been deleted.")

if __name__ == "__main__":

    # Prompt user for m3u8 URL and output file name
    m3u8_url = input("Enter the .m3u8 URL: ").strip()
    output_file_name = input("Enter output file name (with extension, e.g., video.mp4): ").strip() or "combined_video.mp4"
    
    output_folder = "output_video"
    temp_folder = "temp_files"
    os.makedirs(output_folder, exist_ok=True)
    os.makedirs(temp_folder, exist_ok=True)
    
    # Ensure unique output file name
    output_file_name = get_unique_filename(output_folder, output_file_name)
    
    # Get base URL and download .m3u8 file
    base_url = get_base_url(m3u8_url)
    m3u8_file = download_m3u8_file(m3u8_url, temp_folder)

    if m3u8_file:
        # File to save the .ts URLs list
        ts_urls_txt = os.path.join(temp_folder, "ts_urls_list.txt")

        # Extract and save .ts URLs to the .txt file
        ts_urls = extract_ts_urls_from_m3u8(m3u8_file, base_url, ts_urls_txt)

        if ts_urls:
            download_ts_files(ts_urls, temp_folder)

            ffmpeg_file_list = create_ffmpeg_file_list(ts_urls, temp_folder)
            
            output_video_file = os.path.join(output_folder, output_file_name)
            combine_ts_files_ffmpeg(ffmpeg_file_list, output_video_file)
            
            cleanup_ts_files(temp_folder)

