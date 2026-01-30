import os
import json
import logging

class HistoryManager:
    """Manages the history of processed files to prevent duplicate processing across restarts."""
    
    def __init__(self, history_file=".processed_history"):
        self.history_file = history_file
        self.processed_files = self._load_history()
        
    def _load_history(self):
        """Loads processed file paths from the history file."""
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    return set(line.strip() for line in f if line.strip())
            except Exception as e:
                logging.error(f"Error loading history file: {e}")
                return set()
        return set()
    
    def is_processed(self, filepath):
        """Checks if a file has already been processed."""
        # Convert to absolute path to avoid confusion
        abs_path = os.path.abspath(filepath)
        return abs_path in self.processed_files
    
    def add_to_history(self, filepath):
        """Adds a file path to the history and saves it to disk."""
        abs_path = os.path.abspath(filepath)
        if abs_path not in self.processed_files:
            self.processed_files.add(abs_path)
            try:
                with open(self.history_file, 'a', encoding='utf-8') as f:
                    f.write(abs_path + '\n')
            except Exception as e:
                logging.error(f"Error saving to history file: {e}")
                
    def get_count(self):
        """Returns the number of processed files."""
        return len(self.processed_files)
