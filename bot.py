import os
import shutil
import zipfile
import asyncio
import httpx
from balethon import Client
from balethon.objects import Message

# --- Configuration ---
TEMP_DIR = "temp_files"
EXTRACT_DIR = "tmp"
CHUNK_SIZE = 15 * 1024 * 1024  # 10 MB in bytes

TOKEN = input("Please enter BOT TOKEN:\n")
bot = Client(TOKEN)

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

# --- Bot Commands ---

@bot.on_message()
async def handle_commands(message: Message):
    if message.text.startswith("/d"):
        await download_and_unzip(message)
    elif message.text.startswith("/u"):
        await split_and_upload(message)

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

    await status_msg.edit_text("✅ Downloaded and Extracted. Use /u to upload parts.")

async def split_and_upload(message: Message):
    status_msg = await message.reply("Preparing to split and upload...")
    
    # Create a full zip of the extracted folder first
    final_zip = "to_upload.zip"
    with zipfile.ZipFile(final_zip, 'w', zipfile.ZIP_DEFLATED) as z:
        for root, dirs, files in os.walk(EXTRACT_DIR):
            for file in files:
                z.write(os.path.join(root, file), 
                        os.path.relpath(os.path.join(root, file), EXTRACT_DIR))

    # Split into 10MB parts
    file_size = os.path.getsize(final_zip)
    part_num = 1
    
    with open(final_zip, "rb") as f:
        while True:
            chunk = f.read(CHUNK_SIZE)
            if not chunk:
                break
            
            part_name = f"part_{part_num}.zip"
            with open(part_name, "wb") as chunk_file:
                chunk_file.write(chunk)
            
            # Upload part
            await status_msg.edit_text(f"Uploading part {part_num}...")
            await bot.send_document(message.chat.id, part_name)
            
            os.remove(part_name) # Remove part after upload
            part_num += 1

    # Cleanup
    await status_msg.edit_text("🧹 Cleaning up temporary files...")
    if os.path.exists(TEMP_DIR): shutil.rmtree(TEMP_DIR)
    if os.path.exists(EXTRACT_DIR): shutil.rmtree(EXTRACT_DIR)
    if os.path.exists(final_zip): os.remove(final_zip)
    
    await status_msg.edit_text("✨ Task completed and temporary files deleted.")

if __name__ == "__main__":
    print("Bot is running...")
    bot.run()
