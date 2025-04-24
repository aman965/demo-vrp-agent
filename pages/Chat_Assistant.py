import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import traceback
from datetime import datetime
import os
import sys
import logging

st.set_page_config(
    page_title="Chat Assistant",
    page_icon="💬",
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
from app.nlp_processor import process_query

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("CVRP-Chat")

if 'chat_messages' not in st.session_state:
    st.session_state.chat_messages = []

if 'chat_viz' not in st.session_state:
    st.session_state.chat_viz = None

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

def add_chat_message(role, content, metadata=None):
    """Add a message to the chat history"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    message = {
        "role": role, 
        "content": content, 
        "timestamp": timestamp
    }
    if metadata:
        message["metadata"] = metadata
    st.session_state.chat_messages.append(message)

st.title("VRP Assistant Chat")

if 'selected_snapshot' not in st.session_state or st.session_state.selected_snapshot is None:
    st.warning("No snapshot selected. Please select a snapshot first.")
    if st.button("Return to Input Repository"):
        st.session_state.app_mode = 'input_repository'
        st.switch_page("main.py")
    st.stop()

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from app.scenario_manager import get_scenarios_for_snapshot, get_scenario_by_id

snapshot = st.session_state.selected_snapshot
st.markdown(f"### Analyzing Scenarios for Snapshot: **{snapshot['snapshot_name']}**")

scenarios = get_scenarios_for_snapshot(snapshot['snapshot_id'])
scenarios_with_results = [s for s in scenarios if s.get('optimization_results') is not None]

if not scenarios_with_results:
    st.warning("No scenarios with results found for this snapshot. Please run optimization for at least one scenario first.")
    if st.button("Return to Scenario Management"):
        st.session_state.app_mode = 'scenario_management'
        st.switch_page("main.py")
    st.stop()

selected_scenario_index = st.selectbox(
    "Select a scenario to analyze:",
    options=range(len(scenarios_with_results)),
    format_func=lambda i: scenarios_with_results[i]["scenario_name"]
)

selected_scenario = scenarios_with_results[selected_scenario_index]
add_log_message(f"Selected scenario: {selected_scenario['scenario_name']}")

try:
    optimization_results = selected_scenario.get('optimization_results', {})
    
    route_info = optimization_results.get('route_info')
    kpi_df = optimization_results.get('kpi_df')
    detailed_df = optimization_results.get('detailed_df')
    vehicle_capacity = selected_scenario['config']['vehicle_capacity']
    
    if isinstance(kpi_df, dict) and 'records' in kpi_df:
        kpi_df = pd.DataFrame.from_records(kpi_df['records'])
    elif isinstance(kpi_df, list):
        kpi_df = pd.DataFrame(kpi_df)
        
    if isinstance(detailed_df, dict) and 'records' in detailed_df:
        detailed_df = pd.DataFrame.from_records(detailed_df['records'])
    elif isinstance(detailed_df, list):
        detailed_df = pd.DataFrame(detailed_df)
        
except (AttributeError, TypeError, KeyError) as e:
    st.error(f"Error accessing scenario results: {str(e)}")
    add_log_message(f"Error accessing scenario results: {str(e)}", "ERROR")
    if st.button("Return to Scenario Management"):
        st.session_state.app_mode = 'scenario_management'
        st.switch_page("main.py")
    st.stop()

if (route_info is None or 
    kpi_df is None or 
    isinstance(kpi_df, pd.DataFrame) and kpi_df.empty or 
    vehicle_capacity is None):
    st.warning("Incomplete optimization results for this scenario. Please run optimization again.")
    if st.button("Return to Scenario Management"):
        st.session_state.app_mode = 'scenario_management'
        st.switch_page("main.py")
    st.stop()

st.markdown("### Chat with VRP Assistant")
st.markdown("Ask questions about your routes or request scenario analysis.")

chat_container = st.container()
with chat_container:
    for message in st.session_state.chat_messages:
        if message["role"] == "user":
            st.markdown(f"**You ({message['timestamp']}):** {message['content']}")
        elif message["role"] == "assistant":
            st.markdown(f"**Assistant ({message['timestamp']}):** {message['content']}")
            if "metadata" in message and "intent" in message["metadata"]:
                intent = message["metadata"]["intent"]
                if intent != "error" and intent != "unknown":
                    st.caption(f"*Interpreted as: {intent}*")

if st.session_state.chat_viz is not None:
    st.markdown("### Generated Visualization")
    st.plotly_chart(st.session_state.chat_viz, use_container_width=True)

def process_user_query():
    if "query_input" in st.session_state and st.session_state.query_input:
        query = st.session_state.query_input
        add_chat_message("user", query)
        add_log_message(f"Processing chat query: '{query}'", "INFO")
        
        try:
            scenario_context = f"Analyzing scenario: {selected_scenario['scenario_name']}"
            
            result = process_query(
                query=query,
                route_info=route_info,
                kpi_df=kpi_df,
                detailed_df=detailed_df,
                vehicle_capacity=vehicle_capacity,
                context=scenario_context
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

query_input = st.text_input("Type your message here:", key="query_input")
if st.button("Send", on_click=process_user_query):
    pass

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
