import os
import shutil
import logging
from datetime import datetime

class FileArchiver:
    """Handles moving processed files to a date-based archive folder."""
    
    def __init__(self, base_dir):
        self.base_dir = base_dir
        self.archive_root = os.path.join(base_dir, "Archive")
        
    def archive_file(self, filepath, receipt_date=None):
        """
        Moves a file to Archive/YYYY/MM/ directory.
        If receipt_date is not provided, uses the current date.
        """
        if not os.path.exists(filepath):
            logging.error(f"Cannot archive non-existent file: {filepath}")
            return None
            
        try:
            # Determine folder structure based on date
            if receipt_date:
                try:
                    dt = datetime.strptime(receipt_date, "%Y-%m-%d")
                except ValueError:
                    dt = datetime.now()
            else:
                dt = datetime.now()
                
            year_dir = dt.strftime("%Y")
            month_dir = dt.strftime("%m")
            
            target_dir = os.path.join(self.archive_root, year_dir, month_dir)
            
            # Create directories if they don't exist
            os.makedirs(target_dir, exist_ok=True)
            
            # Move file
            filename = os.path.basename(filepath)
            dest_path = os.path.join(target_dir, filename)
            
            # Handle potential filename collisions
            if os.path.exists(dest_path):
                timestamp = datetime.now().strftime("%H%M%S")
                name, ext = os.path.splitext(filename)
                dest_path = os.path.join(target_dir, f"{name}_{timestamp}{ext}")
            
            shutil.move(filepath, dest_path)
            logging.info(f"Archived: {filename} -> {dest_path}")
            return dest_path
            
        except Exception as e:
            logging.error(f"Error archiving file {filepath}: {e}")
            return None

    def is_in_archive(self, filepath):
        """Checks if a file is already within the Archive structure."""
        abs_path = os.path.abspath(filepath)
        abs_archive = os.path.abspath(self.archive_root)
        return abs_path.startswith(abs_archive)
