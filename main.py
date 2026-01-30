import os
import time
import base64
import json
import logging
import requests
import tempfile
from datetime import datetime, timedelta
from dotenv import load_dotenv
from openai import OpenAI
from msal import ConfidentialClientApplication

# Setup logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')

# Load environment variables
load_dotenv()

OPEN_AI_API_KEY = os.getenv("OPEN_AI_API_KEY")
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")

# OneDrive credentials
ONEDRIVE_CLIENT_ID = os.getenv("ONEDRIVE_CLIENT_ID")
ONEDRIVE_CLIENT_SECRET = os.getenv("ONEDRIVE_CLIENT_SECRET")
ONEDRIVE_TENANT_ID = os.getenv("ONEDRIVE_TENANT_ID", "common")
ONEDRIVE_REFRESH_TOKEN = os.getenv("ONEDRIVE_REFRESH_TOKEN")
ONEDRIVE_FOLDER_PATH = os.getenv("ONEDRIVE_FOLDER_PATH", "/사진/카메라 앨범")

# Initialize OpenAI client
client = OpenAI(api_key=OPEN_AI_API_KEY)

# Keep track of processed files
PROCESSED_FILES = set()

def get_onedrive_token():
    """Get access token using refresh token"""
    app = ConfidentialClientApplication(
        ONEDRIVE_CLIENT_ID,
        authority=f"https://login.microsoftonline.com/{ONEDRIVE_TENANT_ID}",
        client_credential=ONEDRIVE_CLIENT_SECRET
    )
    
    result = app.acquire_token_by_refresh_token(
        ONEDRIVE_REFRESH_TOKEN,
        scopes=["https://graph.microsoft.com/Files.Read.All"]
    )
    
    if "access_token" in result:
        return result["access_token"]
    else:
        logging.error(f"Failed to get token: {result.get('error_description')}")
        return None

def list_onedrive_files(access_token, folder_path):
    """List files in OneDrive folder"""
    # Encode folder path for URL
    encoded_path = requests.utils.quote(folder_path)
    url = f"https://graph.microsoft.com/v1.0/me/drive/root:{encoded_path}:/children"
    
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        return response.json().get("value", [])
    else:
        logging.error(f"Failed to list files: {response.status_code} - {response.text}")
        return []

def download_onedrive_file(access_token, file_id):
    """Download file from OneDrive and return temp path"""
    url = f"https://graph.microsoft.com/v1.0/me/drive/items/{file_id}/content"
    
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        # Save to temp file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
        temp_file.write(response.content)
        temp_file.close()
        return temp_file.name
    else:
        logging.error(f"Failed to download file: {response.status_code}")
        return None

def is_valid_image(filename):
    ext = filename.lower().split('.')[-1]
    return ext in ['jpg', 'jpeg', 'png', 'heic']

def process_file(filepath, file_id):
    if file_id in PROCESSED_FILES:
        return

    logging.info(f"Processing new file: {os.path.basename(filepath)}")
    PROCESSED_FILES.add(file_id)
    
    try:
        receipt_data = analyze_receipt(filepath)
        if receipt_data and "items" in receipt_data:
             add_items_to_notion(receipt_data)
        else:
            logging.info("No items found in receipt.")
    except Exception as e:
        logging.error(f"Error processing {filepath}: {e}")
    finally:
        # Clean up temp file
        try:
            os.unlink(filepath)
        except:
            pass

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

def poll_onedrive():
    """Poll OneDrive for new files"""
    logging.info("Polling OneDrive for new files...")
    
    access_token = get_onedrive_token()
    if not access_token:
        logging.error("Failed to get OneDrive access token")
        return
    
    files = list_onedrive_files(access_token, ONEDRIVE_FOLDER_PATH)
    
    # Filter for recent image files (last 7 days)
    cutoff_date = datetime.utcnow() - timedelta(days=7)
    
    for file in files:
        if file.get("folder"):
            continue  # Skip folders
            
        filename = file.get("name", "")
        if not is_valid_image(filename):
            continue
        
        # Check if file is recent
        modified_time = datetime.fromisoformat(file.get("lastModifiedDateTime", "").replace("Z", "+00:00"))
        if modified_time < cutoff_date:
            continue
        
        file_id = file.get("id")
        
        # Download and process
        temp_path = download_onedrive_file(access_token, file_id)
        if temp_path:
            process_file(temp_path, file_id)

if __name__ == "__main__":
    if not all([OPEN_AI_API_KEY, NOTION_TOKEN, NOTION_DATABASE_ID]):
        logging.warning("Missing API keys in .env file.")
    
    if not all([ONEDRIVE_CLIENT_ID, ONEDRIVE_CLIENT_SECRET, ONEDRIVE_REFRESH_TOKEN]):
        logging.error("Missing OneDrive credentials. Please run get_onedrive_token.py first.")
        exit(1)
    
    logging.info(f"Monitoring OneDrive folder: {ONEDRIVE_FOLDER_PATH}")
    
    try:
        while True:
            poll_onedrive()
            time.sleep(60)  # Poll every 60 seconds
            
    except KeyboardInterrupt:
        logging.info("Stopped by user")
