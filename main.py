import streamlit as st
import sys
import os

st.set_page_config(
    page_title="Vehicle Routing Problem Solver",
    page_icon="🚚",
    layout="wide",
    initial_sidebar_state="expanded",
)

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

os.environ["STREAMLIT_RUN_APP"] = "1"

import app.main
