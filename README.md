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

## Prerequisites

1.  **Python 3.10+**: Ensure Python is installed on your system.
2.  **API Keys**:
    -   OpenAI API Key
    -   Notion Integration Token
    -   Notion Database ID

## Installation

1.  Clone this repository or download the code.
2.  Open a terminal (PowerShell or CMD) in the project folder.
3.  Install dependencies:
    ```powershell
    pip install -r requirements.txt
    ```
4.  Configure `.env` file:
    -   Copy `.env.example` to `.env`.
    -   Fill in your `OPEN_AI_API_KEY`, `NOTION_TOKEN`, and `NOTION_DATABASE_ID`.

## Usage

Run the script directly from your terminal:

```powershell
python main.py
```

The script will start monitoring. Simply take a photo of a receipt (which syncs to OneDrive), and it will be processed automatically.

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

## Files

-   `main.py`: The main automation script.
-   `notion_validator.py`: Data validation and duplicate detection module.
-   `requirements.txt`: Python package dependencies.
-   `.env`: Configuration file (Do not share this file).
