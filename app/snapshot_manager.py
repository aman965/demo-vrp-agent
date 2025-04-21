import streamlit as st
import pandas as pd
import os
import datetime
import json
import uuid
import numpy as np
from pathlib import Path
import sys

class CustomJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder to handle non-serializable objects."""
    def default(self, obj):
        if isinstance(obj, pd.DataFrame):
            return obj.to_dict(orient='records')
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if pd.isna(obj):
            return None
        return super().default(obj)

def get_snapshots_dir():
    """Get the path to the snapshots directory, creating it if it doesn't exist."""
    repo_dir = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) / ".data" / "snapshots"
    os.makedirs(repo_dir, exist_ok=True)
    return repo_dir

def save_snapshot(snapshot_name, input_file_id, description=None):
    """
    Save a snapshot configuration to a JSON file.
    
    Args:
        snapshot_name: Name of the snapshot
        input_file_id: ID of the input file this snapshot is based on
        description: Optional description for this snapshot
        
    Returns:
        dict: Metadata about the saved snapshot
    """
    if not snapshot_name:
        snapshot_name = f"snapshot_{uuid.uuid4().hex[:8]}"
    
    snapshot_id = f"snapshot_{uuid.uuid4().hex[:8]}"
    
    snapshot_data = {
        "snapshot_id": snapshot_id,
        "snapshot_name": snapshot_name,
        "input_file_id": input_file_id,
        "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "description": description,
        "scenarios": []
    }
    
    snapshots_dir = get_snapshots_dir()
    file_path = snapshots_dir / f"{snapshot_id}.json"
    
    with open(file_path, "w") as f:
        json.dump(snapshot_data, f, indent=2, cls=CustomJSONEncoder)
    
    return snapshot_data

def get_snapshots_for_input_file(input_file_id):
    """
    Get all snapshots for a specific input file.
    
    Args:
        input_file_id: ID of the input file to get snapshots for
        
    Returns:
        list: List of snapshot data dictionaries
    """
    snapshots_dir = get_snapshots_dir()
    snapshots = []
    
    for file_path in snapshots_dir.glob("*.json"):
        try:
            with open(file_path, "r") as f:
                snapshot_data = json.load(f)
                
            if snapshot_data.get("input_file_id") == input_file_id:
                snapshots.append(snapshot_data)
        except Exception as e:
            st.error(f"Error reading snapshot file {file_path.name}: {str(e)}")
    
    snapshots.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    
    return snapshots

def get_all_snapshots():
    """
    Get all snapshots.
    
    Returns:
        list: List of snapshot data dictionaries
    """
    snapshots_dir = get_snapshots_dir()
    snapshots = []
    
    for file_path in snapshots_dir.glob("*.json"):
        try:
            with open(file_path, "r") as f:
                snapshot_data = json.load(f)
            snapshots.append(snapshot_data)
        except Exception as e:
            st.error(f"Error reading snapshot file {file_path.name}: {str(e)}")
    
    snapshots.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    
    return snapshots

def get_snapshot_by_id(snapshot_id):
    """
    Get a snapshot by its ID.
    
    Args:
        snapshot_id: ID of the snapshot to get
        
    Returns:
        dict: Snapshot data or None if not found
    """
    snapshots_dir = get_snapshots_dir()
    file_path = snapshots_dir / f"{snapshot_id}.json"
    
    if not file_path.exists():
        return None
    
    try:
        with open(file_path, "r") as f:
            snapshot_data = json.load(f)
        return snapshot_data
    except Exception as e:
        st.error(f"Error reading snapshot file {file_path.name}: {str(e)}")
        return None

def update_snapshot_scenarios(snapshot_id, scenario_id):
    """
    Update a snapshot with a new scenario ID.
    
    Args:
        snapshot_id: ID of the snapshot to update
        scenario_id: ID of the scenario to add
        
    Returns:
        bool: True if successful, False otherwise
    """
    snapshot_data = get_snapshot_by_id(snapshot_id)
    if not snapshot_data:
        return False
    
    if "scenarios" not in snapshot_data:
        snapshot_data["scenarios"] = []
    
    if scenario_id not in snapshot_data["scenarios"]:
        snapshot_data["scenarios"].append(scenario_id)
    
    snapshots_dir = get_snapshots_dir()
    file_path = snapshots_dir / f"{snapshot_id}.json"
    
    try:
        with open(file_path, "w") as f:
            json.dump(snapshot_data, f, indent=2, cls=CustomJSONEncoder)
        return True
    except Exception as e:
        st.error(f"Error updating snapshot scenarios: {str(e)}")
        return False

def snapshot_management_ui(input_file):
    """
    Display the snapshot management UI for a specific input file.
    
    Args:
        input_file: Metadata about the input file
        
    Returns:
        tuple: (selected_snapshot, create_scenario) if a snapshot is selected and the user wants to create a scenario,
               otherwise (None, False)
    """
    st.title("Snapshot Management")
    st.markdown(f"Managing snapshots for input file: **{input_file['filename']}**")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Create New Snapshot")
        
        snapshot_name = st.text_input("Snapshot Name", placeholder="Enter a descriptive name for this snapshot")
        
        description = st.text_area(
            "Description (Optional)",
            placeholder="Enter a description for this snapshot",
            help="This is for documentation purposes only."
        )
        
        if st.button("Save Snapshot"):
            with st.spinner("Saving snapshot..."):
                snapshot_data = save_snapshot(
                    snapshot_name=snapshot_name,
                    input_file_id=input_file['filename'],
                    description=description if description else None
                )
                st.success(f"Snapshot '{snapshot_data['snapshot_name']}' saved successfully!")
                st.rerun()
    
    with col2:
        st.subheader("What is a Snapshot?")
        st.markdown("""
        A snapshot is a reference to an input data file that you can use to create multiple scenarios:
        
        - Each snapshot is linked to a specific input file
        - You can create multiple scenarios for each snapshot
        - Snapshots help organize your work and compare different approaches
        
        Create a snapshot to start working with this input file.
        """)
    
    st.subheader("Saved Snapshots")
    snapshots = get_snapshots_for_input_file(input_file['filename'])
    
    if not snapshots:
        st.info("No snapshots have been created yet for this input file. Create your first snapshot above.")
        return None, False
    
    st.markdown("### Available Snapshots")
    
    for i, snapshot in enumerate(snapshots):
        col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
        
        with col1:
            st.markdown(f"**{snapshot['snapshot_name']}**")
            if snapshot.get("description"):
                st.markdown(f"_{snapshot['description']}_")
            st.caption(f"Created: {snapshot['created_at']} | Scenarios: {len(snapshot.get('scenarios', []))}")
        
        with col2:
            if st.button("Manage Scenarios", key=f"manage_{snapshot['snapshot_id']}"):
                st.session_state.selected_snapshot = snapshot
                return snapshot, True
        
        with col3:
            if st.button("Chat Assistant", key=f"chat_{snapshot['snapshot_id']}"):
                st.session_state.selected_snapshot = snapshot
                st.session_state.app_mode = 'chat_assistant'
                st.switch_page("Chat_Assistant")
                st.stop()
        
        with col4:
            if len(snapshot.get('scenarios', [])) >= 2:
                if st.button("Compare Scenarios", key=f"compare_{snapshot['snapshot_id']}"):
                    st.session_state.selected_snapshot = snapshot
                    st.session_state.app_mode = 'scenario_comparison'
                    st.rerun()
            else:
                st.button("Compare Scenarios", key=f"compare_{snapshot['snapshot_id']}", disabled=True)
        
        st.markdown("---")
    
    st.subheader("Select a Snapshot")
    selected_index = st.selectbox(
        "Choose a snapshot to work with:",
        options=range(len(snapshots)),
        format_func=lambda i: snapshots[i]["snapshot_name"]
    )
    
    selected_snapshot = snapshots[selected_index]
    
    st.subheader(f"Selected: {selected_snapshot['snapshot_name']}")
    
    if selected_snapshot.get("description"):
        st.markdown(f"**Description:** {selected_snapshot['description']}")
    
    scenario_count = len(selected_snapshot.get("scenarios", []))
    st.metric("Number of Scenarios", scenario_count)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("Manage Scenarios", type="primary"):
            return selected_snapshot, True
    
    with col2:
        if st.button("Chat Assistant"):
            st.session_state.selected_snapshot = selected_snapshot
            st.session_state.app_mode = 'chat_assistant'
            st.switch_page("Chat_Assistant")
            st.stop()
    
    with col3:
        if scenario_count >= 2:
            if st.button("Compare Scenarios"):
                st.session_state.selected_snapshot = selected_snapshot
                st.session_state.app_mode = 'scenario_comparison'
                st.rerun()
        else:
            st.button("Compare Scenarios", disabled=True)
    
    return None, False
