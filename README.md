# Household Account Book Automation (가계부 자동화)

This is a Python automation script that monitors a OneDrive folder for receipt photos, analyzes them using OpenAI's GPT-4o, and automatically saves the itemized details to a Notion database.

## Features

-   **Automatic Monitoring**: Watches `OneDrive/사진/카메라 앨범` for new images.
-   **AI Analysis**: Extracts Date, Merchant, Items, Unit Price, Quantity, and Category from receipt photos.
-   **Notion Integration**: Uploads each item as a separate row in your Notion Household Ledger.
-   **Duplicate Prevention**: Skips files that have already been processed (in the current session).

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

## Files

-   `main.py`: The main automation script.
-   `requirements.txt`: Python package dependencies.
-   `.env`: Configuration file (Do not share this file).
