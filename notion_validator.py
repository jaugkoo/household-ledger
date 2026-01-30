import os
import logging
import requests
from datetime import datetime
from typing import List, Dict, Optional, Set

class NotionValidator:
    """Handles Notion database validation, duplicate detection, and data management"""
    
    def __init__(self, token: str, database_id: str):
        self.token = token
        self.database_id = database_id
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28"
        }
        self.base_url = "https://api.notion.com/v1"
    
    def get_all_entries(self, max_pages: int = 10) -> List[Dict]:
        """
        Fetch all entries from Notion database
        
        Args:
            max_pages: Maximum number of pages to fetch (100 entries per page)
        
        Returns:
            List of all database entries
        """
        url = f"{self.base_url}/databases/{self.database_id}/query"
        all_results = []
        has_more = True
        start_cursor = None
        page_count = 0
        
        while has_more and page_count < max_pages:
            payload = {}
            if start_cursor:
                payload["start_cursor"] = start_cursor
            
            try:
                response = requests.post(url, headers=self.headers, json=payload)
                if response.status_code != 200:
                    logging.error(f"Failed to fetch entries: {response.status_code} - {response.text}")
                    break
                
                data = response.json()
                all_results.extend(data.get("results", []))
                has_more = data.get("has_more", False)
                start_cursor = data.get("next_cursor")
                page_count += 1
                
            except Exception as e:
                logging.error(f"Error fetching Notion entries: {e}")
                break
        
        logging.info(f"Fetched {len(all_results)} entries from Notion")
        return all_results
    
    def extract_property_value(self, entry: Dict, property_name: str) -> Optional[any]:
        """Extract value from Notion property"""
        try:
            props = entry.get("properties", {})
            prop = props.get(property_name, {})
            prop_type = prop.get("type")
            
            if prop_type == "title":
                title_list = prop.get("title", [])
                return title_list[0].get("text", {}).get("content", "") if title_list else ""
            elif prop_type == "rich_text":
                text_list = prop.get("rich_text", [])
                return text_list[0].get("text", {}).get("content", "") if text_list else ""
            elif prop_type == "number":
                return prop.get("number")
            elif prop_type == "date":
                date_obj = prop.get("date")
                return date_obj.get("start") if date_obj else None
            elif prop_type == "select":
                select_obj = prop.get("select")
                return select_obj.get("name") if select_obj else None
            else:
                return None
        except Exception as e:
            logging.warning(f"Error extracting property '{property_name}': {e}")
            return None
    
    def find_duplicates(self, entries: List[Dict]) -> List[Set[str]]:
        """
        Find duplicate entries based on: item name + date + merchant + total price
        
        Returns:
            List of sets, where each set contains page IDs of duplicate entries
        """
        # Group entries by duplicate key
        groups = {}
        
        for entry in entries:
            page_id = entry.get("id")
            item_name = self.extract_property_value(entry, "항목")
            date = self.extract_property_value(entry, "날짜")
            merchant = self.extract_property_value(entry, "사용처")
            total_price = self.extract_property_value(entry, "합계")
            
            # Create unique key for duplicate detection
            # Skip if any critical field is missing
            if not item_name or not date or total_price is None:
                continue
            
            key = (
                str(item_name).strip().lower(),
                str(date).strip(),
                str(merchant or "").strip().lower(),
                float(total_price)
            )
            
            if key not in groups:
                groups[key] = []
            groups[key].append({
                "page_id": page_id,
                "created_time": entry.get("created_time"),
                "item_name": item_name
            })
        
        # Find groups with duplicates (more than 1 entry)
        duplicate_sets = []
        for key, group in groups.items():
            if len(group) > 1:
                # Sort by created_time (keep newest, delete oldest)
                sorted_group = sorted(group, key=lambda x: x["created_time"], reverse=True)
                # Keep first (newest), mark rest as duplicates
                duplicate_ids = {item["page_id"] for item in sorted_group[1:]}
                duplicate_sets.append(duplicate_ids)
                logging.info(f"Found {len(duplicate_ids)} duplicates for: {sorted_group[0]['item_name']}")
        
        return duplicate_sets
    
    def validate_entry(self, entry: Dict) -> List[str]:
        """
        Validate a single entry for data quality issues
        
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        # Check required fields
        item_name = self.extract_property_value(entry, "항목")
        if not item_name or item_name.strip() == "":
            errors.append("Missing item name (항목)")
        
        date = self.extract_property_value(entry, "날짜")
        if not date:
            errors.append("Missing date (날짜)")
        else:
            # Validate date format
            try:
                datetime.strptime(date, "%Y-%m-%d")
            except ValueError:
                errors.append(f"Invalid date format: {date} (expected YYYY-MM-DD)")
        
        total_price = self.extract_property_value(entry, "합계")
        if total_price is None:
            errors.append("Missing total price (합계)")
        elif total_price <= 0:
            errors.append(f"Invalid price: {total_price} (must be positive)")
        
        # Check category
        category = self.extract_property_value(entry, "분류")
        valid_categories = ["식재료", "가공식품", "간식", "채소", "과일", "생활용품", "기타"]
        if category and category not in valid_categories:
            errors.append(f"Invalid category: {category}")
        
        return errors
    
    def delete_entry(self, page_id: str) -> bool:
        """
        Delete (archive) a Notion page
        
        Returns:
            True if successful, False otherwise
        """
        url = f"{self.base_url}/pages/{page_id}"
        payload = {"archived": True}
        
        try:
            response = requests.patch(url, headers=self.headers, json=payload)
            if response.status_code == 200:
                logging.info(f"Deleted entry: {page_id}")
                return True
            else:
                logging.error(f"Failed to delete entry {page_id}: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            logging.error(f"Error deleting entry {page_id}: {e}")
            return False
    
    def find_entries_by_source(self, source_file: str) -> List[str]:
        """
        Find all entries that came from a specific source image file
        
        Returns:
            List of page IDs
        """
        entries = self.get_all_entries()
        matching_ids = []
        
        for entry in entries:
            entry_source = self.extract_property_value(entry, "원본파일")
            if entry_source and entry_source.strip() == source_file.strip():
                matching_ids.append(entry.get("id"))
        
        logging.info(f"Found {len(matching_ids)} entries from source: {source_file}")
        return matching_ids
    
    def find_entries_by_date_merchant(self, date: str, merchant: str) -> List[str]:
        """
        Find all entries with matching date and merchant
        Used for error correction when source file is not tracked
        
        Returns:
            List of page IDs
        """
        entries = self.get_all_entries()
        matching_ids = []
        
        for entry in entries:
            entry_date = self.extract_property_value(entry, "날짜")
            entry_merchant = self.extract_property_value(entry, "사용처")
            
            if (entry_date == date and 
                str(entry_merchant or "").strip().lower() == str(merchant or "").strip().lower()):
                matching_ids.append(entry.get("id"))
        
        logging.info(f"Found {len(matching_ids)} entries for {date} at {merchant}")
        return matching_ids
    
    def remove_duplicates(self) -> int:
        """
        Find and remove all duplicate entries
        
        Returns:
            Number of duplicates removed
        """
        logging.info("Checking for duplicates...")
        entries = self.get_all_entries()
        duplicate_sets = self.find_duplicates(entries)
        
        total_removed = 0
        for duplicate_ids in duplicate_sets:
            for page_id in duplicate_ids:
                if self.delete_entry(page_id):
                    total_removed += 1
        
        logging.info(f"Removed {total_removed} duplicate entries")
        return total_removed
    
    def validate_all_entries(self) -> Dict[str, List[str]]:
        """
        Validate all entries in the database
        
        Returns:
            Dictionary mapping page_id to list of validation errors
        """
        logging.info("Validating all entries...")
        entries = self.get_all_entries()
        validation_results = {}
        
        for entry in entries:
            page_id = entry.get("id")
            errors = self.validate_entry(entry)
            if errors:
                item_name = self.extract_property_value(entry, "항목")
                validation_results[page_id] = {
                    "item_name": item_name,
                    "errors": errors
                }
        
        if validation_results:
            logging.warning(f"Found {len(validation_results)} entries with validation errors")
        else:
            logging.info("All entries passed validation")
        
        return validation_results
