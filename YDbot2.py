import asyncio
from balethon import Client
from balethon.objects import InlineKeyboard, InlineKeyboardButton
import numpy as np
import os
from pathlib import Path
import yt_dlp
import subprocess
import json
import glob
import itertools
from datetime import datetime
import pandas as pd

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

# configs = {}


# resualt = 1

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



async def make_progress_spinner(message, stop_event=False):
    
    msg = await Client.send_message(message.chat.id,
                              message_id=message.id,
                              text='⠋')
    
    for char in itertools.cycle('⠋⠙⠹⠼⠴⠦⠧⠏'):
    
        if not stop_event:
            
            try:
                await msg.edit_text(text=f"⏳ *در حال جستوجو*...{char}")
            except:
                pass
            await asyncio.sleep(0.3)
        
        else:
            
            await msg.delete()



def make_progress_hook(status_message, bot_loop):
    """Returns a sync hook that edits `status_message` with a progress bar."""
    last_percent = -1
    
    def make_progress_bar(percent, length=17):
        filled = int(length * percent // 100)
        bar = '▓' * filled + '▒' * (min(2, length - filled)) + '░' * max(0, length - filled - 2)
        return f"┃{bar}┃ {percent:.1f}%"

    def hook(d):
        nonlocal last_percent
        if d['status'] != 'downloading':
            return

        total = d.get('total_bytes')
        downloaded = d.get('downloaded_bytes', 0)

        if total and total > 0:
            percent = downloaded / total * 100
            int_percent = int(percent)
            if int_percent == last_percent:
                return
            last_percent = int_percent
            bar_line = make_progress_bar(percent)
            
            speed = d.get('_speed_str', 'N/A')
            eta = d.get('_eta_str', 'N/A')
            text = f"📥 در حال آپلود...\n{bar_line}\n⚡ {speed}"

            # Schedule the edit in the bot's event loop (thread-safe)
            asyncio.run_coroutine_threadsafe(
                status_message.edit_text(text),
                bot_loop
            )
        
        else:
            
            asyncio.run_coroutine_threadsafe(
                status_message.edit_text('✅ فایل آپلود شد'),
                bot_loop
            )

        

    return hook
        
    
    
async def download_youtube(queue, message, url, title):
    
    downloads_path = Path.home() / "Downloads" / "tmp"
    
    # [lambda d: print(f"\rDownloading: {d['_percent_str']} of {d['_total_bytes_str']}", end="") if d['status'] == 'downloading' else None]
    # hook = make_progress_hook()
    
    msg = await client.send_message(message.chat.id,
                                        text='در حال دریافت لینک')
    
    loop = asyncio.get_running_loop()
    
    ydl_opts = {
        'format': 'bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/best[height<=480][ext=mp4]',           # Best MP4 with audio
        'outtmpl': f"{downloads_path}/{title}.mp4",
        'progress_hooks': [make_progress_hook(msg, loop)],
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
        print('Upload date',info.get('upload_date'))
        
        
    
        
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
    
    
    
    
async def yt_download(message, url_vid, new_title, video_size):

    queue = asyncio.Queue()
    await asyncio.gather(download_youtube(queue, message, url_vid, new_title), 
                        split_video_by_size(queue, video_size),
                        upload_video(queue, message))

    
@client.on_message()
async def command_handler(message):
    
    global users_query, target_size_mb
    
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
            # message_id = message.id
            
            
            # [a,b] = users_query[users_query['user_id'] == str(user_id)]['band'].to_list()[0]
            
            # print(a,b)
            
            try:
                # users_query = users_query[users_query['user_id'] != f'{user_id}']
                users_settings.pop(user_id)
            
            except KeyError:
                pass
            
            await asyncio.create_task(make_progress_spinner(message,False))
            
            await yt_search(user_id, query_title, 50, 0, 5)
            
            await asyncio.create_task(make_progress_spinner(message,True))
            
            # btn_0 = InlineKeyboardButton(text="⬇️ مرتبط ترین 🎥 ",callback_data='most')
            # btn_1 = InlineKeyboardButton(text="⬇️ جدید ترین 🎥 ",callback_data='new')
                
            # keyboard = InlineKeyboard()
            # keyboard.add_row(btn_0,btn_1)
        
            # await message.reply('میخوای جدیدترین ویدیو رو دانلود کنم یا مرتبط ترین رو',
            #                     reply_markup=keyboard)
            
            
            # key = {
            #     # 'user_id': message.author.id,
            #     'message_id': str(message.id),
            #     'query': yt_search,
            #     'query_time': datetime.now().strftime("%H%M%S%f"),
            #     'info': ''
            # }
            # configs.append(key)
            # configs[str(message.chat.id)] = yt_search
            
            print(f'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa {message.chat.id}')
            
            
            # loop = asyncio.get_event_loop()
            # query_search = await loop.run_in_executor(None, search_videos, yt_search, 10)
            
            # # print(query_search[1]['id'])
            
            # for i,query in enumerate(query_search):
                
            #     print(query['thumbnail'])
                
            #     btn = InlineKeyboardButton(text="⬇️ Download 🎥 ",callback_data='btn')
                
            #     keyboard = InlineKeyboard()
            #     keyboard.add_row(btn)
                
            #     # await client.send_message(message.chat.id,f'{i}: {query['id']} , {query['title']} , {query['url']}' )
            #     await client.send_photo(message.chat.id,query['thumbnail'],
            #                             f'نام: {query['title']} 🎬 \
            #                             چنل: {query['channel']} 🌐 \
            #                             مدت زمان: {query['duration']} ⏰ \
            #                             بارگذاری: {query['uplad_date']} 📥',
            #                             reply_markup=keyboard)

    elif message.text.startswith('https://www.youtube.com/'):
        
        downloads_path =  Path.home() / "Downloads" / "tmp"
    
        if Path.exists(downloads_path):
            
            pass
        
        else:
            Path.mkdir(downloads_path)
    
                
        url_vid = message.text
        
        print(url_vid)
        
        # processing_msg = await message.reply("بزار ببینم چی میشه 😜 ")
        # await processing_msg.edit_text('داره دانلود میشه')
        
        user_id = message.chat.id
        msg_id = message.id
        
        # define new title with message chat id and message id
        new_title = f'{str(user_id)}_{str(msg_id)}'
        
        # video_path , title = download_youtube(url_vid,new_title)
        
        # input_file = f"{video_path}/{new_title}.mp4"
        # output_pat = f"{downloads_path}/{new_title}___part_%03d.mp4"
        
        try:
            
            # users_query = users_query[users_query['user_id'] != f'{user_id}']
            users_settings.pop(user_id)
            
            
        except KeyError:
            
            pass
        
        await yt_download(message, url_vid, new_title, target_size_mb)
        print('hhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhh',len(users_settings))

        
        # queue = asyncio.Queue()
        # await asyncio.ghater(download_youtube(queue,url_vid,new_title), 
        #                     split_video_by_size(queue, client.target_size_mb),
        #                     upload_video(queue, message))
        
        
        # os.system(f'mv {video_path}/NA.mp4 {video_path}/{new_title}.mp4')
        
        # print(f'ggggggggggggggggggggggg {title} {video_path} {new_title}')
        
        # video_path , title = ["/home/amad","2026-04-07-03-09-32"]
        # video_path , title = download_youtube(url[1])
        # print('Fully succuss downloads :)')
        
        
        
        # safe_chars = re.compile(r'[<>:"/\\|?*]')
        
        # os.system(f'mv {video_path}/{title}.mp4 {video_path}/{new_title}.mp4')


        
        # input_file = f"{video_path}/{new_title}.mp4"
        # output_pat = f"{downloads_path}/{new_title}___part_%03d.mp4"
        # # target_size_mb = 15
        
        # # split_video_by_size(input_file, output_pat, target_size_mb=50)
        
        # loop = asyncio.get_event_loop()
        # await loop.run_in_executor(None, split_video_by_size, input_file, output_pat, client.target_size_mb )

        # lst = glob.glob(f'{downloads_path}/{new_title}___part_*.mp4')
        
        # print(lst)
        
        
        # await message.reply(" دارم ویدیوی مورد علاقه شما رو آپلود میکنم 😋")

        # print(f"Received message from {message.author.first_name}: {message.text}")

        # # filename = "/home/amad/Downloads/v1.mp4"
        
        # await message.reply(f"تعداد پارت های ویدیو {len(lst)}")
        
        # for i in range(len(lst)):
            
        #     vid_pth = f'{downloads_path}/{new_title}___part_{i:03d}.mp4'
            
        #     print(vid_pth)
            
        #     for count in range(10):
                
        #         try:
                    
        #             print(f'Try {count+1} to Send {vid_pth}')
                    
        #             with open(vid_pth, "rb") as video_file:
                    
        #                 await client.send_video(message.chat.id,
        #                     video=video_file,
        #                     caption=f"پارت {i+1} \n{title}.mp4 👍"
        #                 )
                        
                    
        #             print("Send Successfully")
                                
        #             os.remove(f'{downloads_path}/{new_title}___part_{i:03d}.mp4')
                    
                
        #             break

                
        #         except FileNotFoundError:
        #             print(f"Send Successfully : {title}")
        #             # await message.reply("Send Successfully")
        #         except Exception as e:
        #             print(f"Sorry i dont Send query : {e}")
        #             await asyncio.sleep(2)
        #             # await message.reply("نتونستم درخواست شما رو انجام بدم 🥵")
        #             # os.remove(f'{downloads_path}/{new_title}___part_{i:03d}.mp4')
                    
        #     if (count >= 9):
                
        #         await message.reply("نتونستم درخواست شما رو انجام بدم 🥵")
        #         os.remove(f'{downloads_path}/{new_title}___part_{i:03d}.mp4')
                
        #     await asyncio.sleep(1)
            
            
                
        # # org_vid_pth = "Downloads" / f"{title}.mp4"
        
        # os.remove(f"{downloads_path}/{new_title}.mp4")
                
            
                
        # await message.reply(f'کل ویدیوی دلخواهتو گرفتم 🥳 \n{title}')
        # await client.send_message(message.chat.id,"😍")
        
            
    elif message.text.startswith('/help'):
        
        await client.send_message(message.chat.id,f'/strat : welcom to your bot \
                                                    /s <size parts> \
                                                    /d <video address> \
                                                    ')
        
@client.on_callback_query()
async def handle_callback(callback_query):
        global users_settings
        
        # print(users_query)
    # if callback_query.data == "help_pressed":
        # await callback_query.message.reply(f'{user_id}_{random()}')
        # await callback_query.answer("Help shown!")  # Acknowledge the button press
     
        # print(configs[callback_query.chat_instance])
        
        # user_id = callback_query.chat_instance
        # message_id = configs[callback_query.chat_instance]['message_id']
        # query_title = configs[callback_query.chat_instance]['query']
        
    
        # if (callback_query.data == 'most'):
            
        #     search_type = False
            
        #     print('fgffgg')
        #     await yt_search(user_id, message_id, query_title, 10)
            
        if (callback_query.data.startswith('D')):
            
            str = callback_query.data[1:].split(".")
            user_id = callback_query.message.chat.id
            id = str[1]
            
            # nonlocal users_query
            # print(user_id,id)
            # print(users_settings[user_id])
                        
                        
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
            
            # await yt_search(user_id, message_id, '', 50, a, b)

                        
            
        # query_info = await asyncio.to_thread(search_videos, query_search, 6, 'search_type')
        
        # print(query_info)
        
        # global ttt
        # ttt = await asyncio.to_thread(test,ttt)
        
        # await send_info_query(callback_query.chat_instance, configs[callback_query.chat_instance])
        
        # for i,query in enumerate(configs[callback_query.chat_instance]['info']):
            
        #     # print(query['thumbnail'])
            
        #     btn = InlineKeyboardButton(text="⬇️ Download 🎥 ",callback_data=f'{callback_query.chat_instance}_{query['info']['message_id']}')
            
        #     keyboard = InlineKeyboard()
        #     keyboard.add_row(btn)
            
        #     # await client.send_message(message.chat.id,f'{i}: {query['id']} , {query['title']} , {query['url']}' )
        #     await client.send_photo(callback_query.chat_instance,query['thumbnail'],
        #                             f'نام: {query['info']['title']} 🎬 \
        #                             چنل: {query['info']['channel']} 🌐 \
        #                             مدت زمان: {query['info']['duration']} ⏰ \
        #                             بارگذاری: {query['info']['upload_date']} 📥',
        #                             reply_markup=keyboard)
        
# Start the bot (this runs an infinite polling loop)
if __name__ == "__main__":
    print("Bot is running...")
    client.run()
