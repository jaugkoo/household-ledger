import os
import time
import base64
import json
import logging
import threading
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from openai import OpenAI
from notion_validator import NotionValidator
from history_manager import HistoryManager
from archiver import FileArchiver

# 상태창이 닫히면 메인 루프 종료용 (스레드 간 공유)
status_window_running = True
# 상태창에 표시할 진행 상황 (메인 스레드가 갱신, GUI 스레드가 주기적으로 읽음)
status_display = {"file": "", "status": "실행 중 · 감시 대기", "error": ""}
status_display_lock = threading.Lock()

def set_status(file=None, status=None, error=None):
    """상태창용 메시지 갱신 (메인 스레드에서 호출)."""
    with status_display_lock:
        if file is not None:
            status_display["file"] = file
        if status is not None:
            status_display["status"] = status
        if error is not None:
            status_display["error"] = error

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
        logging.info(f"[건너뜀] 아카이브 폴더 안의 파일: {filepath}")
        return
    if history_manager.is_processed(filepath):
        logging.info(f"[건너뜀] 이미 처리된 파일: {filepath}")
        return

    # Skip files older than N days (OneDrive 동기화 시 촬영일 기준일 수 있음)
    max_age_days = int(os.getenv("MAX_FILE_AGE_DAYS", "7"))
    try:
        mtime = os.path.getmtime(filepath)
        file_date = datetime.fromtimestamp(mtime)
        if datetime.now() - file_date > timedelta(days=max_age_days):
            logging.info(f"[건너뜀] {max_age_days}일 초과 파일 (수정일 {file_date.date()}): {filepath}")
            history_manager.add_to_history(filepath)
            return
    except FileNotFoundError:
        logging.warning(f"[건너뜀] 파일 없음 (동기화 대기 중?): {filepath}")
        return

    logging.info(f"Processing new file: {filepath}")
    short_name = os.path.basename(filepath)
    set_status(file=short_name, status="동기화 대기 중...", error="")
    
    # OneDrive 등 동기화 완료 대기 (placeholder 해제 대기)
    time.sleep(5)
    if not os.path.exists(filepath):
        set_status(status="건너뜀", error="대기 후에도 파일 없음 (동기화 미완료?)")
        logging.warning(f"[건너뜀] 대기 후에도 파일 없음: {filepath}")
        return
    try:
        if os.path.getsize(filepath) == 0:
            set_status(status="건너뜀", error="파일 크기 0바이트 (동기화 미완료?)")
            logging.warning(f"[건너뜀] 파일 크기 0바이트 (동기화 미완료?): {filepath}")
            return
    except OSError:
        return
    
    try:
        set_status(status="AI 분석 중...", error="")
        receipt_data = analyze_receipt(filepath)
        if not receipt_data:
            set_status(status="실패", error="AI 분석 결과 없음 (API/이미지 확인)")
            logging.warning(f"AI 분석 결과 없음 (이미지/API 오류 가능): {filepath}")
            return
        if not receipt_data.get("items"):
            set_status(status="완료(항목 없음)", error="")
            logging.info("No items found in receipt. Marking as processed.")
            history_manager.add_to_history(filepath)
            if file_archiver:
                file_archiver.archive_file(filepath)
            return
        set_status(status="노션 업로드 중...", error="")
        success_count, notion_error = add_items_to_notion(receipt_data, source_filepath=filepath)
        total_items = len(receipt_data.get("items", []))
        if success_count == 0 and notion_error:
            set_status(status="노션 업로드 실패", error=notion_error)
            logging.error(f"Notion에 추가된 항목 없음: {notion_error}")
            return
        if success_count < total_items and notion_error:
            set_status(status=f"일부만 추가됨 ({success_count}/{total_items})", error=notion_error)
        if success_count == total_items and notion_error is None:
            set_status(status="노션 업로드 완료", error="")
        if ENABLE_VALIDATION or ENABLE_DUPLICATE_DETECTION:
            set_status(status="검증 중...", error="")
            validate_and_correct(receipt_data, filepath)
        history_manager.add_to_history(filepath)
        if file_archiver:
            file_archiver.archive_file(filepath, receipt_date=receipt_data.get("date"))
        if success_count == total_items:
            set_status(status="완료", error="")
        else:
            set_status(status=f"완료 (노션 {success_count}/{total_items}개)", error=notion_error or "")
    except Exception as e:
        import traceback
        err_msg = str(e)
        tb = traceback.format_exc()
        if len(tb) > 400:
            err_msg = err_msg + "\n" + tb[-400:]
        else:
            err_msg = err_msg + "\n" + tb
        set_status(status="오류", error=err_msg)
        logging.exception(f"Error processing {filepath}: {e}")

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
    Upload items to Notion database.

    Returns:
        tuple: (success_count, error_message). error_message is set on first failure.
    """
    if not data or not data.get("items"):
        return (0, None)

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
    first_error = None
    
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
        
        # 원본파일은 DB에 해당 속성이 있을 때만 사용 (없으면 400 오류). 현재는 전송하지 않음.
        # 필요 시 노션 DB에 "원본파일" rich_text 속성을 추가한 뒤 아래 주석 해제.
        # if source_filepath:
        #     payload["properties"]["원본파일"] = {"rich_text": [{"text": {"content": source_filepath}}]}
        
        # Remove Date if None to avoid error
        if payload["properties"]["날짜"] is None:
            del payload["properties"]["날짜"]
            
        try:
            response = requests.post(url, headers=headers, json=payload)
            if response.status_code == 200:
                success_count += 1
            else:
                err = f"Notion API {response.status_code}: {response.text[:300]}"
                if not first_error:
                    first_error = err
                logging.error(f"Failed to add item '{item_name}': {response.status_code} - {response.text}")
        except Exception as e:
            err = f"Notion 요청 오류: {e}"
            if not first_error:
                first_error = err
            logging.error(f"Notion API Error: {e}")
            
    logging.info(f"Successfully added {success_count} / {len(data['items'])} items to Notion.")
    return (success_count, first_error)

def scan_directory():
    """Manual scan to catch missed files"""
    logging.info("Polling directory for new files...")
    for root, dirs, files in os.walk(WATCH_DIR):
        for file in files:
            filepath = os.path.join(root, file)
            if is_valid_image(file, filepath):
                process_file(filepath)


def run_status_window(watch_dir):
    """작은 확인창: 실행 중인 파일명, 진행 상황, 에러 메시지 표시."""
    global status_window_running
    try:
        import tkinter as tk
    except ImportError:
        logging.warning("tkinter not available, status window disabled.")
        return
    root = tk.Tk()
    root.title("Receipt Automation")
    root.resizable(True, True)
    root.minsize(320, 220)
    root.maxsize(480, 360)
    root.attributes("-topmost", True)
    root.geometry("340x240")
    # 창 닫기 시 플래그 설정 후 종료
    def on_closing():
        global status_window_running
        status_window_running = False
        root.quit()
        root.destroy()
    root.protocol("WM_DELETE_WINDOW", on_closing)
    frame = tk.Frame(root, padx=12, pady=10)
    frame.pack(fill=tk.BOTH, expand=True)
    # 상단: 감시 폴더
    dir_text = (watch_dir[: 38] + "…") if watch_dir and len(watch_dir) > 38 else (watch_dir or "-")
    label_dir = tk.Label(frame, text=f"감시: {dir_text}", font=("Segoe UI", 8), fg="#555")
    label_dir.pack(anchor=tk.W)
    # 현재 파일
    label_file = tk.Label(frame, text="", font=("Segoe UI", 10, "bold"), fg="#1a1a1a")
    label_file.pack(anchor=tk.W)
    # 진행 상황
    label_status = tk.Label(frame, text="실행 중 · 감시 대기", font=("Segoe UI", 10), fg="#2e7d32")
    label_status.pack(anchor=tk.W)
    # 에러 영역 (최대 4줄, 자동 줄바꿈)
    err_frame = tk.Frame(frame)
    err_frame.pack(anchor=tk.W, fill=tk.BOTH, expand=True)
    label_error = tk.Label(err_frame, text="", font=("Segoe UI", 8), fg="#c62828", justify=tk.LEFT, wraplength=300)
    label_error.pack(anchor=tk.NW, fill=tk.BOTH, expand=True)
    # 하단 안내
    hint = tk.Label(frame, text="창을 닫으면 프로그램이 종료됩니다.", font=("Segoe UI", 8), fg="#888")
    hint.pack(anchor=tk.SW)
    # 주기적으로 상태 갱신
    def update_status():
        try:
            with status_display_lock:
                data = {
                    "file": status_display.get("file", ""),
                    "status": status_display.get("status", ""),
                    "error": status_display.get("error", "")
                }
        except Exception:
            data = {"file": "", "status": "", "error": ""}
        label_file.config(text=data["file"] or "(대기 중)")
        label_status.config(text=data["status"] or "-")
        if data["status"] in ("오류", "실패", "건너뜀", "노션 업로드 실패", "일부만 추가됨") or "실패" in (data["status"] or ""):
            label_status.config(fg="#c62828")
        else:
            label_status.config(fg="#2e7d32")
        err_text = (data["error"] or "").strip()
        if len(err_text) > 500:
            err_text = err_text[:500] + "…"
        label_error.config(text=err_text or "-")
        root.after(500, update_status)
    root.after(300, update_status)
    root.mainloop()
    status_window_running = False


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
    
    # 0. 실행 상태 확인창 (별도 스레드)
    status_window_running = True
    status_thread = threading.Thread(target=run_status_window, args=(WATCH_DIR,), daemon=True)
    status_thread.start()
    
    # 1. Start Watchdog
    event_handler = ReceiptHandler()
    observer = Observer()
    observer.schedule(event_handler, WATCH_DIR, recursive=True)
    observer.start()
    
    try:
        while status_window_running:
            # 2. Periodic Poll
            scan_directory()
            for _ in range(60):
                if not status_window_running:
                    break
                time.sleep(1)
    except KeyboardInterrupt:
        status_window_running = False
    finally:
        observer.stop()
    observer.join()
    logging.info("Receipt Automation 종료됨.")
