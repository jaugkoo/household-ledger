# Household Account Book Automation (가계부 자동화)

This is a Python automation script that monitors a OneDrive folder for receipt photos, analyzes them using OpenAI's GPT-4o, and automatically saves the itemized details to a Notion database.

## Features

-   **Automatic Monitoring**: Watches `OneDrive/사진/카메라 앨범` for new images.
-   **AI Analysis**: Extracts Date, Merchant, Items, Unit Price, Quantity, and Category from receipt photos.
-   **Notion Integration**: Uploads each item as a separate row in your Notion Household Ledger.
-   **Duplicate Prevention**: Skips files that have already been processed (in the current session).
-   **Data Validation**: Automatically validates uploaded data for quality issues (missing fields, invalid dates, negative prices).
-   **Duplicate Detection**: Finds and removes duplicate entries based on item name, date, merchant, and price.
-   **Error Correction**: Automatically re-analyzes images and corrects data when validation errors are detected.
-   **Date-Based Organization**: Ensures all entries have valid dates for proper chronological sorting.
-   **Source Tracking**: Tracks which image file each entry came from for accurate error correction.
-   **Persistent History**: Remembers processed files across restarts using `.processed_history`.
-   **Automatic Archiving**: Moves processed receipts to `Archive/YYYY/MM/` to keep your camera roll clean.

## Prerequisites

1.  **Python 3.10+**: Ensure Python is installed on your system.
2.  **API Keys**:
    -   OpenAI API Key
    -   Notion Integration Token
    -   Notion Database ID

## Installation

### Quick Install (Recommended)

1. **Run the installer**:
   ```powershell
   install.bat
   ```

2. **Enter your credentials** in the setup wizard:
   - OpenAI API Key
   - Notion Integration Token
   - Notion Database ID
   - Watch directory (default: OneDrive Camera Roll)

3. **Done!** The program will auto-start when Windows boots.

### Manual Installation

1.  Clone this repository or download the code.
2.  Open a terminal (PowerShell or CMD) in the project folder.
3.  Install dependencies:
    ```powershell
    pip install -r requirements.txt
    ```
4.  Run setup wizard:
    ```powershell
    python setup_wizard.py
    ```
5.  Or manually configure `.env` file:
    -   Copy `.env.example` to `.env`.
    -   Fill in your `OPEN_AI_API_KEY`, `NOTION_TOKEN`, and `NOTION_DATABASE_ID`.

## Usage

### Auto-Start (After Installation)

The program automatically starts when Windows boots. No action needed!

### Manual Start

Run the script directly:

```powershell
start.bat
```

Or from terminal:

```powershell
python main.py
```

The script will start monitoring. Simply take a photo of a receipt (which syncs to OneDrive), and it will be processed automatically.

### Change Settings

To modify API keys or settings:

```powershell
python setup_wizard.py
```

Or edit the `.env` file directly.

## Configuration

You can customize the validation behavior by editing the `.env` file:

```env
# Validation Settings
ENABLE_VALIDATION=true           # Validates data quality (dates, prices, required fields)
ENABLE_DUPLICATE_DETECTION=true  # Automatically removes duplicate entries
ENABLE_AUTO_CORRECTION=true      # Re-analyzes images when errors are detected
```

**How it works:**
1. **Validation**: Checks each uploaded entry for missing fields, invalid dates, and negative prices
2. **Duplicate Detection**: Finds entries with identical item name, date, merchant, and price, keeping only the newest
3. **Auto Correction**: When validation errors are found, the system re-analyzes the image with an enhanced prompt, deletes the incorrect data, and uploads corrected data

## Troubleshooting: 사진이 노션에 추가되지 않을 때

프로그램을 **콘솔에서 실행**하면 (`python main.py`) 로그로 이유를 확인할 수 있습니다.

| 로그 메시지 | 원인 | 해결 |
|------------|------|------|
| `[건너뜀] 이미 처리된 파일` | 이전에 처리된 파일 | `.processed_history`에서 해당 경로를 삭제하거나, 새 사진으로 시도 |
| `[건너뜀] 7일 초과 파일` | 파일 수정일이 7일보다 오래됨 (OneDrive는 촬영일 기준일 수 있음) | `.env`에 `MAX_FILE_AGE_DAYS=30` 등으로 늘리기 |
| `[건너뜀] 파일 없음` / `파일 크기 0바이트` | OneDrive 동기화가 아직 안 됨 | 사진 업로드 후 몇 분 기다리거나, 동기화 완료 후 다시 시도 |
| `AI 분석 결과 없음` | OpenAI API 오류 또는 이미지 인식 실패 | API 키·크레딧 확인, 이미지가 영수증인지·선명한지 확인 |
| `Failed to add item` (Notion) | Notion 토큰·DB ID 오류 또는 DB 속성 불일치 | `.env`의 `NOTION_TOKEN`, `NOTION_DATABASE_ID` 및 DB 속성명 확인 |

**확인할 것:**
1. **WATCH_DIR**: `.env`의 감시 폴더가 **사진을 올리는 OneDrive 폴더 경로**와 동일한지 확인 (예: `C:\Users\...\OneDrive\사진\카메라 앨범`).
2. **파일 형식**: `.jpg`, `.jpeg`, `.png`, `.heic`만 처리됩니다.
3. **Archive 폴더**: 이미 처리되어 `Archive` 안으로 옮겨진 파일은 다시 처리되지 않습니다.

## Files

### Main Files
-   `main.py`: The main automation script.
-   `notion_validator.py`: Data validation and duplicate detection module.
-   `history_manager.py`: Persistent file tracking utility.
-   `archiver.py`: Date-based file archiving utility.

### Installation & Setup
-   `install.bat`: One-click installer with auto-start setup.
-   `setup_wizard.py`: GUI configuration tool.
-   `start.bat`: Manual start script.
-   `uninstall.bat`: Remove auto-start configuration.

### Documentation
-   `README.md`: English documentation.
-   `사용가이드.md`: Korean user guide (comprehensive).
-   `빠른사용법.md`: Korean quick reference.
-   `QUICK_START.md`: Quick start guide.

### Configuration
-   `requirements.txt`: Python package dependencies.
-   `.env`: Configuration file (Do not share this file).
-   `.env.example`: Configuration template.
