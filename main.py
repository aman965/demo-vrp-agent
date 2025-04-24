import streamlit as st
import sys
import os

st.set_page_config(
    page_title="Vehicle Routing Problem Solver",
    page_icon="🚚",
    layout="wide",
    initial_sidebar_state="expanded",
)

app_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app")
if app_dir not in sys.path:
    sys.path.insert(0, app_dir)

current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

os.environ["STREAMLIT_RUN_APP"] = "1"

try:
    import app.main
    print("Successfully imported app.main")
except ImportError as e:
    print(f"Error importing app.main: {e}")
    st.error(f"Failed to import application modules: {e}")
