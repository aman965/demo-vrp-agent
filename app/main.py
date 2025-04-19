import streamlit as st
import pandas as pd
import numpy as np
import io
import base64
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go
import folium
from streamlit_folium import folium_static
import os

from utils import create_distance_matrix, get_download_link, create_folium_map, create_plotly_map
from solver import solve_cvrp, get_route_info

st.set_page_config(
    page_title="Vehicle Routing Problem Solver",
    page_icon="🚚",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("Capacitated Vehicle Routing Problem (CVRP) Solver")
st.markdown("""
This app solves the Capacitated Vehicle Routing Problem (CVRP) using Google OR-Tools.
Upload your customer data, set the parameters, and get optimized routes for your vehicles.
""")

st.sidebar.header("Parameters")

uploaded_file = st.sidebar.file_uploader(
    "Upload CSV file with customer data", 
    type=["csv"]
)

vehicle_count = st.sidebar.number_input(
    "Number of Vehicles",
    min_value=1,
    max_value=100,
    value=5
)

vehicle_capacity = st.sidebar.number_input(
    "Vehicle Capacity",
    min_value=1,
    max_value=10000,
    value=100
)

use_sample_data = st.sidebar.checkbox("Use sample data")

if uploaded_file is not None or use_sample_data:
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
        df = pd.read_csv(uploaded_file)
        
        required_columns = ['CustomerID', 'Latitude', 'Longitude', 'Demand']
        if not all(col in df.columns for col in required_columns):
            st.error(f"CSV file must contain the following columns: {', '.join(required_columns)}")
            st.stop()
    
    st.subheader("Customer Data")
    st.dataframe(df)
    
    if st.button("Run Optimization"):
        with st.spinner("Calculating optimal routes..."):
            distance_matrix = create_distance_matrix(df)
            
            demands = df['Demand'].tolist()
            
            solution_data = solve_cvrp(distance_matrix, demands, vehicle_count, vehicle_capacity)
            
            if solution_data is None:
                st.error("No feasible solution found. Try increasing the number of vehicles or vehicle capacity.")
            else:
                route_info = get_route_info(solution_data, df)
                
                st.subheader("Optimization Results")
                
                st.markdown("### Route Details")
                
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
                
                st.markdown("### Route Paths")
                for route in route_info:
                    st.markdown(f"**{route['route_text']}**")
                
                tab1, tab2, tab3 = st.tabs(["Interactive Map (Folium)", "Interactive Map (Plotly)", "Export Results"])
                
                with tab1:
                    st.markdown("### Route Visualization (Folium)")
                    m = create_folium_map(df, solution_data['routes'])
                    folium_static(m)
                
                with tab2:
                    st.markdown("### Route Visualization (Plotly)")
                    fig = create_plotly_map(df, solution_data['routes'])
                    st.plotly_chart(fig, use_container_width=True)
                
                with tab3:
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
                                'Latitude': df.iloc[stop['node_idx']]['Latitude'],
                                'Longitude': df.iloc[stop['node_idx']]['Longitude']
                            })
                    
                    detailed_df = pd.DataFrame(detailed_results)
                    
                    st.dataframe(detailed_df)
                    
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    
                    st.markdown(
                        get_download_link(
                            route_df, 
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
