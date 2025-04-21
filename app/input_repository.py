import streamlit as st
import pandas as pd
import os
import datetime
import uuid
from pathlib import Path

def get_input_repository_dir():
    """Get the path to the input repository directory, creating it if it doesn't exist."""
    repo_dir = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) / ".data" / "inputs"
    os.makedirs(repo_dir, exist_ok=True)
    return repo_dir

def save_uploaded_file(uploaded_file, custom_name=None):
    """
    Save an uploaded file to the input repository with a custom name.
    
    Args:
        uploaded_file: The uploaded file from st.file_uploader
        custom_name: Optional custom name for the file
        
    Returns:
        dict: Metadata about the saved file
    """
    if uploaded_file is None:
        return None
    
    if not custom_name:
        custom_name = f"data_{uuid.uuid4().hex[:8]}"
    
    if not custom_name.lower().endswith('.csv'):
        custom_name += '.csv'
    
    repo_dir = get_input_repository_dir()
    
    file_path = repo_dir / custom_name
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    df = pd.read_csv(file_path)
    row_count = len(df)
    
    metadata = {
        "filename": custom_name,
        "upload_date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "row_count": row_count,
        "file_path": str(file_path)
    }
    
    return metadata

def get_saved_files():
    """
    Get a list of all saved files in the input repository with their metadata.
    
    Returns:
        list: List of dictionaries containing file metadata
    """
    repo_dir = get_input_repository_dir()
    files = []
    
    for file_path in repo_dir.glob("*.csv"):
        if file_path.name == ".gitkeep":
            continue
            
        try:
            stats = file_path.stat()
            
            df = pd.read_csv(file_path)
            row_count = len(df)
            
            metadata = {
                "filename": file_path.name,
                "upload_date": datetime.datetime.fromtimestamp(stats.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                "row_count": row_count,
                "file_path": str(file_path)
            }
            
            files.append(metadata)
        except Exception as e:
            st.error(f"Error reading file {file_path.name}: {str(e)}")
    
    files.sort(key=lambda x: x["upload_date"], reverse=True)
    
    return files

def load_file(file_path):
    """
    Load a file from the input repository.
    
    Args:
        file_path: Path to the file
        
    Returns:
        pandas.DataFrame: The loaded dataframe
    """
    return pd.read_csv(file_path)

def input_repository_page():
    """
    Display the input repository page.
    
    Returns:
        tuple: (selected_file, df) if a file is selected and the user clicks "Proceed", 
               otherwise (None, None)
    """
    st.title("Input Repository")
    st.markdown("""
    Upload, save, and manage your input files for the Vehicle Routing Problem solver.
    """)
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Upload New File")
        uploaded_file = st.file_uploader("Upload a CSV file", type=["csv"])
        
        if uploaded_file is not None:
            custom_name = st.text_input("Enter a custom name for this file (optional)")
            
            if st.button("Save to Repository"):
                with st.spinner("Saving file..."):
                    metadata = save_uploaded_file(uploaded_file, custom_name)
                    if metadata:
                        st.success(f"File saved as {metadata['filename']} with {metadata['row_count']} rows.")
                        st.experimental_rerun()
    
    with col2:
        st.subheader("File Requirements")
        st.markdown("""
        The CSV file should contain:
        - CustomerID
        - Latitude
        - Longitude
        - Demand
        
        The first row is assumed to be the depot.
        """)
    
    st.subheader("Saved Files")
    files = get_saved_files()
    
    if not files:
        st.info("No files have been saved yet. Upload a file to get started.")
        return None, None
    
    files_df = pd.DataFrame([
        {
            "Filename": f["filename"],
            "Upload Date": f["upload_date"],
            "Row Count": f["row_count"]
        } for f in files
    ])
    
    st.dataframe(files_df, use_container_width=True)
    
    selected_index = st.selectbox(
        "Select a file to use for optimization:",
        options=range(len(files)),
        format_func=lambda i: files[i]["filename"]
    )
    
    selected_file = files[selected_index]
    
    st.subheader(f"Preview: {selected_file['filename']}")
    df = load_file(selected_file["file_path"])
    st.dataframe(df.head(10), use_container_width=True)
    
    if st.button("Proceed to Scenario Setup", type="primary"):
        return selected_file, df
    
    return None, None
