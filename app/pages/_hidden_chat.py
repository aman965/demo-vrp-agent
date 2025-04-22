import streamlit as st

st.set_page_config(
    page_title="VRP Assistant",
    page_icon="💬",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
    [data-testid="stSidebar"] ul li:nth-child(2) {
        display: none;
    }
    [data-testid="stSidebar"] ul li:nth-child(3) {
        display: none;
    }
    </style>
    """,
    unsafe_allow_html=True
)

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import traceback
from datetime import datetime
import os
import sys
import logging

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

if 'optimization_results' not in st.session_state or st.session_state.optimization_results is None:
    st.warning("No optimization results found. Please run optimization first.")
    if st.button("Return to Optimization Page"):
        st.session_state.app_mode = 'optimization'
        st.switch_page("main.py")
    st.stop()

try:
    route_info = st.session_state.optimization_results.get('route_info')
    kpi_df = st.session_state.optimization_results.get('kpi_df')
    detailed_df = st.session_state.optimization_results.get('detailed_df')
    vehicle_capacity = st.session_state.optimization_results.get('vehicle_capacity')
except (AttributeError, TypeError) as e:
    st.error(f"Error accessing optimization results: {str(e)}")
    if st.button("Return to Main Page"):
        st.session_state.app_mode = 'input_repository'
        st.switch_page("main.py")
    st.stop()

if (route_info is None or 
    kpi_df is None or 
    isinstance(kpi_df, pd.DataFrame) and kpi_df.empty or 
    vehicle_capacity is None):
    st.warning("Incomplete optimization results. Please run optimization again.")
    if st.button("Return to Optimization Page"):
        st.session_state.app_mode = 'optimization'
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

query_input = st.text_input("Type your message here:", key="query_input")
if st.button("Send", on_click=process_user_query):
    pass

if st.button("Return to Optimization Page"):
    st.session_state.app_mode = 'optimization'
    st.switch_page("main.py")

with st.expander("Solver Log", expanded=False):
    log_text = "\n".join(st.session_state.log_messages) if 'log_messages' in st.session_state else ""
    st.text_area("Log", value=log_text, height=300, key="log_area")
