"""
Module for storing cryptocurrency data locally.
"""
import os
import json
import logging
from datetime import date
from pathlib import Path

logger = logging.getLogger(__name__)

class DataStorage:
    """Handles storage of cryptocurrency data."""
    
    def __init__(self, base_dir=None):
        """
        Initialize the storage manager.
        
        Args:
            base_dir (str, optional): Base directory for storing data. Defaults to './data'.
        """
        self.base_dir = Path(base_dir) if base_dir else Path('data')
        self.base_dir.mkdir(exist_ok=True, parents=True)
        logger.debug(f"Storage initialized with base directory {self.base_dir}")
    
    def save_coin_data(self, coin_id, date_obj, data):
        """
        Save coin data to a file.
        
        Args:
            coin_id (str): The coin identifier
            date_obj (date): The date of the data
            data (dict): The data to save
            
        Returns:
            str: The path to the saved file
        """
        # Create coin-specific directory
        coin_dir = self.base_dir / coin_id
        coin_dir.mkdir(exist_ok=True)
        
        # Format date for filename
        date_str = date_obj.strftime('%Y-%m-%d')
        file_name = f"{coin_id}_{date_str}.json"
        file_path = coin_dir / file_name
        
        logger.debug(f"Saving data to {file_path}")
        
        # Save data to file
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Data saved to {file_path}")
        return str(file_path)
    
    def get_coin_data(self, coin_id, date_obj):
        """
        Retrieve coin data from a file.
        
        Args:
            coin_id (str): The coin identifier
            date_obj (date): The date of the data
            
        Returns:
            dict: The retrieved data, or None if not found
        """
        date_str = date_obj.strftime('%Y-%m-%d')
        file_name = f"{coin_id}_{date_str}.json"
        file_path = self.base_dir / coin_id / file_name
        
        if not file_path.exists():
            logger.warning(f"Data file not found: {file_path}")
            return None
        
        logger.debug(f"Reading data from {file_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error reading data from {file_path}: {str(e)}")
            return None
