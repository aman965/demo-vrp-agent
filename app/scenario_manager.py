import streamlit as st
import pandas as pd
import os
import datetime
import json
import uuid
import numpy as np
from pathlib import Path

class CustomJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder to handle non-serializable objects."""
    def default(self, obj):
        if isinstance(obj, (np.int_, np.intc, np.intp, np.int8,
            np.int16, np.int32, np.int64, np.uint8,
            np.uint16, np.uint32, np.uint64)):
            return int(obj)
        elif isinstance(obj, (np.float_, np.float16, np.float32, np.float64)):
            return float(obj)
        elif isinstance(obj, (np.ndarray,)):
            return obj.tolist()
        elif isinstance(obj, pd.DataFrame):
            return obj.to_dict('records')
        elif isinstance(obj, datetime.datetime):
            return obj.strftime("%Y-%m-%d %H:%M:%S")
        elif pd.isna(obj):
            return None
        return super().default(obj)

def get_scenarios_dir():
    """Get the path to the scenarios directory, creating it if it doesn't exist."""
    repo_dir = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) / ".data" / "scenarios"
    os.makedirs(repo_dir, exist_ok=True)
    return repo_dir

def save_scenario(snapshot_id, scenario_name, num_vehicles, vehicle_capacity, constraints=None):
    """
    Save a scenario configuration to a JSON file.
    
    Args:
        snapshot_id: ID of the snapshot this scenario is based on
        scenario_name: Name of the scenario
        num_vehicles: Number of vehicles for this scenario
        vehicle_capacity: Vehicle capacity for this scenario
        constraints: Optional text constraints for this scenario
        
    Returns:
        dict: Metadata about the saved scenario
    """
    if not scenario_name:
        scenario_name = f"scenario_{uuid.uuid4().hex[:8]}"
    
    scenario_id = f"scenario_{uuid.uuid4().hex[:8]}"
    
    scenario_data = {
        "scenario_id": scenario_id,
        "scenario_name": scenario_name,
        "snapshot_id": snapshot_id,
        "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "config": {
            "num_vehicles": num_vehicles,
            "vehicle_capacity": vehicle_capacity
        },
        "constraints": constraints,
        "optimization_results": None
    }
    
    scenarios_dir = get_scenarios_dir()
    file_path = scenarios_dir / f"{scenario_id}.json"
    
    with open(file_path, "w") as f:
        json.dump(scenario_data, f, indent=2, cls=CustomJSONEncoder)
    
    return scenario_data

def get_scenarios_for_snapshot(snapshot_id):
    """
    Get all scenarios for a specific snapshot.
    
    Args:
        snapshot_id: ID of the snapshot to get scenarios for
        
    Returns:
        list: List of scenario data dictionaries
    """
    scenarios_dir = get_scenarios_dir()
    scenarios = []
    
    for file_path in scenarios_dir.glob("*.json"):
        try:
            with open(file_path, "r") as f:
                scenario_data = json.load(f)
                
            if scenario_data.get("snapshot_id") == snapshot_id:
                scenarios.append(scenario_data)
        except Exception as e:
            st.error(f"Error reading scenario file {file_path.name}: {str(e)}")
    
    scenarios.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    
    return scenarios

def add_scenario_to_snapshot(snapshot_id, scenario_id):
    """
    Add a scenario ID to a snapshot's list of scenarios.
    
    Args:
        snapshot_id: ID of the snapshot to update
        scenario_id: ID of the scenario to add
        
    Returns:
        bool: True if successful, False otherwise
    """
    from snapshot_manager import get_snapshot_by_id, update_snapshot_scenarios
    
    snapshot = get_snapshot_by_id(snapshot_id)
    if not snapshot:
        return False
    
    return update_snapshot_scenarios(snapshot_id, scenario_id)

def get_scenario_by_id(scenario_id):
    """
    Get a scenario by its ID.
    
    Args:
        scenario_id: ID of the scenario to get
        
    Returns:
        dict: Scenario data or None if not found
    """
    scenarios_dir = get_scenarios_dir()
    file_path = scenarios_dir / f"{scenario_id}.json"
    
    if not file_path.exists():
        return None
    
    try:
        with open(file_path, "r") as f:
            scenario_data = json.load(f)
        return scenario_data
    except Exception as e:
        st.error(f"Error reading scenario file {file_path.name}: {str(e)}")
        return None

def update_scenario_results(scenario_id, results):
    """
    Update a scenario with optimization results.
    
    Args:
        scenario_id: ID of the scenario to update
        results: Optimization results to save
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        scenario_data = get_scenario_by_id(scenario_id)
        if not scenario_data:
            st.error(f"Could not find scenario with ID: {scenario_id}")
            return False
        
        # Ensure all numpy/pandas objects are converted to basic Python types
        clean_results = {
            'total_distance': float(results.get('total_distance', 0)),
            'total_customers': int(results.get('total_customers', 0)),
            'total_demand': int(results.get('total_demand', 0)),
            'capacity_utilization': float(results.get('capacity_utilization', 0)),
            'route_summary': results.get('route_summary', []),
            'route_info': results.get('route_info', []),
            'kpi_df': results.get('kpi_df', []),
            'detailed_df': results.get('detailed_df', []),
            'vehicle_capacity': int(results.get('vehicle_capacity', 0)),
            'timestamp': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        scenario_data["optimization_results"] = clean_results
        
        scenarios_dir = get_scenarios_dir()
        file_path = scenarios_dir / f"{scenario_id}.json"
        
        with open(file_path, "w") as f:
            json.dump(scenario_data, f, indent=2, cls=CustomJSONEncoder)
        return True
        
    except Exception as e:
        st.error(f"Error updating scenario results: {str(e)}")
        return False

def scenario_management_ui(snapshot_id, snapshot_name):
    """
    Display the scenario management UI for a specific snapshot.
    
    Args:
        snapshot_id: ID of the snapshot to manage scenarios for
        snapshot_name: Name of the snapshot for display purposes
        
    Returns:
        tuple: (selected_scenario, run_optimization) if a scenario is selected and the user wants to run optimization,
               otherwise (None, False)
    """
    st.title("Scenario Management")
    st.markdown(f"Managing scenarios for snapshot: **{snapshot_name}**")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Create New Scenario")
        
        scenario_name = st.text_input("Scenario Name", placeholder="Enter a descriptive name for this scenario")
        
        num_vehicles = st.number_input(
            "Number of Vehicles",
            min_value=1,
            max_value=100,
            value=5
        )
        
        vehicle_capacity = st.number_input(
            "Vehicle Capacity",
            min_value=1,
            max_value=10000,
            value=100
        )
        
        constraints = st.text_area(
            "Additional Constraints (Optional)",
            placeholder="Enter any additional constraints or notes for this scenario",
            help="This is for documentation purposes only and doesn't affect the optimization."
        )
        
        if st.button("Save Scenario"):
            with st.spinner("Saving scenario..."):
                scenario_data = save_scenario(
                    snapshot_id=snapshot_id,
                    scenario_name=scenario_name,
                    num_vehicles=num_vehicles,
                    vehicle_capacity=vehicle_capacity,
                    constraints=constraints if constraints else None
                )
                
                # Add the scenario to the snapshot's list of scenarios
                add_scenario_to_snapshot(snapshot_id, scenario_data["scenario_id"])
                
                st.success(f"Scenario '{scenario_data['scenario_name']}' saved successfully!")
                st.rerun()
    
    with col2:
        st.subheader("What is a Scenario?")
        st.markdown("""
        A scenario is a specific configuration for solving the Vehicle Routing Problem:
        
        - **Number of Vehicles**: How many vehicles are available
        - **Vehicle Capacity**: Maximum load each vehicle can carry
        - **Constraints**: Any additional notes or constraints
        
        Create multiple scenarios to compare different configurations.
        """)
    
    st.subheader("Saved Scenarios")
    scenarios = get_scenarios_for_snapshot(snapshot_id)
    
    if not scenarios:
        st.info("No scenarios have been created yet for this snapshot. Create your first scenario above.")
        return None, False
    
    scenarios_df = pd.DataFrame([
        {
            "Scenario Name": s["scenario_name"],
            "Created": s["created_at"],
            "Vehicles": s["config"]["num_vehicles"],
            "Capacity": s["config"]["vehicle_capacity"],
            "Results": "Available" if s.get("optimization_results") else "Not Run"
        } for s in scenarios
    ])
    
    st.dataframe(scenarios_df, use_container_width=True)
    
    selected_index = st.selectbox(
        "Select a scenario to use:",
        options=range(len(scenarios)),
        format_func=lambda i: scenarios[i]["scenario_name"]
    )
    
    selected_scenario = scenarios[selected_index]
    
    st.subheader(f"Selected: {selected_scenario['scenario_name']}")
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Number of Vehicles", selected_scenario["config"]["num_vehicles"])
    with col2:
        st.metric("Vehicle Capacity", selected_scenario["config"]["vehicle_capacity"])
    
    if selected_scenario.get("constraints"):
        st.markdown(f"**Constraints:** {selected_scenario['constraints']}")
    
    has_results = selected_scenario.get("optimization_results") is not None
    
    if has_results:
        st.success("This scenario has been run. You can view the results or run it again.")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("View Results"):
                st.session_state.view_scenario_results = selected_scenario["scenario_id"]
                return selected_scenario, False
        with col2:
            if st.button("Run Again", type="primary"):
                return selected_scenario, True
    else:
        if st.button("Run Optimization", type="primary"):
            return selected_scenario, True
    
    return None, False
