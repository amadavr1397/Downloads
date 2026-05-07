import asyncio
from balethon import Client
from balethon.objects import Message
from balethon.objects import InlineKeyboard, InlineKeyboardButton
import numpy as np
import os
from pathlib import Path
import yt_dlp
import subprocess
import json
import glob
# import re
from datetime import datetime
# import time
import pandas as pd
import math
import shutil
import zipfile
import httpx

users_query = pd.DataFrame()

users_settings = {}

# users_band = pd.DataFrame({
#             'user_id': '',
#             'band': [0,5],
#     })


BOT_TOKEN = input(f"Enter a TOKEN : \n")

# Create the client instance
client = Client(BOT_TOKEN)

target_size_mb = 10

TEMP_DIR = "temp_file"
EXTRACT_DIR = "extracted_file"
CHUNK_SIZE = 10 * 1024 * 1024

# --- Helper Functions ---
def progress_bar(current, total, length=10):
    """Generates a visual progress bar string."""
    percent = current / total
    filled_length = int(length * percent)
    bar = "■" * filled_length + "□" * (length - filled_length)
    return f"[{bar}] {percent:.1%}"

async def update_progress(message: Message, text: str, current, total):
    """Updates the message with the current progress."""
    bar = progress_bar(current, total)
    try:
        # await asyncio.sleep(1)
        await message.edit_text(f"{text}\n{bar}")
    except Exception:
        pass  # Avoid flooding with edit errors if content is same


async def download_and_unzip(message: Message):
    # Extract URL from command: /d https://github.com/...
    args = message.text.split(" ", 1)
    file_name = message.text.split('/')[-1]
    if len(args) < 2:
        return await message.reply("Please provide a GitHub URL: `/d [url]`")
    
    url = args[1]
    zip_path = os.path.join(TEMP_DIR, file_name)
    
    if not os.path.exists(TEMP_DIR):
        os.makedirs(TEMP_DIR)

    status_msg = await message.reply("Initializing download...")

    # 1. Download with progress
    async with httpx.AsyncClient() as client:
        async with client.stream("GET", url, follow_redirects=True) as response:
            total_size = int(response.headers.get("Content-Length", 0))
            downloaded = 0
            
            with open(zip_path, "wb") as f:
                async for chunk in response.aiter_bytes():
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0:
                        await update_progress(status_msg, "Downloading...", downloaded, total_size)

    # 2. Unzip with progress
    await status_msg.edit_text("Extracting files...")
    if not os.path.exists(EXTRACT_DIR):
        os.makedirs(EXTRACT_DIR)

    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        all_files = zip_ref.namelist()
        total_files = len(all_files)
        for i, file in enumerate(all_files, 1):
            zip_ref.extract(file, EXTRACT_DIR)
            if i % 5 == 0 or i == total_files: # Update every 5 files to avoid rate limits
                await update_progress(status_msg, "Extracting...", i, total_files)
                
                
    btn = InlineKeyboardButton(text=" ⬇️ Download ",callback_data=f'U{zip_path}')
    keyboard = InlineKeyboard()
    keyboard.add_row(btn)

    await status_msg.edit_text("✅ Downloaded and Extracted. Use this button to upload parts.", reply_markup=keyboard)

async def split_and_upload(message: Message, final_zip):
    status_msg = await message.reply("Preparing to split and upload...")
    
    # Create a full zip of the extracted folder first
    # final_zip = "to_upload.zip"
    with zipfile.ZipFile(final_zip, 'w', zipfile.ZIP_DEFLATED) as z:
        for root, dirs, files in os.walk(EXTRACT_DIR):
            for file in files:
                z.write(os.path.join(root, file), 
                        os.path.relpath(os.path.join(root, file), EXTRACT_DIR))

    # Split into 10MB parts
    file_size = os.path.getsize(final_zip)
    name = final_zip.split('/')[-1].split('.')[0]
    part_num = 1
    
    with open(final_zip, "rb") as f:
        while True:
            chunk = f.read(CHUNK_SIZE)
            if not chunk:
                break
            
            part_name = f"{name}_part_{part_num}.zip"
            with open(part_name, "wb") as chunk_file:
                chunk_file.write(chunk)
            
            # Upload part
            await status_msg.edit_text(f"Uploading part {part_num}...")
            await client.send_document(message.chat.id, part_name)
            
            # os.remove(part_name) # Remove part after upload
            part_num += 1

    # Cleanup
    await status_msg.edit_text("🧹 Cleaning up temporary files...")
    if os.path.exists(TEMP_DIR): shutil.rmtree(TEMP_DIR)
    if os.path.exists(EXTRACT_DIR): shutil.rmtree(EXTRACT_DIR)
    if os.path.exists(final_zip): os.remove(final_zip)
    
    await status_msg.edit_text("✨ Task completed and temporary files deleted.")

async def download_and_split_link(message, size):
    
    lnk = message.text.split(' ', 1)
    name = message.text.split('/',-1).split('.',0)
    typ  = message.text.split('/',-1).split('.',-1)
    folder = f"{message.chat.id}_{message.id}_file"
    
    if Path.exists(f'{folder}_file'):
        pass
    else:
        Path.mkdir(f'{folder}_file')
    
    if Path.exists('splited_parts'):
        pass
    else:
        Path.mkdir('splited_parts')
    
    try:
            os.system(f'wget {lnk} -O {folder}/{name}.{typ}')
            os.system(f"zip -s {size}m -r splited_parts/{name}.{typ} {folder}/{name}.{typ}")
            
    except Exception as e:
        
            print(e)

def get_video_info(input_path):
    """Retrieve duration and total bitrate using ffprobe."""
    cmd = [
        'ffprobe', '-v', 'error', '-show_entries',
        'format=duration,bit_rate', '-of', 'json', input_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {result.stderr}")
    
    data = json.loads(result.stdout)
    fmt = data['format']
    duration = float(fmt['duration'])
    bitrate = int(fmt.get('bit_rate', 0))
    
    # If bitrate not reported, calculate from file size and duration
    if bitrate == 0:
        file_size = os.path.getsize(input_path)
        bitrate = int((file_size * 8) / duration)
    
    return duration, bitrate

    
async def search_query(queue, user_id, search, number=5, a=0, b=5):
    """
    Synchronous search – returns list of dicts with 'id', 'title', 'channel', etc.
    Runs in a thread to avoid blocking the bot.
    """
    global users_query, users_settings
    # global users_band
    
    if search != "":
        ydl_opts = {
            'quiet': True,
            'skip_download': True,
            'extract_flat': True,   # fast, no full extraction
            # 'js_runtime': '/root/node-v22.14.0-linux-x64/bin/node',
            'cookiefile': 'YTDLnis_Cookies.txt',
        }
        
        
        prefix = "ytsearch" 
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"{prefix}{number}:{search}", download=False)
            entries = info.get('entries', [])
                
        tmp = []
        
        for e in entries:
            
            tmp.append(e.get('id'))
            
        users_settings[user_id] = {
                    'band': [a,b],
                    'id_vid': tmp,
                    'msg_id': []
                }
        
        os.system(f'printf "{users_settings}" > set.txt')
        print(users_settings)
        print(len(users_settings))
        
  
        
        
        try:
            
            users_query = users_query[users_query['user_id'] != f'{user_id}']
            
        except:
            
            pass
        
        
        ydl_opts = {
                'quiet': True,
                'skip_download': True,
                'remote_components': ['ejs:github'],
                'cookiefile': 'YTDLnis_Cookies.txt',
                'js_runtime': 'deno',
        }
        
        tmp = []
        
        for id in users_settings[user_id]['id_vid'][a:b]:
            
            print('rrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrr',user_id,id)
            
         
            url_vid = f"https://www.youtube.com/watch?v={id}"
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info =  ydl.extract_info(url_vid, download=False)
                
                
            title = info.get('title', 'N/A')
            upload_date = info.get('upload_date')
            if upload_date:
                dt = datetime.strptime(upload_date, '%Y%m%d')
                formatted_date = dt.strftime('%d %B %Y')
            else:
                formatted_date = 'Unknown'
            channel = info.get('channel')
            duration = info.get('duration_string', '?')
            views = info.get('view_count', 0)
            likes = info.get('like_count')
            thumbnail = f"https://i.ytimg.com/vi/{id}/hqdefault.jpg"               
            description = (info.get('description') or '')[:50]

            
            
            tmp.append(
                {
                    'user_id': f'{user_id}',
                    'id': id,
                    'title': title,
                    'upload_date': formatted_date,
                    'channel': channel,
                    'duration': duration,
                    'views': views,
                    'likes': likes,
                    'thumbnail': thumbnail,
                    'description': description
                    
                })
        
        tmp = pd.DataFrame(tmp)
        users_query = pd.concat([users_query, tmp], ignore_index=True)
        
        print(users_query[users_query['user_id'] == f'{user_id}'])
            
            
            
        data = users_query[users_query['user_id'] == f'{user_id}']
        await queue.put([search, data])
        
    else:
        
        try:
            
            users_query = users_query[users_query['user_id'] != str(user_id)]
            
        except:
            
            pass
        
        
        ydl_opts = {
                'quiet': True,
                'skip_download': True,
                'remote_components': ['ejs:github'],
                'cookiefile': 'YTDLnis_Cookies.txt',
                'js_runtime': 'deno',
        }
        
        tmp = []
        
        for id in users_settings[user_id]['id_vid'][a:b]:
        
        
            url_vid = f"https://www.youtube.com/watch?v={id}"
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info =  ydl.extract_info(url_vid, download=False)
                
                
            title = info.get('title', 'N/A')
            upload_date = info.get('upload_date')
            if upload_date:
                dt = datetime.strptime(upload_date, '%Y%m%d')
                formatted_date = dt.strftime('%d %B %Y')
            else:
                formatted_date = 'Unknown'
            channel = info.get('channel')
            duration = info.get('duration_string', '?')
            # views = info.get('view_count', 0)
            # likes = info.get('like_count')
            thumbnail = f"https://i.ytimg.com/vi/{id}/hqdefault.jpg"               
            # description = (info.get('description') or '')[:50]

            
            
            tmp.append(
                {
                    'user_id': f'{user_id}',
                    'id': id,
                    'title': title,
                    'upload_date': formatted_date,
                    'channel': channel,
                    'duration': duration,
                    # 'views': views,
                    # 'likes': likes,
                    'thumbnail': thumbnail,
                    # 'description': description
                    
                })
    
        tmp = pd.DataFrame(tmp)
        users_query = pd.concat([users_query, tmp], ignore_index=True)
        
        
        data = users_query[users_query['user_id'] == f'{user_id}']
        await queue.put([search, data])
    
    
    
    
async def send_query(queue, user_id):
    

    items = await queue.get()
    search = items[0]
    usr_query = items[1]
    # usr_query = users_query[users_query['user_id'] == str(user_id)]
    
    # print(usr_query)
    
    tmp_msg = []
    
    
    for index in range(len(usr_query)):
            
        query = usr_query.iloc[index]
        
        btn = InlineKeyboardButton(text=" ⬇️ Download 🎥 ",callback_data=f'D{user_id}.{query['id']}')
        
        keyboard_ = InlineKeyboard()
        keyboard_.add_row(btn)
        
        
        try:
            msg_id = await client.send_photo(user_id,query['thumbnail'],
                                f"🎬 نام: {query['title']}  \
                                🌐 چنل: {query['upload_date']}  \
                                ⏰ مدت زمان: {query['duration']}",
                                reply_markup=keyboard_)
            
            tmp_msg.append(msg_id)
            # users_settings[user_id]['msg_id'] = msg_id
            
        except Exception as e:
            
            print(f'It has Error {e}')
            
            msg_id = await client.send_message(user_id,
                                f'🎬 نام: {query['title']}  \
                                🌐 چنل: {query['channel']}  \
                                ⏰ مدت زمان: {query['duration']} ',
                                reply_markup=keyboard_)
            
            tmp_msg.append(msg_id)
            # users_settings[user_id]['msg_id'] = msg_id
    
    
        
    mor = InlineKeyboardButton(text="بیشتر",callback_data=f'M{user_id}')

    keyboard = InlineKeyboard()
    keyboard.add_row(mor)
    

    try:
        msg_id = await client.send_message(user_id,
                            'جستوجوی بیشتر',
                            reply_markup=keyboard)
        
        tmp_msg.append(msg_id)
        # users_settings[user_id]['msg_id'] = msg_id
            
    except Exception as e:
        
        print(f'It has Error {e}')
        
    
    users_settings[user_id]['msg_id'] = tmp_msg  
   
    
async def yt_search(user_id, query_title, number=5, a=0, b=5):
    
    queue = asyncio.Queue()
    await asyncio.gather(search_query(queue, user_id, query_title, number, a, b),
                        send_query(queue, user_id))
    
    
    
async def download_youtube(queue, url, title):
    
    downloads_path = Path.home() / "Downloads" / "tmp"
    
    ydl_opts = {
        'format': 'bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/best[height<=480][ext=mp4]',           # Best MP4 with audio
        'outtmpl': f"{downloads_path}/{title}.mp4",
        'progress_hooks': [lambda d: print(f"\rDownloading: {d['_percent_str']} of {d['_total_bytes_str']}", end="") if d['status'] == 'downloading' else None],
        'noplaylist': True,
        'quiet': False,
        'no_warnings': True,
        'cookiefile': 'YTDLnis_Cookies.txt',
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        print(f"Title: {info.get('title')}")
        print(f"Duration: {info.get('duration_string')}")
        print(f"Saving to: {downloads_path}")
        print('dddddddddddddddddddddddddddddddddddddddddddddddddddd',info.get('upload_date'))
        
        
        

        # caption = (
        #     f"🎬 <b>{title}</b>\n"
        #     f"📅 Uploaded: {formatted_date}\n"
        #     f"⏱ Duration: {duration}\n"
        #     f"👁 Views: {views:,}\n"
        #     f"❤️ Likes: {likes_str}\n\n"
        #     f"📄 {description}..."
        # )
        
        

        ydl.download([url])
        print("\n✅ Download complete!")
        
        print(f"\n✅ Downloaded: {downloads_path}")
        
        orginal_title = info.get('title')
        await queue.put([downloads_path, title, orginal_title])
        
        
    
async def split_video_by_size(queue, target_size_mb, safety_factor=0.98):
    """
    Split a video into segments of approximately target_size_mb each.
    
    :param input_path: Path to the input video file.
    :param output_pattern: Pattern for output files (e.g., 'output_%03d.mp4').
    :param target_size_mb: Desired size of each segment in megabytes.
    :param safety_factor: Fraction of target size to use for duration calculation
                          (prevents overshoot due to bitrate variations).
    """
    items = await queue.get()
    downloads_path = items[0]
    title = items[1]
    input_path     = f'{downloads_path}/{title}.mp4'
    output_pattern = f'{downloads_path}/{title}___part_%03d.mp4'
    orginal_title  =    items[2]
    
    # Get video duration and bitrate
    duration, bitrate = get_video_info(input_path)
    target_size_bytes = target_size_mb * 1024 * 1024
    
    # Calculate segment duration (in seconds) needed to reach the target size
    # bitrate is in bits/second → bytes per second = bitrate / 8
    segment_duration = (target_size_bytes * safety_factor) / (bitrate / 8)
    
    # Ensure segment duration does not exceed total duration
    segment_duration = min(segment_duration, duration)
    
    print(f"Video duration: {duration:.2f} s, bitrate: {bitrate/1000:.0f} kbps")
    print(f"Target segment size: {target_size_mb} MB → segment duration: {segment_duration:.2f} s")
    
    # Build FFmpeg command
    cmd = [
        'ffmpeg', '-i', input_path,
        '-c', 'copy',          # No re-encoding
        '-map', '0',           # Include all streams
        '-f', 'segment',
        '-segment_time', str(segment_duration),
        '-reset_timestamps', '1',
        output_pattern
    ]
    
    print("Running FFmpeg...")
    subprocess.run(cmd, check=True)
    print("Splitting completed.")
    
    await queue.put([downloads_path, title, orginal_title])
    

async def upload_video(queue, message):
    
    items = await queue.get()
    downloads_path  = items[0]
    title           = items[1]
    orginal_title   = items[2]
    
    pattern = f'{downloads_path}/{title}'
    
    
    lst = glob.glob(f'{pattern}___part_*.mp4')
        
    print(lst)
        
        
    await message.reply(" دارم ویدیوی مورد علاقه شما رو آپلود میکنم 😋")

    print(f"Received message from {message.author.first_name}: {message.text}")

        
    await message.reply(f"تعداد پارت های ویدیو {len(lst)}")
        
    for i in range(len(lst)):
        
        vid_pth = f'{pattern}___part_{i:03d}.mp4'
        
        print(vid_pth)
        
        for count in range(10):
            
            try:
                
                print(f'Try {count+1} to Send {vid_pth}')
                
                with open(vid_pth, "rb") as video_file:
                
                    await client.send_video(message.chat.id,
                        video=video_file,
                        caption=f"پارت {i+1} \n{orginal_title}.mp4 👍"
                    )
                    
                
                print("Send Successfully")
                            
                os.remove(f'{pattern}___part_{i:03d}.mp4')
                
            
                break

            
            except FileNotFoundError:
                print(f"Send Successfully : {orginal_title}")
                # await message.reply("Send Successfully")
            except Exception as e:
                print(f"Sorry i dont Send query : {e}")
                await asyncio.sleep(2)
                # await message.reply("نتونستم درخواست شما رو انجام بدم 🥵")
                # os.remove(f'{downloads_path}/{new_title}___part_{i:03d}.mp4')
                
        if (count >= 9):
            
            await message.reply(f"نتونستم پارت {i:03d} بفرستم 🥵")
            os.remove(f'{pattern}___part_{i:03d}.mp4')
            
        await asyncio.sleep(1)
    
    
    await message.reply(f'کل ویدیوی دلخواهتو گرفتم 🥳 \n{orginal_title}')
    await client.send_message(message.chat.id,"😍")
    os.remove(f"{pattern}.mp4")
    
    print('hhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhh',len(users_settings))
    
    
    
async def yt_download(message, url_vid, new_title, video_size):

    queue = asyncio.Queue()
    await asyncio.gather(download_youtube(queue, url_vid, new_title), 
                        split_video_by_size(queue, video_size),
                        upload_video(queue, message))

    
@client.on_message()
async def command_handler(message):
    
    global users_query, target_size_mb, CHUNK_SIZE
    
    if message.text.startswith('/start'):
        
        await message.reply('Hello')
 
 
    
    elif message.text.startswith('/s'):
                
    
        if (len(message.text.split(' ')) == 2):
            
            # global target_size_mb
            target_size_mb = np.int32(message.text.split(' ')[1])
            
            await message.reply(f"Part size of videos is {target_size_mb}")
            
        elif (len(message.text.split(' ')) == 1):
            
            await message.reply(f"Part size of videos is {target_size_mb}")
            
            
            
            
    elif message.text.startswith('/yt'):
        
        if (len(message.text.split(' ')) >= 2):
            
            query_title = message.text.split(' ')[1:]
            user_id = message.chat.id
            
            try:
                # users_query = users_query[users_query['user_id'] != f'{user_id}']
                users_settings.pop(user_id)
            
            except KeyError:
                pass
            
            await yt_search(user_id, query_title, 50, 0, 5)
            
            print(f'USER {message.chat.id} Search the {query_title}')
            

    elif message.text.startswith('https://www.youtube.com/'):
        
        downloads_path =  Path.home() / "Downloads" / "tmp"
    
        if Path.exists(downloads_path):
            
            pass
        
        else:
            Path.mkdir(downloads_path)
    
                
        url_vid = message.text
        
        print(url_vid)
        
        processing_msg = await message.reply("بزار ببینم چی میشه 😜 ")
        await processing_msg.edit_text('داره دانلود میشه')
        
        user_id = message.chat.id
        msg_id = message.id
        
        # define new title with message chat id and message id
        new_title = f'{str(user_id)}_{str(msg_id)}'
        
        try:
            
            users_settings.pop(user_id)
            
            
        except KeyError:
            
            pass
        
        await yt_download(message, url_vid, new_title, target_size_mb)

            
    elif message.text.startswith('/help'):
        
        await client.send_message(message.chat.id,f"/strat : welcom to your bot \
                                                    /s <size parts> \
                                                    /d <Downloadable File Link: apk, zip, tar.gz, exe> \
                                                    /sz Size of file parts \
                                                    ")

    
    elif message.text.startswith("/d"):
        
        typ = message.text.split("/")[-1].split(".")[-1]
        print(typ)
        
        if typ == 'zip':
            await download_and_unzip(message)
            
        else:
            await download_and_split_link(message, CHUNK_SIZE)
    
    elif message.text.startswith("/sz"):
        
        CHUNK_SIZE = int(message.text.split(" ", 1))
        CHUNK_SIZE = CHUNK_SIZE * 1024 * 1024
        
        await message.reply(f'Size of parts: {CHUNK_SIZE}')
        
@client.on_callback_query()
async def handle_callback(callback_query):
        global users_settings
        
            
        if (callback_query.data.startswith('D')):
            
            str = callback_query.data[1:].split(".")
            user_id = callback_query.message.chat.id
            id = str[1]
            
                        
            url_vid = f"https://www.youtube.com/watch?v={id}"
            new_title = f"{user_id}_{id}"
            
            global target_size_mb
            await yt_download(callback_query.message, url_vid, new_title, target_size_mb)
            
            
        elif (callback_query.data.startswith('M')):
            
            user_id = callback_query.message.chat.id

            [a,b] = users_settings[user_id]['band']
            
            a = a + 5
            b = b + 5
            
            if (b > 50):
                
                a = 0; b = 5
            
            users_settings[user_id]['band'] = [a, b]
            
            
            print(user_id,a,b)
            
            
            await users_settings[user_id]['msg_id'][-1].delete()
            
            
            await yt_search(user_id, '', 50, a, b)
            

        elif (callback_query.data.startswith('U')):
        
            file_name = callback_query.data[1:]
            
            print(file_name)
        
            await split_and_upload(callback_query.message, file_name)

                        
           
# Start the bot (this runs an infinite polling loop)
if __name__ == "__main__":
    print("Bot is running...")
    client.run()
