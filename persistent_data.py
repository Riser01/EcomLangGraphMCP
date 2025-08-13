# persistent_data.py
import json
import os
from typing import Dict, Any
import threading

class PersistentOrderDB:
    """A thread-safe persistent order database that saves to JSON file."""
    
    def __init__(self, db_file: str = "orders_db.json"):
        self.db_file = db_file
        self._lock = threading.Lock()
        self._data = {}
        self._load_data()
    
    def _load_data(self):
        """Load data from JSON file, or initialize with default data if file doesn't exist."""
        try:
            if os.path.exists(self.db_file):
                with open(self.db_file, 'r') as f:
                    self._data = json.load(f)
                print(f"[PersistentDB] Loaded {len(self._data)} orders from {self.db_file}")
            else:
                # Initialize with default data from data.py
                from data import _MOCK_ORDERS_DB
                self._data = _MOCK_ORDERS_DB.copy()
                self._save_data()
                print(f"[PersistentDB] Initialized with {len(self._data)} default orders")
        except Exception as e:
            print(f"[PersistentDB] Error loading data: {e}")
            # Fallback to default data
            from data import _MOCK_ORDERS_DB
            self._data = _MOCK_ORDERS_DB.copy()
    
    def _save_data(self):
        """Save current data to JSON file."""
        try:
            with open(self.db_file, 'w') as f:
                json.dump(self._data, f, indent=2)
            print(f"[PersistentDB] Saved {len(self._data)} orders to {self.db_file}")
        except Exception as e:
            print(f"[PersistentDB] Error saving data: {e}")
    
    def get(self, order_id: str) -> Dict[str, Any]:
        """Get an order by ID."""
        with self._lock:
            return self._data.get(order_id)
    
    def update(self, order_id: str, updates: Dict[str, Any]) -> bool:
        """Update an order and persist changes."""
        with self._lock:
            if order_id in self._data:
                self._data[order_id].update(updates)
                self._save_data()
                return True
            return False
    
    def get_all(self) -> Dict[str, Any]:
        """Get all orders."""
        with self._lock:
            return self._data.copy()

# Global instance for the MCP server
persistent_orders_db = PersistentOrderDB()
