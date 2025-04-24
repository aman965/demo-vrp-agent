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