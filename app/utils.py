import numpy as np
import pandas as pd
from math import radians, cos, sin, asin, sqrt
import io
import base64
import folium
from folium.plugins import MarkerCluster
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import json
import os
import streamlit as st
import logging
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("CVRP-App")


def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculate the great circle distance between two points 
    on the earth (specified in decimal degrees)
    """
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])

    dlon = lon2 - lon1 
    dlat = lat2 - lat1 
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a)) 
    r = 6371  # Radius of earth in kilometers
    return c * r


def create_distance_matrix(df):
    """
    Create a distance matrix from a dataframe with lat/lon coordinates
    """
    n = len(df)
    distance_matrix = np.zeros((n, n))
    
    for i in range(n):
        for j in range(n):
            if i != j:
                distance_matrix[i, j] = haversine_distance(
                    df.iloc[i]['Latitude'], 
                    df.iloc[i]['Longitude'],
                    df.iloc[j]['Latitude'], 
                    df.iloc[j]['Longitude']
                )
    
    return distance_matrix


def get_download_link(df, filename, text):
    """
    Generate a download link for a dataframe
    """
    excel_buffer = io.BytesIO()
    df.to_excel(excel_buffer, index=False)
    excel_buffer.seek(0)
    b64 = base64.b64encode(excel_buffer.read()).decode()
    href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="{filename}">{text}</a>'
    return href


def create_folium_map(df, routes):
    """
    Create a folium map with the routes
    """
    depot_lat = df.iloc[0]['Latitude']
    depot_lon = df.iloc[0]['Longitude']
    m = folium.Map(location=[depot_lat, depot_lon], zoom_start=10)
    
    folium.Marker(
        [depot_lat, depot_lon],
        popup="Depot",
        icon=folium.Icon(color="red", icon="home"),
    ).add_to(m)
    
    marker_cluster = MarkerCluster().add_to(m)
    for i in range(1, len(df)):
        folium.Marker(
            [df.iloc[i]['Latitude'], df.iloc[i]['Longitude']],
            popup=f"Customer {df.iloc[i]['CustomerID']} (Demand: {df.iloc[i]['Demand']})",
            icon=folium.Icon(color="blue"),
        ).add_to(marker_cluster)
    
    colors = ['blue', 'green', 'purple', 'orange', 'darkred', 'darkblue', 'darkgreen', 'cadetblue', 
              'darkpurple', 'pink', 'lightblue', 'lightgreen', 'gray', 'black', 'lightred']
    
    for vehicle_id, route in enumerate(routes):
        if len(route) <= 1:  # Skip empty routes
            continue
            
        color = colors[vehicle_id % len(colors)]
        route_points = []
        
        route_points.append([depot_lat, depot_lon])
        
        for node in route[1:-1]:  # Skip depot at start and end
            route_points.append([df.iloc[node]['Latitude'], df.iloc[node]['Longitude']])
            
        route_points.append([depot_lat, depot_lon])
        
        folium.PolyLine(
            route_points,
            color=color,
            weight=2.5,
            opacity=0.8,
            popup=f"Vehicle {vehicle_id+1}"
        ).add_to(m)
    
    return m


def create_plotly_map(df, routes):
    """
    Create a plotly map with the routes
    """
    fig = go.Figure()
    
    depot_lat = df.iloc[0]['Latitude']
    depot_lon = df.iloc[0]['Longitude']
    
    fig.add_trace(go.Scattergeo(
        lon=[depot_lon],
        lat=[depot_lat],
        text=["Depot"],
        mode="markers",
        marker=dict(size=10, color="red", symbol="star"),
        name="Depot"
    ))
    
    customer_lats = df.iloc[1:]['Latitude'].tolist()
    customer_lons = df.iloc[1:]['Longitude'].tolist()
    customer_texts = [f"Customer {row['CustomerID']} (Demand: {row['Demand']})" for _, row in df.iloc[1:].iterrows()]
    
    fig.add_trace(go.Scattergeo(
        lon=customer_lons,
        lat=customer_lats,
        text=customer_texts,
        mode="markers",
        marker=dict(size=8, color="blue"),
        name="Customers"
    ))
    
    colors = px.colors.qualitative.Plotly
    
    for vehicle_id, route in enumerate(routes):
        if len(route) <= 1:  # Skip empty routes
            continue
            
        color = colors[vehicle_id % len(colors)]
        route_lats = []
        route_lons = []
        
        for node in route:
            route_lats.append(df.iloc[node]['Latitude'])
            route_lons.append(df.iloc[node]['Longitude'])
        
        fig.add_trace(go.Scattergeo(
            lon=route_lons,
            lat=route_lats,
            mode="lines",
            line=dict(width=2, color=color),
            name=f"Vehicle {vehicle_id+1}"
        ))
    
    fig.update_layout(
        title="Vehicle Routes",
        geo=dict(
            projection_type="natural earth",
            showland=True,
            landcolor="rgb(243, 243, 243)",
            countrycolor="rgb(204, 204, 204)",
        ),
        height=600,
    )
    
    return fig


def get_openai_config():
    """Get OpenAI API configuration with fallback hierarchy"""
    config = {
        "model": "gpt-4",  # Default to GPT-4 as requested
        "temperature": 0.1,
        "max_tokens": 1000
    }
    
    try:
        config["model"] = st.secrets.get("OPENAI_MODEL", os.environ.get("OPENAI_MODEL", config["model"]))
    except FileNotFoundError:
        config["model"] = os.environ.get("OPENAI_MODEL", config["model"])
    
    return config


def get_openai_api_key():
    """Get OpenAI API key with fallback hierarchy"""
    api_key = None
    
    try:
        api_key = st.secrets.get("OPENAI_API_KEY", None)
    except FileNotFoundError:
        pass
        
    if not api_key:
        api_key = os.environ.get("OPENAI_API_KEY", None)
        
    if not api_key:
        api_key = os.environ.get("vrp_demo_key", None)
    
    return api_key


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


def safe_get_dataframe_value(df, row_idx, column, default=None):
    """Safely get a value from a DataFrame with proper null checking"""
    if df is None or column not in df.columns:
        return default
    
    try:
        return df.iloc[row_idx][column]
    except (IndexError, KeyError):
        return default


def navigate_to_page(page_name, required_state_vars=None):
    """Navigate to a page with validation of required state variables"""
    if required_state_vars:
        for var in required_state_vars:
            if var not in st.session_state or st.session_state[var] is None:
                st.error(f"Missing required data: {var}")
                return False
    
    try:
        st.switch_page(page_name)
        return True
    except Exception as e:
        st.error(f"Navigation error: {str(e)}")
        return False


def get_base_data_dir():
    """Get the base data directory, creating it if it doesn't exist."""
    base_dir = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) / ".data"
    os.makedirs(base_dir, exist_ok=True)
    return base_dir


def ensure_dataframe(data):
    """Ensure data is a pandas DataFrame"""
    if data is None:
        return pd.DataFrame()
        
    if isinstance(data, dict) and 'records' in data:
        return pd.DataFrame.from_records(data['records'])
    elif isinstance(data, list):
        return pd.DataFrame(data)
    elif isinstance(data, pd.DataFrame):
        return data
    else:
        return pd.DataFrame()


def save_dataframe(df, path, format="csv"):
    """Save DataFrame to file with specified format"""
    if df is None or df.empty:
        return None
        
    os.makedirs(os.path.dirname(path), exist_ok=True)
    
    if format.lower() == "csv":
        df.to_csv(path, index=False)
    elif format.lower() == "parquet":
        try:
            df.to_parquet(path, index=False)
        except Exception as e:
            add_log_message(f"Error saving parquet: {str(e)}", "ERROR")
            csv_path = path.replace(".parquet", ".csv")
            df.to_csv(csv_path, index=False)
            return csv_path
    
    return path


def load_dataframe(path, format=None):
    """Load DataFrame from file with auto-detection of format"""
    if not os.path.exists(path):
        return None
        
    if format is None:
        if path.endswith(".csv"):
            format = "csv"
        elif path.endswith(".parquet"):
            format = "parquet"
        else:
            format = "csv"  # Default
    
    try:
        if format.lower() == "csv":
            return pd.read_csv(path)
        elif format.lower() == "parquet":
            return pd.read_parquet(path)
    except Exception as e:
        add_log_message(f"Error loading dataframe from {path}: {str(e)}", "ERROR")
        return None


def validate_scenario_schema(scenario_data):
    """Validate scenario data schema"""
    required_fields = ["scenario_id", "scenario_name", "snapshot_id", "config"]
    
    for field in required_fields:
        if field not in scenario_data:
            add_log_message(f"Missing required field in scenario: {field}", "ERROR")
            return False
    
    if "config" in scenario_data:
        config = scenario_data["config"]
        if not isinstance(config, dict):
            add_log_message("Config must be a dictionary", "ERROR")
            return False
            
        required_config = ["num_vehicles", "vehicle_capacity"]
        for field in required_config:
            if field not in config:
                add_log_message(f"Missing required config field: {field}", "ERROR")
                return False
    
    return True
