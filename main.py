import streamlit as st
import os
import sys

st.set_page_config(
    page_title="Vehicle Routing Problem Solver",
    page_icon="🚚",
    layout="wide",
    initial_sidebar_state="expanded",
)

os.environ["STREAMLIT_RUN_APP"] = "1"

try:
    from app import main as app_main
    print("Successfully imported app.main as app_main")
except ImportError as e:
    try:
        import app.main
        print("Successfully imported app.main")
    except ImportError as e2:
        error_msg = f"Failed to import application modules: {e2}"
        print(error_msg)
        st.error(error_msg)
        
        st.error("Python path: " + str(sys.path))
        st.error("Current directory: " + os.getcwd())
        st.error("Directory contents: " + str(os.listdir('.')))
        if os.path.exists('app'):
            st.error("App directory contents: " + str(os.listdir('app')))
