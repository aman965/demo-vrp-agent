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
    page_title="Scenario Comparison",
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
from app.snapshot_manager import get_snapshot_by_id

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("CVRP-Comparison")

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

st.title("Scenario Comparison")

if 'selected_snapshot' not in st.session_state or st.session_state.selected_snapshot is None:
    st.warning("No snapshot selected. Please select a snapshot first.")
    if st.button("Return to Input Repository"):
        st.session_state.app_mode = 'input_repository'
        st.switch_page("main.py")
    st.stop()

snapshot = st.session_state.selected_snapshot
st.markdown(f"### Comparing Scenarios for Snapshot: **{snapshot['snapshot_name']}**")

if not snapshot.get('scenarios', []):
    st.warning("This snapshot has no scenarios to compare. Please create at least two scenarios first.")
    if st.button("Return to Scenario Management"):
        st.session_state.app_mode = 'scenario_management'
        st.switch_page("main.py")
    st.stop()

if len(snapshot.get('scenarios', [])) < 2:
    st.warning("This snapshot has only one scenario. Please create at least one more scenario to compare.")
    if st.button("Return to Scenario Management"):
        st.session_state.app_mode = 'scenario_management'
        st.switch_page("main.py")
    st.stop()

scenario_ids = snapshot.get('scenarios', [])
scenarios = []

for scenario_id in scenario_ids:
    scenario_data = get_scenario_by_id(scenario_id)
    if scenario_data and 'optimization_results' in scenario_data:
        scenarios.append(scenario_data)
    else:
        add_log_message(f"Scenario {scenario_id} has no optimization results or could not be loaded", "WARNING")

if len(scenarios) < 2:
    st.warning("Not enough scenarios with optimization results to compare. Please run optimization for at least two scenarios.")
    if st.button("Return to Scenario Management"):
        st.session_state.app_mode = 'scenario_management'
        st.switch_page("main.py")
    st.stop()

st.subheader("Select Scenarios to Compare")
selected_scenario_indices = st.multiselect(
    "Choose scenarios to compare:",
    options=range(len(scenarios)),
    default=range(min(len(scenarios), 2)),
    format_func=lambda i: scenarios[i]['scenario_name']
)

if not selected_scenario_indices or len(selected_scenario_indices) < 2:
    st.warning("Please select at least two scenarios to compare.")
    if st.button("Return to Scenario Management"):
        st.session_state.app_mode = 'scenario_management'
        st.switch_page("main.py")
    st.stop()

selected_scenarios = [scenarios[i] for i in selected_scenario_indices]

st.subheader("Key Performance Indicators Comparison")

comparison_data = []
for scenario in selected_scenarios:
    if 'optimization_results' in scenario and 'kpi_df' in scenario['optimization_results']:
        kpi_df = pd.DataFrame(scenario['optimization_results']['kpi_df'])
        
        kpi_df['Scenario'] = scenario['scenario_name']
        
        comparison_data.append(kpi_df)
    else:
        st.warning(f"Scenario '{scenario['scenario_name']}' has no KPI data.")

if not comparison_data:
    st.error("No KPI data available for the selected scenarios.")
    if st.button("Return to Scenario Management"):
        st.session_state.app_mode = 'scenario_management'
        st.switch_page("main.py")
    st.stop()

combined_kpi_df = pd.concat(comparison_data, ignore_index=True)

st.dataframe(combined_kpi_df)

st.subheader("Visualization Comparison")

fig_distance = px.bar(
    combined_kpi_df, 
    x='Vehicle', 
    y='Distance', 
    color='Vehicle',
    title='Distance by Vehicle',
    labels={'Distance': 'Distance (km)'}
)
st.plotly_chart(fig_distance, use_container_width=True)

fig_util = px.bar(
    combined_kpi_df, 
    x='Vehicle', 
    y='Utilization', 
    color='Vehicle',
    title='Capacity Utilization by Vehicle',
    labels={'Utilization': 'Utilization (%)'}
)
fig_util.update_layout(yaxis_range=[0, 100])
st.plotly_chart(fig_util, use_container_width=True)

fig_customers = px.bar(
    combined_kpi_df, 
    x='Vehicle', 
    y='Customers', 
    color='Vehicle',
    title='Customers Served by Vehicle'
)
st.plotly_chart(fig_customers, use_container_width=True)

st.subheader("Navigation")
col1, col2 = st.columns(2)

with col1:
    if st.button("Return to Scenario Management"):
        st.session_state.app_mode = 'scenario_management'
        st.switch_page("main.py")

with col2:
    if st.button("Return to Input Repository"):
        st.session_state.app_mode = 'input_repository'
        st.switch_page("main.py")

with st.expander("Solver Log", expanded=False):
    log_text = "\n".join(st.session_state.log_messages) if 'log_messages' in st.session_state else ""
    st.text_area("Log", value=log_text, height=300, key="log_area")
