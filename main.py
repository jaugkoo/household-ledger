import os
import time
import base64
import json
import logging
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from openai import OpenAI

# Setup logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')

# Load environment variables
load_dotenv()

OPEN_AI_API_KEY = os.getenv("OPEN_AI_API_KEY")
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")
WATCH_DIR = os.getenv("WATCH_DIR")

# Initialize OpenAI client
client = OpenAI(api_key=OPEN_AI_API_KEY)

# Keep track of processed files to avoid duplicates
PROCESSED_FILES = set()

def is_valid_image(filename):
    ext = os.path.splitext(filename)[1].lower()
    return ext in ['.jpg', '.jpeg', '.png', '.heic']

def process_file(filepath):
    if filepath in PROCESSED_FILES:
        return

    # Skip files older than 7 days
    try:
        mtime = os.path.getmtime(filepath)
        file_date = datetime.fromtimestamp(mtime)
        if datetime.now() - file_date > timedelta(days=7):
            PROCESSED_FILES.add(filepath)
            return
    except FileNotFoundError:
        return

    logging.info(f"Processing new file: {filepath}")
    PROCESSED_FILES.add(filepath)
    
    time.sleep(2) # Wait for sync
    
    try:
        receipt_data = analyze_receipt(filepath)
        if receipt_data and "items" in receipt_data:
             add_items_to_notion(receipt_data)
        else:
            logging.info("No items found in receipt.")
    except Exception as e:
        logging.error(f"Error processing {filepath}: {e}")

class ReceiptHandler(FileSystemEventHandler):
    def on_created(self, event):
        if not event.is_directory and is_valid_image(event.src_path):
            logging.info(f"Detected creation: {event.src_path}")
            process_file(event.src_path)

    def on_moved(self, event):
        if not event.is_directory and is_valid_image(event.dest_path):
            logging.info(f"Detected move/rename: {event.dest_path}")
            process_file(event.dest_path)

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def analyze_receipt(image_path):
    logging.info("Analyzing image with AI...")
    try:
        base64_image = encode_image(image_path)
    except Exception as e:
        logging.error(f"Failed to read image: {e}")
        return None

    # Prompt for itemized extraction
    prompt = """
    Analyze this receipt image and extract the following information.
    Return a JSON object with this structure:
    {
        "merchant": "Merchant Name",
        "date": "YYYY-MM-DD",
        "items": [
            {
                "name": "Item Name",
                "quantity": 1,
                "unit_price": 1000,
                "total_price": 1000,
                "category": "One of: 식재료, 가공식품, 간식, 채소, 과일, 생활용품, 기타"
            }
        ]
    }
    - "merchant": The store name.
    - "date": The transaction date.
    - "items": Array of purchased items.
    - "category": Infer the category based on the item name from the given list.
    - Remove currency symbols from prices.
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "You are a receipt scanner. Output only valid JSON."
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                    ]
                }
            ],
            response_format={"type": "json_object"}
        )
        
        content = response.choices[0].message.content
        if not content:
            return None
            
        data = json.loads(content)
        logging.info(f"Extracted {len(data.get('items', []))} items from receipt.")
        return data
    except Exception as e:
        logging.error(f"OpenAI API Error: {e}")
        if hasattr(e, 'response'):
             logging.error(f"OpenAI Response: {e.response}")
        return None

def add_items_to_notion(data):
    if not data or not data.get("items"):
        return

    logging.info("Uploading items to Notion...")
    url = "https://api.notion.com/v1/pages"
    
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }

    merchant_name = data.get("merchant") or "Unknown"
    receipt_date = data.get("date")

    success_count = 0
    
    for item in data["items"]:
        item_name = item.get("name") or "Unknown Item"
        qty = item.get("quantity", 1)
        unit_price = item.get("unit_price", 0)
        total_price = item.get("total_price", 0)
        category = item.get("category", "기타")

        payload = {
            "parent": {"database_id": NOTION_DATABASE_ID},
            "properties": {
                "항목": {
                    "title": [
                        {"text": {"content": item_name}}
                    ]
                },
                "날짜": {
                    "date": {"start": receipt_date} 
                } if receipt_date else None,
                "합계": {
                    "number": total_price
                },
                "단가": {
                    "number": unit_price
                },
                "수량": {
                    "number": qty
                },
                "분류": {
                    "select": {
                        "name": category
                    }
                },
                "사용처": {
                     "rich_text": [
                        {"text": {"content": merchant_name}}
                    ]
                }
            }
        }
        
        # Remove Date if None to avoid error
        if payload["properties"]["날짜"] is None:
            del payload["properties"]["날짜"]
            
        try:
            response = requests.post(url, headers=headers, json=payload)
            if response.status_code == 200:
                success_count += 1
            else:
                logging.error(f"Failed to add item '{item_name}': {response.status_code} - {response.text}")
        except Exception as e:
            logging.error(f"Notion API Error: {e}")
            
    logging.info(f"Successfully added {success_count} / {len(data['items'])} items to Notion.")

def scan_directory():
    """Manual scan to catch missed files"""
    logging.info("Polling directory for new files...")
    for root, dirs, files in os.walk(WATCH_DIR):
        for file in files:
            if is_valid_image(file):
                filepath = os.path.join(root, file)
                process_file(filepath)

if __name__ == "__main__":
    if not all([OPEN_AI_API_KEY, NOTION_TOKEN, NOTION_DATABASE_ID]):
        logging.warning("Missing API keys in .env file.")
    
    logging.info(f"Monitoring Directory (Recursive): {WATCH_DIR}")
    
    # 1. Start Watchdog
    event_handler = ReceiptHandler()
    observer = Observer()
    observer.schedule(event_handler, WATCH_DIR, recursive=True)
    observer.start()
    
    try:
        while True:
            # 2. Periodic Poll
            scan_directory()
            time.sleep(60)
            
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
