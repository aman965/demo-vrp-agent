"""
JSON utilities for the VRP application.
"""
import json
import numpy as np
import pandas as pd
from datetime import datetime

class CustomJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles numpy types, pandas objects, and datetime objects."""
    def default(self, obj):
        if isinstance(obj, pd.DataFrame):
            return obj.to_dict(orient='records')
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, datetime):
            return obj.isoformat()
        if pd.isna(obj):
            return None
        return super().default(obj) 