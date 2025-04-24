"""
JSON utilities for the VRP application.
"""
import json
import numpy as np
from datetime import datetime

class CustomJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles numpy types and datetime objects."""
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj) 