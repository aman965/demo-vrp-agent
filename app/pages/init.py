import streamlit as st

st.set_page_config(
    page_title="VRP Initialization",
    page_icon="🚀",
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

st.title("VRP Solver Initialization")
st.markdown("This page is used for initialization purposes only.")
st.markdown("Please navigate to the main page to use the application.")

if st.button("Go to Main Page"):
    st.switch_page("../../main.py")
