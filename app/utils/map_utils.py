"""
Map utilities for the VRP application.
"""
import numpy as np
import folium
import plotly.graph_objects as go
from math import radians, sin, cos, sqrt, atan2

def haversine(lat1, lon1, lat2, lon2):
    """Calculate the great circle distance between two points on Earth."""
    R = 6371  # Earth's radius in kilometers

    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    distance = R * c

    return distance

def create_distance_matrix(df):
    """Create a distance matrix from latitude and longitude coordinates."""
    n = len(df)
    distance_matrix = np.zeros((n, n))
    
    for i in range(n):
        for j in range(n):
            if i != j:
                distance_matrix[i][j] = haversine(
                    df.iloc[i]['latitude'], 
                    df.iloc[i]['longitude'],
                    df.iloc[j]['latitude'], 
                    df.iloc[j]['longitude']
                )
    
    return distance_matrix

def create_folium_map(df, routes=None, depot_idx=0):
    """Create a Folium map visualization of the routes."""
    # Create a map centered on the mean coordinates
    center_lat = df['latitude'].mean()
    center_lon = df['longitude'].mean()
    m = folium.Map(location=[center_lat, center_lon], zoom_start=10)
    
    # Add depot marker
    folium.Marker(
        [df.iloc[depot_idx]['latitude'], df.iloc[depot_idx]['longitude']],
        popup='Depot',
        icon=folium.Icon(color='red', icon='info-sign')
    ).add_to(m)
    
    # Add customer markers and routes if provided
    colors = ['blue', 'green', 'purple', 'orange', 'darkred', 'lightred', 'beige', 'darkblue', 'darkgreen', 'cadetblue']
    
    if routes:
        for vehicle_idx, route in enumerate(routes):
            color = colors[vehicle_idx % len(colors)]
            
            # Draw route lines
            route_coords = []
            for point_idx in route:
                lat = df.iloc[point_idx]['latitude']
                lon = df.iloc[point_idx]['longitude']
                route_coords.append([lat, lon])
                
                # Add customer marker
                if point_idx != depot_idx:
                    folium.CircleMarker(
                        [lat, lon],
                        radius=5,
                        popup=f'Customer {point_idx}',
                        color=color,
                        fill=True
                    ).add_to(m)
            
            # Create the route line
            folium.PolyLine(
                route_coords,
                weight=2,
                color=color,
                opacity=0.8
            ).add_to(m)
    else:
        # If no routes provided, just show all points
        for idx, row in df.iterrows():
            if idx != depot_idx:
                folium.CircleMarker(
                    [row['latitude'], row['longitude']],
                    radius=5,
                    popup=f'Customer {idx}',
                    color='blue',
                    fill=True
                ).add_to(m)
    
    return m

def create_plotly_map(df, routes=None, depot_idx=0):
    """Create a Plotly map visualization of the routes."""
    fig = go.Figure()
    
    # Add depot marker
    fig.add_trace(go.Scattermapbox(
        lat=[df.iloc[depot_idx]['latitude']],
        lon=[df.iloc[depot_idx]['longitude']],
        mode='markers',
        marker=dict(size=15, color='red'),
        text=['Depot'],
        name='Depot'
    ))
    
    # Colors for different routes
    colors = ['blue', 'green', 'purple', 'orange', 'red', 'pink', 'yellow', 'cyan', 'brown', 'gray']
    
    if routes:
        for vehicle_idx, route in enumerate(routes):
            color = colors[vehicle_idx % len(colors)]
            
            # Extract coordinates for the route
            route_lats = [df.iloc[i]['latitude'] for i in route]
            route_lons = [df.iloc[i]['longitude'] for i in route]
            
            # Add route line
            fig.add_trace(go.Scattermapbox(
                lat=route_lats,
                lon=route_lons,
                mode='lines',
                line=dict(width=2, color=color),
                name=f'Route {vehicle_idx + 1}'
            ))
            
            # Add customer markers
            customer_lats = [df.iloc[i]['latitude'] for i in route if i != depot_idx]
            customer_lons = [df.iloc[i]['longitude'] for i in route if i != depot_idx]
            customer_texts = [f'Customer {i}' for i in route if i != depot_idx]
            
            fig.add_trace(go.Scattermapbox(
                lat=customer_lats,
                lon=customer_lons,
                mode='markers',
                marker=dict(size=10, color=color),
                text=customer_texts,
                name=f'Customers Route {vehicle_idx + 1}'
            ))
    else:
        # If no routes provided, just show all points
        customer_lats = [row['latitude'] for idx, row in df.iterrows() if idx != depot_idx]
        customer_lons = [row['longitude'] for idx, row in df.iterrows() if idx != depot_idx]
        customer_texts = [f'Customer {idx}' for idx in range(len(df)) if idx != depot_idx]
        
        fig.add_trace(go.Scattermapbox(
            lat=customer_lats,
            lon=customer_lons,
            mode='markers',
            marker=dict(size=10, color='blue'),
            text=customer_texts,
            name='Customers'
        ))
    
    # Update layout
    fig.update_layout(
        mapbox=dict(
            style="carto-positron",
            zoom=9,
            center=dict(
                lat=df['latitude'].mean(),
                lon=df['longitude'].mean()
            )
        ),
        showlegend=True,
        margin=dict(l=0, r=0, t=0, b=0)
    )
    
    return fig 