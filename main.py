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
from notion_validator import NotionValidator
from history_manager import HistoryManager
from archiver import FileArchiver

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

# Validation settings
ENABLE_VALIDATION = os.getenv("ENABLE_VALIDATION", "true").lower() == "true"
ENABLE_DUPLICATE_DETECTION = os.getenv("ENABLE_DUPLICATE_DETECTION", "true").lower() == "true"
ENABLE_AUTO_CORRECTION = os.getenv("ENABLE_AUTO_CORRECTION", "true").lower() == "true"

# Initialize OpenAI client
client = OpenAI(api_key=OPEN_AI_API_KEY)

# Initialize managers
history_manager = HistoryManager()
file_archiver = FileArchiver(WATCH_DIR) if WATCH_DIR else None
notion_validator = NotionValidator(NOTION_TOKEN, NOTION_DATABASE_ID) if (NOTION_TOKEN and NOTION_DATABASE_ID) else None

# Track image file paths for error correction
IMAGE_FILE_TRACKER = {}  # {(date, merchant): filepath}

def is_valid_image(filename, filepath=None):
    if filepath and "Archive" in filepath:
        return False
    ext = os.path.splitext(filename)[1].lower()
    return ext in ['.jpg', '.jpeg', '.png', '.heic']

def process_file(filepath):
    # Skip if in Archive or already processed
    if file_archiver and file_archiver.is_in_archive(filepath):
        return
    if history_manager.is_processed(filepath):
        return

    # Skip files older than 7 days
    try:
        mtime = os.path.getmtime(filepath)
        file_date = datetime.fromtimestamp(mtime)
        if datetime.now() - file_date > timedelta(days=7):
            history_manager.add_to_history(filepath)
            return
    except FileNotFoundError:
        return

    logging.info(f"Processing new file: {filepath}")
    
    time.sleep(2) # Wait for sync
    
    try:
        receipt_data = analyze_receipt(filepath)
        if receipt_data and "items" in receipt_data:
            # Upload to Notion with source file tracking
            add_items_to_notion(receipt_data, source_filepath=filepath)
            
            # Run validation and correction workflow
            if ENABLE_VALIDATION or ENABLE_DUPLICATE_DETECTION:
                validate_and_correct(receipt_data, filepath)
                
            # Mark as processed and archive
            history_manager.add_to_history(filepath)
            if file_archiver:
                file_archiver.archive_file(filepath, receipt_date=receipt_data.get("date"))
        else:
            logging.info("No items found in receipt. Marking as processed.")
            history_manager.add_to_history(filepath)
            if file_archiver:
                file_archiver.archive_file(filepath)
    except Exception as e:
        logging.error(f"Error processing {filepath}: {e}")

def validate_and_correct(receipt_data, filepath):
    """
    Validate uploaded data and correct errors if needed
    
    Args:
        receipt_data: The receipt data that was just uploaded
        filepath: Path to the source image file
    """
    if notion_validator is None:
        return
    merchant = receipt_data.get("merchant")
    date = receipt_data.get("date")
    
    # Step 1: Check for duplicates
    if ENABLE_DUPLICATE_DETECTION:
        logging.info("Checking for duplicate entries...")
        try:
            duplicates_removed = notion_validator.remove_duplicates()
            if duplicates_removed > 0:
                logging.info(f"Removed {duplicates_removed} duplicate entries")
        except Exception as e:
            logging.error(f"Error during duplicate detection: {e}")
    
    # Step 2: Validate data quality
    if ENABLE_VALIDATION:
        logging.info("Validating data quality...")
        try:
            # Get entries from this receipt
            if filepath:
                entry_ids = notion_validator.find_entries_by_source(filepath)
            else:
                entry_ids = notion_validator.find_entries_by_date_merchant(date, merchant)
            
            if not entry_ids:
                logging.warning("Could not find uploaded entries for validation")
                return
            
            # Validate each entry
            entries = notion_validator.get_all_entries()
            has_errors = False
            
            for entry in entries:
                if entry.get("id") in entry_ids:
                    errors = notion_validator.validate_entry(entry)
                    if errors:
                        has_errors = True
                        item_name = notion_validator.extract_property_value(entry, "항목")
                        logging.warning(f"Validation errors for '{item_name}': {', '.join(errors)}")
            
            # Step 3: Auto-correct if errors found
            if has_errors and ENABLE_AUTO_CORRECTION:
                logging.info("Validation errors detected. Starting auto-correction...")
                correct_errors(filepath, date, merchant)
            elif has_errors:
                logging.warning("Validation errors found but auto-correction is disabled")
                
        except Exception as e:
            logging.error(f"Error during validation: {e}")

def correct_errors(filepath, date, merchant):
    """
    Correct errors by re-analyzing image and replacing data
    
    Args:
        filepath: Path to the source image file
        date: Receipt date
        merchant: Merchant name
    """
    logging.info("Re-analyzing image for error correction...")
    
    try:
        # Step 1: Re-analyze with enhanced prompt
        corrected_data = analyze_receipt(filepath, is_retry=True)
        
        if not corrected_data or not corrected_data.get("items"):
            logging.error("Re-analysis failed to extract data")
            return
        
        # Step 2: Delete old incorrect entries
        logging.info("Deleting old incorrect entries...")
        if filepath:
            old_entry_ids = notion_validator.find_entries_by_source(filepath)
        else:
            old_entry_ids = notion_validator.find_entries_by_date_merchant(date, merchant)
        
        deleted_count = 0
        for entry_id in old_entry_ids:
            if notion_validator.delete_entry(entry_id):
                deleted_count += 1
        
        logging.info(f"Deleted {deleted_count} old entries")
        
        # Step 3: Upload corrected data
        logging.info("Uploading corrected data...")
        add_items_to_notion(corrected_data, source_filepath=filepath)
        logging.info("Error correction completed successfully")
        
    except Exception as e:
        logging.error(f"Error during auto-correction: {e}")

class ReceiptHandler(FileSystemEventHandler):
    def on_created(self, event):
        if not event.is_directory and is_valid_image(os.path.basename(event.src_path), event.src_path):
            logging.info(f"Detected creation: {event.src_path}")
            process_file(event.src_path)

    def on_moved(self, event):
        if not event.is_directory and is_valid_image(os.path.basename(event.dest_path), event.dest_path):
            logging.info(f"Detected move/rename: {event.dest_path}")
            process_file(event.dest_path)

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def analyze_receipt(image_path, is_retry=False):
    """
    Analyze receipt image with AI
    
    Args:
        image_path: Path to the receipt image
        is_retry: If True, use enhanced prompt for error correction
    """
    logging.info(f"Analyzing image with AI... (retry={is_retry})")
    try:
        base64_image = encode_image(image_path)
    except Exception as e:
        logging.error(f"Failed to read image: {e}")
        return None

    # Enhanced prompt for retry attempts
    if is_retry:
        prompt = """
        IMPORTANT: This is a re-analysis due to data quality issues. Please be extra careful and accurate.
        
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
        
        CRITICAL REQUIREMENTS:
        - "merchant": Extract the EXACT store name from the receipt.
        - "date": Must be in YYYY-MM-DD format. Double-check the date.
        - "items": Extract ALL items, do not skip any.
        - "name": Use the exact item name from the receipt.
        - "quantity": Must be a positive integer.
        - "unit_price" and "total_price": Must be positive numbers. Remove all currency symbols (₩, 원, etc.).
        - "category": Choose the MOST APPROPRIATE category from: 식재료, 가공식품, 간식, 채소, 과일, 생활용품, 기타
        
        Double-check all numbers and ensure no fields are missing.
        """
    else:
        # Standard prompt for first attempt
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
        - "date": The transaction date in YYYY-MM-DD format.
        - "items": Array of purchased items.
        - "category": Infer the category based on the item name from the given list.
        - Remove currency symbols from prices.
        - Ensure all prices are positive numbers.
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

def add_items_to_notion(data, source_filepath=None):
    """
    Upload items to Notion database
    
    Args:
        data: Receipt data with merchant, date, and items
        source_filepath: Path to the source image file (for error correction tracking)
    """
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
    
    # Track this image file for error correction
    if receipt_date and merchant_name and source_filepath:
        IMAGE_FILE_TRACKER[(receipt_date, merchant_name)] = source_filepath

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
        
        # Add source file tracking if available
        if source_filepath:
            payload["properties"]["원본파일"] = {
                "rich_text": [
                    {"text": {"content": source_filepath}}
                ]
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
            filepath = os.path.join(root, file)
            if is_valid_image(file, filepath):
                process_file(filepath)

if __name__ == "__main__":
    # Check if configuration is missing
    config_missing = not all([OPEN_AI_API_KEY, NOTION_TOKEN, NOTION_DATABASE_ID])
    
    if config_missing:
        logging.warning("Missing configuration in .env file.")
        # Try to launch setup wizard if it exists
        setup_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "setup_wizard.py")
        if os.path.exists(setup_script):
            logging.info("Launching setup wizard...")
            try:
                import subprocess
                subprocess.run(["python", setup_script], check=True)
                # Reload env after setup
                load_dotenv(override=True)
                OPEN_AI_API_KEY = os.getenv("OPEN_AI_API_KEY")
                NOTION_TOKEN = os.getenv("NOTION_TOKEN")
                NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")
                
                if not all([OPEN_AI_API_KEY, NOTION_TOKEN, NOTION_DATABASE_ID]):
                    logging.error("Configuration still missing after setup. Exiting.")
                    exit(1)
                else:
                    # Re-initialize clients (module-level names)
                    client = OpenAI(api_key=OPEN_AI_API_KEY)
                    notion_validator = NotionValidator(NOTION_TOKEN, NOTION_DATABASE_ID)
            except Exception as e:
                logging.error(f"Failed to run setup wizard: {e}")
                exit(1)
        else:
            logging.error("Setup wizard not found. Please create .env file manually.")
            exit(1)
    
    if not WATCH_DIR:
        logging.error("WATCH_DIR is not set in .env. Exiting.")
        exit(1)
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
