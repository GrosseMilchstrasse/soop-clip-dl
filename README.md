# Soop clipped from vod download

## Introduction

This project is a Python program that allows users to clip and download `.m4s` video segments from a `.m3u8` playlist URL from **https://www.sooplive.co.kr/**, combine them into a single video file. This is particularly useful for handling media files from streaming services that deliver content as multiple small segments.

## How to Use

This guide provides instructions on setting up the program for beginners, including installing Python, creating a virtual environment, and installing the necessary packages or you can JUST RUN IT because this only use common dependencies.

### Prerequisites

1. **Python 3.7+**: Ensure you have Python installed on your system. You can download it from [Python's official website](https://www.python.org/downloads/).

2. **FFmpeg**: The program uses FFmpeg to download edited m3u8

3. **m3u8**: To find m3u8 url you can use browser add on and find something like this "https://vod-archive-global-cdn-z02.sooplive.co.kr/spkt/vod/..._1_.mp4/manifest.m3u8?cv=v1"

### Step-by-Step Setup

Follow these steps to set up and run the project.

1. **Clone the Repository**

   Clone this repository to your local machine.
   ```bash
   git clone https://github.com/GrosseMilchstrasse/soop-vod-dl.git
   cd soop-vod-dl
   ```
   Alternatively, you can download it as a ZIP file and extract it.

2. **Create a Virtual Environment**

    It’s recommended to use a virtual environment to manage dependencies. In the project folder, create and activate a virtual environment:
    ```bash
    python -m venv myenv
    source myenv/bin/activate

    # For Windows
    python -m venv myenv
    myenv\Scripts\activate

    # For macOS/Linux
    python3 -m venv myenv
    source myenv/bin/activate

3. **Install Depedencies**

    Install the required libraries specified in requirements.txt:
   
       pip install -r requirements.txt

5. **Running the Program**

    python main.py

    When prompted, enter the .m3u8 URL. The program will:

      Download each .ts segment from the playlist.
      Combine the segments into a single .mp4 video file.
      Delete the temporary .ts files after combining.

    Example of Usage:

   1. Run the Program:

            python main.py
        
   2. Enter your .m3u8 url when prompted:

            Enter the .m3u8 URL: https://example.com/path/to/video.m3u8

   3. The combined video file will be saved in the output directory, ready to play.

6. **Advance and Optional**

    You can update to your own path for ouput folder

7. **Additional Notes**

    - FFmpeg Path: Ensure FFmpeg is added to your system’s PATH, so the command ffmpeg works from the terminal. If not, refer to the FFmpeg documentation to set it up.

    - Python Dependencies: All dependencies are listed in requirements.txt. If you install additional packages, remember to update requirements.txt with pip freeze > requirements.txt.

**License**
This `README.md` provides a beginner-friendly guide for installing and using the program, from setting up a virtual environment to running the code. Let me know if you'd like to adjust any part of it!

