import streamlit as st
import pandas as pd
import numpy as np
import io
import base64
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go
import folium
import os
import traceback
import time
import logging
import sys
import uuid
import json

current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

try:
    from .utils import safe_get_dataframe_value, ensure_dataframe, add_log_message, get_input_file_path_by_id
    from .utils import create_distance_matrix, get_download_link, create_folium_map, create_plotly_map
    from .solver import solve_cvrp, get_route_info
    from .nlp_processor import process_query
    from .input_repository import input_repository_page
    from .snapshot_manager import snapshot_management_ui, save_snapshot, get_snapshot_by_id
    from .scenario_manager import scenario_management_ui, save_scenario, update_scenario_results
    from .scenario_comparison import scenario_comparison_ui
    
    print("Using relative imports in app/main.py")
except ImportError:
    from utils import safe_get_dataframe_value, ensure_dataframe, add_log_message, get_input_file_path_by_id
    from utils import create_distance_matrix, get_download_link, create_folium_map, create_plotly_map
    from solver import solve_cvrp, get_route_info
    from nlp_processor import process_query
    from input_repository import input_repository_page
    from snapshot_manager import snapshot_management_ui, save_snapshot, get_snapshot_by_id
    from scenario_manager import scenario_management_ui, save_scenario, update_scenario_results
    from scenario_comparison import scenario_comparison_ui
    
    print("Using direct imports in app/main.py")

if __name__ == "__main__":
    st.set_page_config(
        page_title="Vehicle Routing Problem Solver",
        page_icon="🚚",
        layout="wide",
        initial_sidebar_state="expanded",
    )
else:
    from app.utils import safe_get_dataframe_value, ensure_dataframe, add_log_message, get_input_file_path_by_id
    from app.utils import create_distance_matrix, get_download_link, create_folium_map, create_plotly_map
    from app.solver import solve_cvrp, get_route_info
    from app.nlp_processor import process_query
    from app.input_repository import input_repository_page
    from app.snapshot_manager import snapshot_management_ui, save_snapshot, get_snapshot_by_id
    from app.scenario_manager import scenario_management_ui, save_scenario, update_scenario_results
    from app.scenario_comparison import scenario_comparison_ui
    
    st.markdown(
    """
    <style>
    /* Hide unwanted pages from sidebar */
    [data-testid="stSidebar"] ul li:has(a[href*="hidden_chat"]),
    [data-testid="stSidebar"] ul li:has(a[href*="init"]) {
        display: none !important;
    }
    
    /* Move navigation to top */
    section[data-testid="stSidebar"] div.element-container:has(div.stMarkdown h3:contains("Navigation")) {
        order: -1;
    }
    </style>
    """,
    unsafe_allow_html=True
)

    try:
        from streamlit_folium import folium_static
        FOLIUM_AVAILABLE = True
    except ImportError:
        FOLIUM_AVAILABLE = False
        st.warning("streamlit-folium package not available. Folium maps will be disabled. Please use Plotly maps instead.")

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    logger = logging.getLogger("CVRP-Solver")

    if 'app_mode' not in st.session_state:
        st.session_state.app_mode = 'input_repository'

    if 'selected_file' not in st.session_state:
        st.session_state.selected_file = None
        
    if 'selected_df' not in st.session_state:
        st.session_state.selected_df = None
        
    if 'selected_snapshot' not in st.session_state:
        st.session_state.selected_snapshot = None
    
    if 'selected_scenario' not in st.session_state:
        st.session_state.selected_scenario = None
        
    if 'optimization_results' not in st.session_state:
        st.session_state.optimization_results = None
        
    if 'view_scenario_results' not in st.session_state:
        st.session_state.view_scenario_results = None

    with st.sidebar:
        st.markdown("### Navigation")
        
        if st.button("Input Repository", key="nav_input_repo", use_container_width=True):
            st.session_state.app_mode = 'input_repository'
            st.switch_page("main.py")
        
        if st.button("Snapshot Management", key="nav_snapshot", use_container_width=True):
            if st.session_state.selected_file is not None:
                st.session_state.app_mode = 'snapshot_management'
                st.switch_page("main.py")
            else:
                st.error("Please select an input file first")
        
        if st.button("Scenario Management", key="nav_scenario", use_container_width=True):
            if st.session_state.selected_snapshot is not None:
                st.session_state.app_mode = 'scenario_management'
                st.switch_page("main.py")
            else:
                st.error("Please select a snapshot first")

    if st.session_state.app_mode == 'input_repository':
        selected_file, df = input_repository_page()
        
        if selected_file is not None and df is not None:
            st.session_state.selected_file = selected_file
            st.session_state.selected_df = df
            st.session_state.app_mode = 'snapshot_management'
            st.switch_page("main.py")
        
        st.stop()

    if st.session_state.app_mode == 'snapshot_management':
        if st.session_state.selected_file is None:
            st.error("No input file selected. Please select an input file first.")
            st.session_state.app_mode = 'input_repository'
            st.switch_page("main.py")
            
        selected_snapshot, create_scenario = snapshot_management_ui(st.session_state.selected_file)
        
        if selected_snapshot is not None:
            st.session_state.selected_snapshot = selected_snapshot
            
            if create_scenario:
                st.session_state.app_mode = 'scenario_management'
                st.switch_page("main.py")
        
        if st.button("Return to Input Repository"):
            st.session_state.app_mode = 'input_repository'
            st.switch_page("main.py")
        
        st.stop()

    if st.session_state.app_mode == 'scenario_management':
        if st.session_state.selected_snapshot is None:
            st.error("No snapshot selected. Please select a snapshot first.")
            st.session_state.app_mode = 'snapshot_management'
            st.switch_page("main.py")
            
        selected_scenario, run_optimization = scenario_management_ui(
            snapshot_id=st.session_state.selected_snapshot['snapshot_id'],
            snapshot_name=st.session_state.selected_snapshot['snapshot_name']
        )
        
        if selected_scenario is not None:
            st.session_state.selected_scenario = selected_scenario
            
            if run_optimization:
                st.session_state.app_mode = 'optimization'
                st.switch_page("main.py")
            
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Return to Snapshot Management"):
                st.session_state.app_mode = 'snapshot_management'
                st.switch_page("main.py")
        with col2:
            if st.button("Return to Input Repository"):
                st.session_state.app_mode = 'input_repository'
                st.switch_page("main.py")
        
        st.stop()

    if st.session_state.app_mode == 'view_results':
        st.title("Optimization Results")

        if st.session_state.selected_scenario is None:
            st.error("No scenario selected to view results.")
            st.session_state.app_mode = 'scenario_management'
            st.switch_page("main.py")
            st.stop()
        
        results = st.session_state.selected_scenario.get("optimization_results", None)
        
        if not results:
            st.warning("No saved optimization results found for this scenario.")
            st.session_state.app_mode = 'scenario_management'
            st.switch_page("main.py")
            st.stop()
        
        st.success(f"Results for: {st.session_state.selected_scenario['scenario_name']}")
        
        st.metric("Total Distance (km)", f"{results['total_distance']:.2f}")
        st.metric("Total Demand Delivered", results['total_demand'])
        st.metric("Capacity Utilization", f"{results['capacity_utilization']:.2f}%")
        
        st.markdown("### Route Summary")
        st.dataframe(pd.DataFrame(results['route_summary']))
        
        st.markdown("Return to [Scenario Management](main.py) to re-run or select another.")
        
        if st.button("Back to Scenarios"):
            st.session_state.app_mode = 'scenario_management'
            st.switch_page("main.py")
        
        st.stop()

        if st.session_state.selected_scenario is None:
            st.error("No scenario selected. Please select a scenario first.")
            st.session_state.app_mode = 'scenario_management'
            st.switch_page("main.py")
        
        try:
            from .scenario_manager import get_scenario_by_id
        except ImportError:
            from scenario_manager import get_scenario_by_id
            
        scenario_id = st.session_state.selected_scenario.get('scenario_id')
        if scenario_id:
            fresh_scenario = get_scenario_by_id(scenario_id)
            if fresh_scenario:
                st.session_state.selected_scenario = fresh_scenario
                st.session_state.optimization_results = fresh_scenario.get('optimization_results', {})
                add_log_message(f"Loaded optimization results from disk for scenario {fresh_scenario.get('scenario_name')}")
        
        st.title("Scenario Results")
        st.success(f"Viewing results for scenario: {st.session_state.selected_scenario['scenario_name']}")
        
        scenario_results = st.session_state.optimization_results
        
        if not scenario_results:
            st.error("No results found for this scenario.")
            if st.button("Return to Scenario Management"):
                st.session_state.app_mode = 'scenario_management'
                st.switch_page("main.py")
            st.stop()
    
        optimization_results = st.session_state.get('optimization_results', {})
        route_info = optimization_results.get('route_info')
        solution_data = optimization_results.get('solution_data')
        kpi_df = optimization_results.get('kpi_df')
        detailed_df = optimization_results.get('detailed_df')
        
        kpi_df = ensure_dataframe(kpi_df)
        detailed_df = ensure_dataframe(detailed_df)
    
        vehicle_capacity = None
        if 'config' in st.session_state.selected_scenario and 'vehicle_capacity' in st.session_state.selected_scenario['config']:
            vehicle_capacity = st.session_state.selected_scenario['config']['vehicle_capacity']
        elif 'vehicle_capacity' in optimization_results:
            vehicle_capacity = optimization_results['vehicle_capacity']
        
        if not vehicle_capacity:
            st.warning("Vehicle capacity not found in scenario config or optimization results.")
            vehicle_capacity = 100  # Default value
    
        total_distance = scenario_results.get("total_distance", 0)
        total_customers = scenario_results.get("total_customers", 0)
        total_demand = scenario_results.get("total_demand", 0)
        capacity_utilization = scenario_results.get("capacity_utilization", 0)
        
        route_summary = scenario_results.get("route_summary", [])
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Distance (km)", f"{total_distance:.2f}")
        with col2:
            st.metric("Total Customers Served", total_customers)
        with col3:
            st.metric("Total Demand Delivered", total_demand)
        with col4:
            st.metric("Capacity Utilization", f"{capacity_utilization:.2f}%")
        
        # If route_summary is not available, generate it from route_info
        if not route_summary and route_info:
            route_summary = []
            for route in route_info:
                route_summary.append({
                    'Vehicle': f"Vehicle {route['vehicle_id']}",
                    'Stops': len(route['stops']) if 'stops' in route else 0,
                    'Total Distance (km)': round(route['total_distance'], 2),
                    'Total Demand': route['total_demand'],
                    'Capacity Utilization (%)': round(route['total_demand'] / vehicle_capacity * 100, 2)
                })
        
        st.subheader("Route Summary")
        if route_summary:
            route_df = pd.DataFrame(route_summary)
            st.dataframe(route_df)
        
        if route_info:
            st.markdown("### Route Paths")
            for route in route_info:
                if 'route_text' in route:
                    st.markdown(f"**{route['route_text']}**")
                elif 'stops' in route:
                    stops = [stop['customer_id'] for stop in route['stops']] if 'stops' in route else []
                    stops_str = "Depot → " + " → ".join(stops) + " → Depot" if stops else "Depot → Depot"
                    st.markdown(f"**Vehicle {route['vehicle_id']}: {stops_str}**")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Return to Scenario Management"):
                st.session_state.app_mode = 'scenario_management'
                st.switch_page("main.py")
    
        with col2:
            if st.button("Chat with Assistant"):
                st.session_state.app_mode = 'chat_assistant'
                st.switch_page("pages/Chat_Assistant.py")
        
        st.stop()

if st.session_state.app_mode == 'scenario_comparison':
    if st.session_state.selected_snapshot is None:
        st.error("No snapshot selected. Please select a snapshot first.")
        st.session_state.app_mode = 'snapshot_management'
        st.switch_page("main.py")
    
    scenario_comparison_ui(
        snapshot_id=st.session_state.selected_snapshot['snapshot_id'],
        snapshot_name=st.session_state.selected_snapshot['snapshot_name']
    )
    
    st.stop()

if st.session_state.app_mode == 'optimization':
    if not st.session_state.get("optimization_results") and st.session_state.get("selected_scenario"):
        from .scenario_manager import get_scenario_by_id
        scenario = get_scenario_by_id(st.session_state.selected_scenario["scenario_id"])
        st.session_state.optimization_results = scenario.get("optimization_results", {})
        st.toast("✅ Optimization results loaded in main.py")
        st.success("✅ Optimization results loaded from saved scenario")
        
    if st.session_state.selected_scenario is None:
        st.error("No scenario selected. Please select a scenario first.")
        st.session_state.app_mode = 'scenario_management'
        st.switch_page("main.py")
    
    from .scenario_manager import get_scenario_by_id
    scenario_id = st.session_state.selected_scenario.get('scenario_id')
    if scenario_id:
        fresh_scenario = get_scenario_by_id(scenario_id)
        if fresh_scenario:
            st.session_state.selected_scenario = fresh_scenario
            if ('optimization_results' not in st.session_state or not st.session_state.optimization_results) and 'optimization_results' in fresh_scenario:
                st.session_state.optimization_results = fresh_scenario.get('optimization_results', {})
                add_log_message(f"Loaded optimization results from disk for scenario {fresh_scenario.get('scenario_name')}")
    
    if 'optimization_results' in st.session_state and st.session_state.optimization_results:
        add_log_message("Using existing optimization results from session state")
        st.session_state.app_mode = 'view_results'
        st.switch_page("main.py")
        st.stop()
    
    add_log_message("No existing results found, running new optimization")
    
    input_file_id = st.session_state.selected_scenario['snapshot_id']
    input_file_path = get_input_file_path_by_id(input_file_id)
    
    if not input_file_path or not os.path.exists(input_file_path):
        st.error(f"Input file not found for snapshot ID: {input_file_id}")
        if st.button("Return to Scenario Management"):
            st.session_state.app_mode = 'scenario_management'
            st.switch_page("main.py")
        st.stop()
    
    try:
        df = pd.read_csv(input_file_path)
        st.write(f"Loaded input data with {len(df)} rows")
    except Exception as e:
        st.error(f"Error loading input data: {str(e)}")
        if st.button("Return to Scenario Management"):
            st.session_state.app_mode = 'scenario_management'
            st.switch_page("main.py")
        st.stop()
    
    vehicle_count = st.session_state.selected_scenario['config']['num_vehicles']
    vehicle_capacity = st.session_state.selected_scenario['config']['vehicle_capacity']
    
    st.session_state.selected_df = df
    

if st.session_state.app_mode == 'chat_assistant':
    if st.session_state.selected_snapshot is None:
        st.error("No snapshot selected. Please select a snapshot first.")
        st.session_state.app_mode = 'snapshot_management'
        st.switch_page("main.py")
    
    from .snapshot_manager import get_snapshot_by_id
    snapshot_id = st.session_state.selected_snapshot.get('snapshot_id')
    if snapshot_id:
        fresh_snapshot = get_snapshot_by_id(snapshot_id)
        if fresh_snapshot:
            st.session_state.selected_snapshot = fresh_snapshot
            add_log_message(f"Loaded fresh snapshot data for {fresh_snapshot.get('snapshot_name')}")
    
    st.title(f"Chat Assistant for {st.session_state.selected_snapshot['snapshot_name']}")
    st.markdown("Ask questions about scenarios in this snapshot or compare scenario results.")
    
    if st.button("Return to Snapshot Management"):
        st.session_state.app_mode = 'snapshot_management'
        st.switch_page("main.py")
    
    st.switch_page("pages/Chat_Assistant.py")
    st.stop()

st.title("Capacitated Vehicle Routing Problem (CVRP) Solver")
st.markdown("""
This app solves the Capacitated Vehicle Routing Problem (CVRP) using Google OR-Tools.
Configure the parameters and get optimized routes for your vehicles.
""")


if st.session_state.selected_scenario:
    scenario_config = st.session_state.selected_scenario['config']
    
    st.success(f"Using scenario: {st.session_state.selected_scenario['scenario_name']}")
    st.info(f"Based on snapshot: {st.session_state.selected_scenario['snapshot_id']}")
    
    vehicle_count = scenario_config['num_vehicles']
    vehicle_capacity = scenario_config['vehicle_capacity']
    use_sample_data = False
else:
    vehicle_count = 5
    vehicle_capacity = 100
    use_sample_data = False

if st.session_state.selected_df is not None or use_sample_data:
    if use_sample_data:
        data = {
            'CustomerID': ['Depot'] + [f'C{i}' for i in range(1, 21)],
            'Latitude': [40.7128] + [40.7128 + (np.random.random() - 0.5) * 0.1 for _ in range(20)],
            'Longitude': [-74.0060] + [-74.0060 + (np.random.random() - 0.5) * 0.1 for _ in range(20)],
            'Demand': [0] + [int(np.random.randint(5, 30)) for _ in range(20)]
        }
        df = pd.DataFrame(data)
        st.info("Using sample data with random coordinates around New York City.")
    else:
        df = ensure_dataframe(st.session_state.selected_df)
        
        required_columns = ['CustomerID', 'Latitude', 'Longitude', 'Demand']
        if df.empty or not all(col in df.columns for col in required_columns):
            st.error(f"CSV file must contain the following columns: {', '.join(required_columns)}")
            st.stop()
    
    st.subheader("Customer Data")
    st.dataframe(df)
    
    if 'log_messages' not in st.session_state:
        st.session_state.log_messages = []
        
    if 'chat_messages' not in st.session_state:
        st.session_state.chat_messages = []
    
    log_container = st.container()
    
    def add_log_message(message, level="INFO"):
        """Add a message to the log with timestamp and level"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        if level == "INFO":
            logging.info(message)
            formatted_message = f"{timestamp} - INFO: {message}"
        elif level == "ERROR":
            logging.error(message)
            formatted_message = f"{timestamp} - ERROR: {message}"
        elif level == "WARNING":
            logging.warning(message)
            formatted_message = f"{timestamp} - WARNING: {message}"
        else:
            logging.debug(message)
            formatted_message = f"{timestamp} - DEBUG: {message}"
        
        if 'log_messages' not in st.session_state:
            st.session_state.log_messages = []
            
        st.session_state.log_messages.append(formatted_message)
        
        return message
    
    with log_container:
        log_expander = st.expander("Solver Log", expanded=False)
        with log_expander:
            log_text = "\n".join(st.session_state.log_messages)
            st.text_area("Log Messages", value=log_text, height=300, key="log_display")
    
    if 'optimization_results' in st.session_state and st.session_state.optimization_results:
        add_log_message("Using existing optimization results from scenario")
        
        try:
            solution_data = st.session_state.optimization_results.get("solution_data")
            route_info = st.session_state.optimization_results.get("route_info")
            kpi_df = st.session_state.optimization_results.get("kpi_df")
            detailed_df = st.session_state.optimization_results.get("detailed_df")
            
            vehicle_capacity = st.session_state.optimization_results.get("vehicle_capacity")
            if vehicle_capacity is None and st.session_state.selected_scenario and 'config' in st.session_state.selected_scenario:
                vehicle_capacity = st.session_state.selected_scenario['config'].get('vehicle_capacity', 100)
                add_log_message(f"Using vehicle capacity from scenario config: {vehicle_capacity}")
            
            total_distance = st.session_state.optimization_results.get("total_distance", 0)
            total_customers = st.session_state.optimization_results.get("total_customers", 0)
            total_demand = st.session_state.optimization_results.get("total_demand", 0)
            capacity_utilization = st.session_state.optimization_results.get("capacity_utilization", 0)
            
            route_summary = st.session_state.optimization_results.get("route_summary", [])
            
            has_results = (route_info is not None) or (len(route_summary) > 0)
            
            if has_results:
                st.success("Loaded previously optimized results")
                
                st.subheader("Optimization Results")
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Total Distance (km)", f"{total_distance:.2f}")
                with col2:
                    st.metric("Total Customers Served", total_customers)
                with col3:
                    st.metric("Total Demand Delivered", total_demand)
                with col4:
                    st.metric("Overall Capacity Utilization", f"{capacity_utilization:.2f}%")
                
                st.markdown("### Route Details")
                
                # If route_summary is not available, generate it from route_info
                if not route_summary and route_info:
                    route_summary = []
                    for route in route_info:
                        route_summary.append({
                            'Vehicle': f"Vehicle {route['vehicle_id']}",
                            'Stops': len(route['stops']),
                            'Total Distance (km)': round(route['total_distance'], 2),
                            'Total Demand': route['total_demand'],
                            'Capacity Utilization (%)': round(route['total_demand'] / vehicle_capacity * 100, 2)
                        })
                
                route_df = pd.DataFrame(route_summary)
                st.dataframe(route_df)
                
                if route_info:
                    st.markdown("### Route Paths")
                    for route in route_info:
                        st.markdown(f"**{route['route_text']}**")
                
                tab1, tab2, tab3, tab4, tab5 = st.tabs(["KPIs & Visualizations", "Interactive Map (Folium)", "Interactive Map (Plotly)", "Export Results", "Chat"])
                
                
                if st.button("Run New Optimization"):
                    st.session_state.optimization_results = None
                    st.rerun()
                
                if st.session_state.selected_scenario and 'scenario_id' in st.session_state.selected_scenario:
                    if st.button("Save Results to Scenario"):
                        scenario_id = st.session_state.selected_scenario['scenario_id']
                        
                        results_data = {
                            "solution_data": solution_data,
                            "route_info": route_info,
                            "kpi_df": kpi_df.to_dict() if isinstance(kpi_df, pd.DataFrame) else kpi_df,
                            "detailed_df": detailed_df.to_dict() if isinstance(detailed_df, pd.DataFrame) else detailed_df,
                            "vehicle_capacity": vehicle_capacity,
                            "total_distance": total_distance,
                            "total_customers": total_customers,
                            "total_demand": total_demand,
                            "capacity_utilization": capacity_utilization,
                            "route_summary": route_summary
                        }
                        
                        success = update_scenario_results(scenario_id, results_data)
                        if success:
                            st.success(f"Results saved to scenario {st.session_state.selected_scenario['scenario_name']}")
                        else:
                            st.error("Failed to save results to scenario")
                
                st.stop()
        except Exception as e:
            st.error(f"Error displaying existing results: {str(e)}")
            st.session_state.optimization_results = None
            st.warning("Will run new optimization instead")
    
    if st.button("Run Optimization"):
        st.session_state.log_messages = []
        st.session_state.expand_logs = True
        
        with st.spinner("Calculating optimal routes..."):
            try:
                add_log_message("Starting optimization process...")
                add_log_message(f"Number of customers: {len(df) - 1}")
                add_log_message(f"Number of vehicles: {vehicle_count}")
                add_log_message(f"Vehicle capacity: {vehicle_capacity}")
                
                if 'Demand' in df.columns and not df.empty:
                    total_demand = sum(df['Demand'])
                else:
                    total_demand = 0
                    add_log_message("Warning: No demand data found", "WARNING")
                
                total_capacity = vehicle_count * vehicle_capacity
                add_log_message(f"Total demand: {total_demand}")
                add_log_message(f"Total capacity: {total_capacity}")
                
                if total_demand > total_capacity:
                    error_msg = f"Total demand ({total_demand}) exceeds total capacity ({total_capacity}). The problem is infeasible."
                    add_log_message(error_msg, "ERROR")
                    st.error(error_msg)
                    st.error("Try increasing the number of vehicles or vehicle capacity.")
                    st.stop()
                
                add_log_message("Creating distance matrix...")
                distance_matrix = create_distance_matrix(df)
                add_log_message(f"Distance matrix shape: {distance_matrix.shape}")
                
                add_log_message("Extracting demand values...")
                if 'Demand' in df.columns and not df.empty:
                    demands = df['Demand'].tolist()
                else:
                    demands = []
                    add_log_message("Warning: No demand data found", "WARNING")
                
                add_log_message("Solving CVRP problem using OR-Tools...")
                start_time = time.time()
                solution_data = solve_cvrp(distance_matrix, demands, vehicle_count, vehicle_capacity)
                solve_time = time.time() - start_time
                add_log_message(f"Solver finished in {solve_time:.2f} seconds")
                
                if solution_data is None:
                    error_msg = "No feasible solution found."
                    add_log_message(error_msg, "ERROR")
                    st.error(error_msg)
                    st.error("Possible reasons:")
                    st.error("1. Not enough vehicles to serve all customers")
                    st.error("2. Vehicle capacity is too small for some customer demands")
                    st.error("3. The solver couldn't find a solution within the time limit")
                    st.error("Try increasing the number of vehicles, vehicle capacity, or simplifying the problem.")
                    st.stop()
                
                add_log_message("Solution found! Processing route information...")
                route_info = get_route_info(solution_data, df)
                
                if not route_info or len(route_info) == 0:
                    error_msg = "Failed to extract route information from solution."
                    add_log_message(error_msg, "ERROR")
                    st.error(error_msg)
                    st.stop()
                
                add_log_message(f"Number of routes: {len(route_info)}")
                for i, route in enumerate(route_info):
                    add_log_message(f"Route {i+1}: {len(route['stops'])} stops, {route['total_distance']:.2f} km, {route['total_demand']} demand")
                
                add_log_message("Optimization completed successfully!", "INFO")
                
                st.subheader("Optimization Results")
                
                try:
                    total_distance = sum(route['total_distance'] for route in route_info)
                    total_customers = sum(len(route['stops']) for route in route_info)
                    total_demand = sum(route['total_demand'] for route in route_info)
                    total_capacity = vehicle_count * vehicle_capacity
                    capacity_utilization = (total_demand / total_capacity) * 100
                    
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Total Distance (km)", f"{total_distance:.2f}")
                    with col2:
                        st.metric("Total Customers Served", total_customers)
                    with col3:
                        st.metric("Total Demand Delivered", total_demand)
                    with col4:
                        st.metric("Overall Capacity Utilization", f"{capacity_utilization:.2f}%")
                    
                    st.markdown("### Route Details")
                except Exception as e:
                    error_msg = f"An error occurred while calculating summary metrics: {str(e)}"
                    add_log_message(error_msg, "ERROR")
                    st.error(error_msg)
            
            except Exception as e:
                error_msg = f"An error occurred during optimization: {str(e)}"
                add_log_message(error_msg, "ERROR")
                add_log_message(traceback.format_exc(), "ERROR")
                st.error(error_msg)
                st.error("Please check the Solver Log for details.")
                st.stop()
            
            try:
                route_summary = []
                for route in route_info:
                    route_summary.append({
                        'Vehicle': f"Vehicle {route['vehicle_id']}",
                        'Stops': len(route['stops']),
                        'Total Distance (km)': round(route['total_distance'], 2),
                        'Total Demand': route['total_demand'],
                        'Capacity Utilization (%)': round(route['total_demand'] / vehicle_capacity * 100, 2)
                    })
                
                route_df = pd.DataFrame(route_summary)
                st.dataframe(route_df)
            except Exception as e:
                error_msg = f"An error occurred while displaying route summary: {str(e)}"
                add_log_message(error_msg, "ERROR")
                st.error(error_msg)
            
            try:
                st.markdown("### Route Paths")
                for route in route_info:
                    st.markdown(f"**{route['route_text']}**")
            except Exception as e:
                error_msg = f"An error occurred while displaying route paths: {str(e)}"
                add_log_message(error_msg, "ERROR")
                st.error(error_msg)
            
            try:
                tab1, tab2, tab3, tab4, tab5 = st.tabs(["KPIs & Visualizations", "Interactive Map (Folium)", "Interactive Map (Plotly)", "Export Results", "Chat"])
            except Exception as e:
                error_msg = f"An error occurred while creating tabs: {str(e)}"
                add_log_message(error_msg, "ERROR")
                st.error(error_msg)
                st.stop()
            
            try:
                with tab1:
                    st.markdown("### Key Performance Indicators (KPIs)")
                    
                    kpi_df = pd.DataFrame([
                        {
                            'Vehicle': f"Vehicle {route['vehicle_id']}",
                            'Customers Visited': len(route['stops']),
                            'Distance (km)': round(route['total_distance'], 2),
                            'Demand Delivered': route['total_demand'],
                            'Capacity': vehicle_capacity,
                            'Capacity Utilization (%)': round(route['total_demand'] / vehicle_capacity * 100, 2)
                        } for route in route_info
                    ])
                    
                    total_row = pd.DataFrame([{
                        'Vehicle': 'TOTAL',
                        'Customers Visited': kpi_df['Customers Visited'].sum(),
                        'Distance (km)': kpi_df['Distance (km)'].sum(),
                        'Demand Delivered': kpi_df['Demand Delivered'].sum(),
                        'Capacity': kpi_df['Capacity'].sum(),
                        'Capacity Utilization (%)': round(kpi_df['Demand Delivered'].sum() / kpi_df['Capacity'].sum() * 100, 2)
                    }])
                    
                    kpi_df = pd.concat([kpi_df, total_row], ignore_index=True)
                    st.dataframe(kpi_df, use_container_width=True)
                    
                    st.markdown("### Visualizations")
                    
                    viz_col1, viz_col2 = st.columns(2)
                    
                    with viz_col1:
                        distance_fig = px.bar(
                            kpi_df[:-1],  # Exclude total row
                            x='Vehicle',
                            y='Distance (km)',
                            title='Distance Traveled per Vehicle',
                            color='Distance (km)',
                            color_continuous_scale='Viridis'
                        )
                        st.plotly_chart(distance_fig, use_container_width=True)
                    
                    with viz_col2:
                        utilization_fig = px.bar(
                            kpi_df[:-1],  # Exclude total row
                            x='Vehicle',
                            y='Capacity Utilization (%)',
                            title='Vehicle Capacity Utilization',
                            color='Capacity Utilization (%)',
                            color_continuous_scale='RdYlGn'
                        )
                        st.plotly_chart(utilization_fig, use_container_width=True)
                    
                    demand_fig = px.pie(
                        kpi_df[:-1],  # Exclude total row
                        values='Demand Delivered',
                        names='Vehicle',
                        title='Demand Distribution Across Vehicles',
                        hole=0.4
                    )
                    st.plotly_chart(demand_fig, use_container_width=True)
            except Exception as e:
                error_msg = f"An error occurred while displaying KPIs and visualizations: {str(e)}"
                add_log_message(error_msg, "ERROR")
                st.error(error_msg)
            
            try:
                with tab2:
                    st.markdown("### Route Visualization (Folium)")
                    if FOLIUM_AVAILABLE:
                        m = create_folium_map(df, solution_data['routes'])
                        folium_static(m)
                    else:
                        st.warning("Folium map visualization is not available. Please use the Plotly map in the next tab.")
                        st.info("To enable Folium maps, make sure the 'streamlit-folium' package is installed.")
            except Exception as e:
                error_msg = f"An error occurred while displaying Folium map: {str(e)}"
                add_log_message(error_msg, "ERROR")
                st.error(error_msg)
            
            try:
                with tab3:
                    st.markdown("### Route Visualization (Plotly)")
                    fig = create_plotly_map(df, solution_data['routes'])
                    st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                error_msg = f"An error occurred while displaying Plotly map: {str(e)}"
                add_log_message(error_msg, "ERROR")
                st.error(error_msg)
            
            try:
                with tab4:
                    st.markdown("### Export Results")
                    
                    detailed_results = []
                    for route in route_info:
                        vehicle_id = route['vehicle_id']
                        for i, stop in enumerate(route['stops']):
                            detailed_results.append({
                                'Vehicle': f"Vehicle {vehicle_id}",
                                'Stop Number': i + 1,
                                'Customer ID': stop['customer_id'],
                                'Demand': stop['demand'],
                                'Latitude': safe_get_dataframe_value(df, stop['node_idx'], 'Latitude', 0),
                                'Longitude': safe_get_dataframe_value(df, stop['node_idx'], 'Longitude', 0)
                            })
                    
                    detailed_df = pd.DataFrame(detailed_results)
                    
                    optimization_results = {
                        'route_info': route_info,
                        'kpi_df': kpi_df,
                        'detailed_df': detailed_df,
                        'vehicle_capacity': vehicle_capacity,
                        'solution_data': solution_data
                    }
                    
                    st.session_state.optimization_results = optimization_results
                    
                    if st.session_state.selected_scenario:
                        scenario_id = st.session_state.selected_scenario['scenario_id']
                        add_log_message(f"Updating results for scenario: {st.session_state.selected_scenario['scenario_name']}", "INFO")
                        
                        scenario_results = {
                            'total_distance': total_distance,
                            'total_customers': total_customers,
                            'total_demand': total_demand,
                            'capacity_utilization': capacity_utilization,
                            'route_summary': route_summary,
                            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        }
                        
                        try:
                            update_success = update_scenario_results(scenario_id, scenario_results)
                            if update_success:
                                add_log_message("Scenario results updated successfully", "INFO")
                            else:
                                add_log_message("Failed to update scenario results", "WARNING")
                        except Exception as e:
                            add_log_message(f"Error updating scenario results: {str(e)}", "ERROR")
                            add_log_message(traceback.format_exc(), "ERROR")
                    
                    st.dataframe(detailed_df)
                    
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    
                    st.markdown(
                        get_download_link(
                            kpi_df, 
                            f"vrp_summary_{timestamp}.xlsx", 
                            "Download Route Summary"
                        ), 
                        unsafe_allow_html=True
                    )
                    
                    st.markdown(
                        get_download_link(
                            detailed_df, 
                            f"vrp_detailed_{timestamp}.xlsx", 
                            "Download Detailed Results"
                        ), 
                        unsafe_allow_html=True
                    )
            except Exception as e:
                error_msg = f"An error occurred while preparing export results: {str(e)}"
                add_log_message(error_msg, "ERROR")
                st.error(error_msg)
                
            try:
                if 'chat_messages' not in st.session_state:
                    st.session_state.chat_messages = []
                
                if 'active_tab' not in st.session_state:
                    st.session_state.active_tab = 0
                
                if 'chat_viz' not in st.session_state:
                    st.session_state.chat_viz = None
                
                if 'query_to_process' not in st.session_state:
                    st.session_state.query_to_process = None
                
                def add_chat_message(role, content, metadata=None):
                    timestamp = datetime.now().strftime("%H:%M:%S")
                    message = {
                        "role": role, 
                        "content": content, 
                        "timestamp": timestamp
                    }
                    if metadata:
                        message["metadata"] = metadata
                    st.session_state.chat_messages.append(message)
                
                def handle_chat_submit():
                    query = st.session_state.user_input
                    if query:
                        add_chat_message("user", query)
                        add_log_message(f"Processing chat query: '{query}'", "INFO")
                        
                        try:
                            result = process_query(
                                query=query,
                                route_info=route_info,
                                kpi_df=kpi_df,
                                detailed_df=detailed_df,
                                vehicle_capacity=vehicle_capacity
                            )
                            
                            add_log_message(f"Query processed with intent: {result['intent']}", "INFO")
                            
                            add_chat_message(
                                "assistant", 
                                result["response_text"], 
                                {"intent": result["intent"]}
                            )
                            
                            if result["visualization"]:
                                add_log_message("Generating visualization for query", "INFO")
                                st.session_state.chat_viz = result["visualization"]
                        
                        except Exception as e:
                            error_msg = f"An error occurred while processing your query: {str(e)}"
                            add_log_message(error_msg, "ERROR")
                            add_log_message(traceback.format_exc(), "ERROR")
                            add_chat_message("assistant", f"I'm sorry, I encountered an error: {str(e)}")
                        
                        st.session_state.user_input = ""
                
                tab_names = ["KPIs & Visualizations", "Interactive Map (Folium)", 
                            "Interactive Map (Plotly)", "Export Results", "Chat"]
                tabs = st.tabs(tab_names)
                
                with tabs[0]:
                    if st.session_state.active_tab == 0:
                        st.markdown("### Key Performance Indicators (KPIs)")
                        
                        kpi_df = pd.DataFrame([
                            {
                                'Vehicle': f"Vehicle {route['vehicle_id']}",
                                'Customers Visited': len(route['stops']),
                                'Distance (km)': round(route['total_distance'], 2),
                                'Demand Delivered': route['total_demand'],
                                'Capacity': vehicle_capacity,
                                'Capacity Utilization (%)': round(route['total_demand'] / vehicle_capacity * 100, 2)
                            } for route in route_info
                        ])
                        
                        total_row = pd.DataFrame([{
                            'Vehicle': 'TOTAL',
                            'Customers Visited': kpi_df['Customers Visited'].sum(),
                            'Distance (km)': kpi_df['Distance (km)'].sum(),
                            'Demand Delivered': kpi_df['Demand Delivered'].sum(),
                            'Capacity': kpi_df['Capacity'].sum(),
                            'Capacity Utilization (%)': round(kpi_df['Demand Delivered'].sum() / kpi_df['Capacity'].sum() * 100, 2)
                        }])
                        
                        kpi_df = pd.concat([kpi_df, total_row], ignore_index=True)
                        st.dataframe(kpi_df, use_container_width=True)
                        
                        st.markdown("### Visualizations")
                        
                        viz_col1, viz_col2 = st.columns(2)
                        
                        with viz_col1:
                            distance_fig = px.bar(
                                kpi_df[:-1],  # Exclude total row
                                x='Vehicle',
                                y='Distance (km)',
                                title='Distance Traveled per Vehicle',
                                color='Distance (km)',
                                color_continuous_scale='Viridis'
                            )
                            st.plotly_chart(distance_fig, use_container_width=True, key="distance_chart")
                        
                        with viz_col2:
                            utilization_fig = px.bar(
                                kpi_df[:-1],  # Exclude total row
                                x='Vehicle',
                                y='Capacity Utilization (%)',
                                title='Vehicle Capacity Utilization',
                                color='Capacity Utilization (%)',
                                color_continuous_scale='RdYlGn'
                            )
                            st.plotly_chart(utilization_fig, use_container_width=True, key="utilization_chart")
                        
                        demand_fig = px.pie(
                            kpi_df[:-1],  # Exclude total row
                            values='Demand Delivered',
                            names='Vehicle',
                            title='Demand Distribution Across Vehicles',
                            hole=0.4
                        )
                        st.plotly_chart(demand_fig, use_container_width=True, key="demand_chart")
                
                with tabs[1]:
                    if st.session_state.active_tab == 1:
                        st.markdown("### Route Visualization (Folium)")
                        if FOLIUM_AVAILABLE:
                            m = create_folium_map(df, solution_data['routes'])
                            folium_static(m)
                        else:
                            st.warning("Folium map visualization is not available. Please use the Plotly map in the next tab.")
                            st.info("To enable Folium maps, make sure the 'streamlit-folium' package is installed.")
                
                with tabs[2]:
                    if st.session_state.active_tab == 2:
                        st.markdown("### Route Visualization (Plotly)")
                        fig = create_plotly_map(df, solution_data['routes'])
                        st.plotly_chart(fig, use_container_width=True, key="plotly_map_chart")
                
                with tabs[3]:
                    if st.session_state.active_tab == 3:
                        st.markdown("### Export Results")
                        
                        detailed_results = []
                        for route in route_info:
                            vehicle_id = route['vehicle_id']
                            for i, stop in enumerate(route['stops']):
                                detailed_results.append({
                                    'Vehicle': f"Vehicle {vehicle_id}",
                                    'Stop Number': i + 1,
                                    'Customer ID': stop['customer_id'],
                                    'Demand': stop['demand'],
                                    'Latitude': safe_get_dataframe_value(df, stop['node_idx'], 'Latitude', 0),
                                    'Longitude': safe_get_dataframe_value(df, stop['node_idx'], 'Longitude', 0)
                                })
                        
                        detailed_df = pd.DataFrame(detailed_results)
                        
                        st.dataframe(detailed_df)
                        
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        
                        st.markdown(
                            get_download_link(
                                kpi_df, 
                                f"vrp_summary_{timestamp}.xlsx", 
                                "Download Route Summary"
                            ), 
                            unsafe_allow_html=True
                        )
                        
                        st.markdown(
                            get_download_link(
                                detailed_df, 
                                f"vrp_detailed_{timestamp}.xlsx", 
                                "Download Detailed Results"
                            ), 
                            unsafe_allow_html=True
                        )
                
                if 'chat_messages' not in st.session_state:
                    st.session_state.chat_messages = []
                
                if 'chat_viz' not in st.session_state:
                    st.session_state.chat_viz = None
                
                if 'chat_input' not in st.session_state:
                    st.session_state.chat_input = ""
                
                st.session_state.active_tab = 4
                
                def on_chat_input_change():
                    st.session_state.chat_input_value = st.session_state.chat_input_widget
                
                def on_send_button_click():
                    if st.session_state.chat_input_value:
                        query = st.session_state.chat_input_value
                        
                        add_chat_message("user", query)
                        add_log_message(f"Processing chat query: '{query}'", "INFO")
                        
                        try:
                            result = process_query(
                                query=query,
                                route_info=route_info,
                                kpi_df=kpi_df,
                                detailed_df=detailed_df,
                                vehicle_capacity=vehicle_capacity
                            )
                            
                            add_log_message(f"Query processed with intent: {result['intent']}", "INFO")
                            
                            add_chat_message(
                                "assistant", 
                                result["response_text"], 
                                {"intent": result["intent"]}
                            )
                            
                            if result["visualization"]:
                                add_log_message("Generating visualization for query", "INFO")
                                st.session_state.chat_viz = result["visualization"]
                        
                        except Exception as e:
                            error_msg = f"An error occurred while processing your query: {str(e)}"
                            add_log_message(error_msg, "ERROR")
                            add_log_message(traceback.format_exc(), "ERROR")
                            add_chat_message("assistant", f"I'm sorry, I encountered an error: {str(e)}")
                        
                        st.session_state.chat_input_value = ""
                        st.session_state.chat_input_widget = ""
                
                with tabs[4]:
                    st.markdown("### Chat with VRP Assistant")
                    st.markdown("Ask questions about your routes or request scenario analysis.")
                    
                    if 'optimization_results' not in st.session_state:
                        st.session_state.optimization_results = {}
                    
                    st.session_state.optimization_results = {
                        'route_info': route_info,
                        'kpi_df': kpi_df,
                        'detailed_df': detailed_df,
                        'vehicle_capacity': vehicle_capacity
                    }
                    
                    if st.button("Open Chat Assistant", key="open_chat_button"):
                        st.session_state.app_mode = 'chat_assistant'
                        st.switch_page("main.py")
                
            except Exception as e:
                error_msg = f"An error occurred in the chat interface: {str(e)}"
                add_log_message(error_msg, "ERROR")
                st.error(error_msg)
else:
    st.info("Please upload a CSV file with customer data or use the sample data option.")
    
    st.markdown("""
    
    The CSV file should contain the following columns:
    - **CustomerID**: Unique identifier for each customer
    - **Latitude**: Customer location latitude
    - **Longitude**: Customer location longitude
    - **Demand**: Customer demand (numeric)
    
    The first row (index 0) is assumed to be the depot.
    
    Example:
    ```
    CustomerID,Latitude,Longitude,Demand
    Depot,40.7128,-74.0060,0
    C1,40.7300,-74.0100,10
    C2,40.7200,-73.9900,15
    C3,40.7000,-74.0200,8
    ```
    """)
