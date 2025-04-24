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

# Add Customization Considered button and expander
if st.button("🎯 Customization Considered"):
    with st.expander("Customization History", expanded=True):
        if scenario.get('prompt_history') and len(scenario['prompt_history']) > 0:
            for i, attempt in enumerate(scenario['prompt_history'], 1):
                # Create a header row with attempt number and status badge
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.markdown(f"#### Attempt {i}")
                with col2:
                    if attempt.get('accepted', False):
                        st.success("✅ Accepted")
                    else:
                        st.warning("❌ Rejected")
                
                st.markdown("**🔍 Prompt:**")
                st.markdown(f"```\n{attempt.get('prompt', 'N/A')}\n```")
                
                st.markdown("**📋 Interpretation:**")
                if attempt.get('analysis'):
                    if attempt['analysis'].get('summary'):
                        st.markdown(attempt['analysis']['summary'])
                    
                    if attempt['analysis'].get('constraints'):
                        st.markdown("**Extracted Constraints:**")
                        for j, constraint in enumerate(attempt['analysis']['constraints'], 1):
                            st.markdown(f"{j}. {constraint}")
                    
                    if attempt['analysis'].get('notes'):
                        st.markdown("**Implementation Notes:**")
                        for note in attempt['analysis']['notes'].split('\n'):
                            if note.strip():
                                st.markdown(f"- {note.strip()}")
                else:
                    st.markdown("*No interpretation available*")
                
                # Display solver implementation notes if available
                if attempt.get('implementation_notes'):
                    st.markdown("**🧩 How Constraints Were Applied:**")
                    for note in attempt['implementation_notes']:
                        st.markdown(f"- {note}")
                
                if i < len(scenario['prompt_history']):
                    st.markdown("---")
        else:
            st.info("No custom constraints were added to this scenario.")

# Display route summary
st.subheader("Route Summary")
if 'route_summary' in results:
    route_summary_df = pd.DataFrame(results['route_summary'])
    st.dataframe(route_summary_df, use_container_width=True)

# Display detailed route information
st.subheader("Detailed Route Information")
if 'detailed_df' in results and results['detailed_df']:
    detailed_df = pd.DataFrame(results['detailed_df'])
    st.dataframe(detailed_df, use_container_width=True)

# Display visualizations
st.subheader("Route Visualizations")

# Create a map visualization if coordinates are available
if ('detailed_df' in results and results['detailed_df'] and 
    len(results['detailed_df']) > 0 and 
    all(col.lower() in results['detailed_df'][0] for col in ['latitude', 'longitude'])):
    
    detailed_df = pd.DataFrame(results['detailed_df'])
    
    fig = px.scatter_mapbox(
        detailed_df,
        lat='Latitude' if 'Latitude' in detailed_df.columns else 'latitude',
        lon='Longitude' if 'Longitude' in detailed_df.columns else 'longitude',
        color='Vehicle' if 'Vehicle' in detailed_df.columns else 'route_id',
        hover_name='Customer ID' if 'Customer ID' in detailed_df.columns else 'customer_id',
        hover_data=['Demand' if 'Demand' in detailed_df.columns else 'demand'],
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