import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import os
import sys
import json
import logging

st.set_page_config(
    page_title="Scenario Results",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
    [data-testid="stSidebar"] ul li:has(a[href*="hidden_chat"]),
    [data-testid="stSidebar"] ul li:has(a[href*="init"]) {
        display: none !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from app.scenario_manager import get_scenario_by_id

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("CVRP-Results")

def add_log_message(message, level="INFO"):
    """Add a message to the log with timestamp"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    log_message = f"{timestamp} - {level}: {message}"
    
    if level == "ERROR":
        logger.error(message)
    elif level == "WARNING":
        logger.warning(message)
    else:
        logger.info(message)
    
    if 'log_messages' not in st.session_state:
        st.session_state.log_messages = []
    
    st.session_state.log_messages.append(log_message)

st.title("Scenario Results")

if 'view_scenario_results' not in st.session_state or st.session_state.view_scenario_results is None:
    st.warning("No scenario selected for viewing results.")
    # Clear the view results state
    if 'view_scenario_results' in st.session_state:
        st.session_state.view_scenario_results = None
    if st.button("Return to Scenario Management"):
        st.session_state.app_mode = 'scenario_management'
        st.switch_page("main.py")
    st.stop()

scenario_id = st.session_state.view_scenario_results
scenario = get_scenario_by_id(scenario_id)

if not scenario:
    st.error("Could not find the selected scenario.")
    # Clear the view results state
    st.session_state.view_scenario_results = None
    if st.button("Return to Scenario Management"):
        st.session_state.app_mode = 'scenario_management'
        st.switch_page("main.py")
    st.stop()

st.markdown(f"### Results for Scenario: **{scenario['scenario_name']}**")

if not scenario.get('optimization_results'):
    st.warning("No optimization results available for this scenario.")
    # Clear the view results state
    st.session_state.view_scenario_results = None
    if st.button("Return to Scenario Management"):
        st.session_state.app_mode = 'scenario_management'
        st.switch_page("main.py")
    st.stop()

results = scenario['optimization_results']

# Display key metrics
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Total Distance", f"{results.get('total_distance', 0):.2f} km")
with col2:
    st.metric("Total Customers", results.get('total_customers', 0))
with col3:
    st.metric("Total Demand", results.get('total_demand', 0))
with col4:
    st.metric("Capacity Utilization", f"{results.get('capacity_utilization', 0):.1f}%")

# Display route summary
st.subheader("Route Summary")
if 'route_summary' in results:
    route_summary_df = pd.DataFrame(results['route_summary'])
    st.dataframe(route_summary_df, use_container_width=True)

# Display detailed route information
st.subheader("Detailed Route Information")
if 'detailed_df' in results:
    detailed_df = pd.DataFrame(results['detailed_df'])
    st.dataframe(detailed_df, use_container_width=True)

# Display visualizations
st.subheader("Route Visualizations")

# Create a map visualization if coordinates are available
if 'detailed_df' in results and all(col in results['detailed_df'][0] for col in ['latitude', 'longitude']):
    detailed_df = pd.DataFrame(results['detailed_df'])
    
    fig = px.scatter_mapbox(
        detailed_df,
        lat='latitude',
        lon='longitude',
        color='route_id',
        hover_name='customer_id',
        hover_data=['demand'],
        zoom=10,
        height=600
    )
    
    fig.update_layout(mapbox_style="open-street-map")
    fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
    st.plotly_chart(fig, use_container_width=True)

# Display navigation buttons
col1, col2 = st.columns(2)
with col1:
    if st.button("Return to Scenario Management"):
        # Clear the view results state
        st.session_state.view_scenario_results = None
        st.session_state.app_mode = 'scenario_management'
        st.switch_page("main.py")
with col2:
    if st.button("Return to Input Repository"):
        # Clear the view results state
        st.session_state.view_scenario_results = None
        st.session_state.app_mode = 'input_repository'
        st.switch_page("main.py")

# Display solver log if available
if 'log_messages' in st.session_state:
    with st.expander("Solver Log", expanded=False):
        log_text = "\n".join(st.session_state.log_messages)
        st.text_area("Log", value=log_text, height=300, key="log_area") 