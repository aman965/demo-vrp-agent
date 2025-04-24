"""
File utilities for the VRP application.
"""
import base64
import io

def get_download_link(df, filename="data.csv", text="Download CSV"):
    """Generate a download link for a DataFrame."""
    csv = df.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode()
    href = f'<a href="data:file/csv;base64,{b64}" download="{filename}">{text}</a>'
    return href 