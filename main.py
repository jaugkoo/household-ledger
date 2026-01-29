import os
import time
import base64
import json
import logging
import requests
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

class ReceiptHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory:
            return
        
        filename = event.src_path
        ext = os.path.splitext(filename)[1].lower()
        if ext in ['.jpg', '.jpeg', '.png', '.heic']:
            logging.info(f"New image detected: {filename}")
            
            # Wait a moment for file write to complete (OneDrive sync)
            time.sleep(2)
            
            try:
                receipt_data = analyze_receipt(filename)
                if receipt_data:
                     add_to_notion(receipt_data)
                else:
                    logging.info("No receipt data found in image.")
            except Exception as e:
                logging.error(f"Error processing {filename}: {e}")

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def analyze_receipt(image_path):
    logging.info("Analyzing image with AI...")
    base64_image = encode_image(image_path)

    prompt = """
    Analyze this image. If it is a receipt, extract the following information in JSON format:
    {
        "date": "YYYY-MM-DD",
        "merchant": "Merchant Name",
        "amount": 12345 (number only, remove currency symbols),
        "items": "Brief summary of items bought"
    }
    If it is NOT a receipt, return null.
    """

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": "You are an automated receipt scanner. Output only valid JSON."
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
    logging.info(f"Extracted Data: {data}")
    return data

def add_to_notion(data):
    if not data:
        return

    logging.info("Uploading to Notion...")
    url = "https://api.notion.com/v1/pages"
    
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }

    # Construct Notion payload
    # Note: Properties must match your Notion Database EXACTLY.
    # Adjust "Date", "Name", "Total", "Items" to match your column names.
    payload = {
        "parent": {"database_id": NOTION_DATABASE_ID},
        "properties": {
            "Name": { # Title property, usually named 'Name' or 'Merchant'
                "title": [
                    {"text": {"content": data.get("merchant", "Unknown")}}
                ]
            },
            "Date": { # Date property
                "date": {"start": data.get("date")} 
            } if data.get("date") else None,
            "Amount": { # Number property
                "number": data.get("amount")
            },
            "Items": { # Rich text property
                "rich_text": [
                    {"text": {"content": data.get("items", "")}}
                ]
            }
        }
    }
    
    # Remove None keys to avoid bad request if date is missing
    if payload["properties"]["Date"] is None:
        del payload["properties"]["Date"]

    response = requests.post(url, headers=headers, json=payload)
    
    if response.status_code == 200:
        logging.info("Successfully added to Notion!")
    else:
        logging.error(f"Failed to add to Notion: {response.text}")

if __name__ == "__main__":
    if not all([OPEN_AI_API_KEY, NOTION_TOKEN, NOTION_DATABASE_ID]):
        logging.warning("Missing API keys in .env file. Please edit it first.")
    
    logging.info(f"Monitoring Directory: {WATCH_DIR}")
    event_handler = ReceiptHandler()
    observer = Observer()
    observer.schedule(event_handler, WATCH_DIR, recursive=False)
    observer.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
