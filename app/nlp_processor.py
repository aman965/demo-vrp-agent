import json
import openai
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

try:
    api_key = st.secrets["OPENAI_API_KEY"]
    openai.api_key = api_key
    API_KEY_AVAILABLE = True
    st.success("OpenAI API key found in st.secrets. NLP features are enabled.")
except (KeyError, TypeError):
    try:
        import os
        api_key = os.environ.get("streamlit_demo")
        if api_key:
            openai.api_key = api_key
            API_KEY_AVAILABLE = True
            st.success("OpenAI API key found in environment variables. NLP features are enabled.")
        else:
            API_KEY_AVAILABLE = False
            st.warning("OpenAI API key not found in st.secrets or environment variables. NLP features will not work.")
    except Exception:
        API_KEY_AVAILABLE = False
        st.warning("OpenAI API key not found in st.secrets. NLP features will not work.")

def process_query(query, route_info, kpi_df, detailed_df, vehicle_capacity):
    """
    Process a natural language query about the VRP solution
    
    Args:
        query: The user's natural language query
        route_info: The route information from the solver
        kpi_df: DataFrame with KPI information
        detailed_df: DataFrame with detailed route information
        vehicle_capacity: The capacity of each vehicle
        
    Returns:
        dict: Contains response text, visualization (if any), and intent information
    """
    if not API_KEY_AVAILABLE:
        return {
            "response_text": "Sorry, I can't process your query because the OpenAI API key is not configured in Streamlit secrets. Please add the OPENAI_API_KEY to your secrets.",
            "visualization": None,
            "intent": "error"
        }
    
    try:
        intent_data = interpret_query(query, kpi_df.columns.tolist())
    except Exception as e:
        return {
            "response_text": f"I encountered an error while processing your query: {str(e)}",
            "visualization": None,
            "intent": "error"
        }
        
    if intent_data["intent"] == "error":
        return {
            "response_text": "I'm sorry, I couldn't understand your query. Please try again with a different question.",
            "visualization": None,
            "intent": "error"
        }
    
    if intent_data["intent"] == "kpi_request":
        return handle_kpi_request(intent_data, kpi_df)
    elif intent_data["intent"] == "visualization_request":
        return handle_visualization_request(intent_data, kpi_df, detailed_df)
    elif intent_data["intent"] == "comparison_request":
        return handle_comparison_request(intent_data, kpi_df)
    elif intent_data["intent"] == "summary_request":
        return handle_summary_request(kpi_df, route_info, vehicle_capacity)
    elif intent_data["intent"] == "route_detail_request":
        return handle_route_detail_request(intent_data, route_info, detailed_df)
    else:
        return {
            "response_text": "I understand you're asking about the VRP solution, but I'm not sure how to answer that specific question. Could you try rephrasing?",
            "visualization": None,
            "intent": "unknown"
        }

def interpret_query(query, available_metrics):
    """
    Use OpenAI to interpret the user's query and extract intent
    
    Args:
        query: The user's natural language query
        available_metrics: List of available metrics in the KPI dataframe
        
    Returns:
        dict: Contains intent information
    """
    try:
        system_message = f"""
        You are an assistant that interprets user queries about vehicle routing problem (VRP) solutions.
        Available metrics: {', '.join(available_metrics)}
        
        Categorize the query into one of these intents:
        1. kpi_request - User wants a specific KPI value
        2. visualization_request - User wants a chart or visualization
        3. comparison_request - User wants to compare metrics between vehicles
        4. summary_request - User wants an overall summary
        5. route_detail_request - User wants specific information about a route segment or distance between points
        6. error - Query cannot be interpreted
        
        For each intent, extract relevant parameters:
        - For kpi_request: metric_name, vehicle_id (if specified, otherwise "all")
        - For visualization_request: chart_type (bar, pie, line), metric_name
        - For comparison_request: metric_name, comparison_type (max, min, ranking)
        - For route_detail_request: vehicle_id, from_location, to_location, position (first, last, second, etc.)
        
        Return a JSON object with the intent and parameters.
        """
        
        client = openai.OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4",  # Using GPT-4 as requested by the user
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": query}
            ],
            temperature=0.1,
            max_tokens=150,
            response_format={"type": "json_object"}  # Request JSON response format
        )
        
        content = response.choices[0].message.content
        
        try:
            intent_data = json.loads(content)
        except json.JSONDecodeError:
            try:
                json_str = content[content.find('{'):content.rfind('}')+1]
                intent_data = json.loads(json_str)
            except (json.JSONDecodeError, ValueError):
                intent_data = {"intent": "error", "reason": "Failed to parse response"}
        
        return intent_data
    
    except Exception as e:
        return {"intent": "error", "reason": str(e)}

def handle_kpi_request(intent_data, kpi_df):
    """
    Handle a request for a specific KPI value
    
    Args:
        intent_data: The interpreted intent data
        kpi_df: DataFrame with KPI information
        
    Returns:
        dict: Contains response text and visualization (if any)
    """
    metric_name = intent_data.get("metric_name")
    vehicle_id = intent_data.get("vehicle_id", "all")
    
    metric_mapping = {
        "distance": "Distance (km)",
        "demand": "Demand Delivered",
        "customers": "Customers Visited",
        "utilization": "Capacity Utilization (%)",
        "capacity": "Capacity"
    }
    
    actual_metric = None
    for key, value in metric_mapping.items():
        if metric_name and key in metric_name.lower():
            actual_metric = value
            break
    
    if not actual_metric and metric_name:
        for col in kpi_df.columns:
            if metric_name.lower() in col.lower():
                actual_metric = col
                break
    
    if not actual_metric:
        return {
            "response_text": f"I couldn't find information about '{metric_name}'. Available metrics are: {', '.join(kpi_df.columns.tolist())}",
            "visualization": None,
            "intent": "kpi_request"
        }
    
    if vehicle_id == "all" or vehicle_id.lower() == "total":
        value = kpi_df.iloc[-1][actual_metric]
        response_text = f"The total {actual_metric} across all vehicles is {value}"
    else:
        vehicle_row = kpi_df[kpi_df['Vehicle'] == vehicle_id]
        if len(vehicle_row) == 0:
            vehicle_row = kpi_df[kpi_df['Vehicle'] == f"Vehicle {vehicle_id}"]
        
        if len(vehicle_row) == 0:
            return {
                "response_text": f"I couldn't find information for {vehicle_id}. Available vehicles are: {', '.join(kpi_df['Vehicle'].tolist()[:-1])}",
                "visualization": None,
                "intent": "kpi_request"
            }
        
        value = vehicle_row.iloc[0][actual_metric]
        response_text = f"The {actual_metric} for {vehicle_row.iloc[0]['Vehicle']} is {value}"
    
    return {
        "response_text": response_text,
        "visualization": None,
        "intent": "kpi_request"
    }

def handle_visualization_request(intent_data, kpi_df, detailed_df):
    """
    Handle a request for a visualization
    
    Args:
        intent_data: The interpreted intent data
        kpi_df: DataFrame with KPI information
        detailed_df: DataFrame with detailed route information
        
    Returns:
        dict: Contains response text and visualization
    """
    chart_type = intent_data.get("chart_type", "bar")
    metric_name = intent_data.get("metric_name")
    
    metric_mapping = {
        "distance": "Distance (km)",
        "demand": "Demand Delivered",
        "customers": "Customers Visited",
        "utilization": "Capacity Utilization (%)",
        "capacity": "Capacity"
    }
    
    actual_metric = None
    for key, value in metric_mapping.items():
        if metric_name and key in metric_name.lower():
            actual_metric = value
            break
    
    if not actual_metric and metric_name:
        for col in kpi_df.columns:
            if metric_name.lower() in col.lower():
                actual_metric = col
                break
    
    if not actual_metric:
        return {
            "response_text": f"I couldn't create a visualization for '{metric_name}'. Available metrics are: {', '.join(kpi_df.columns.tolist())}",
            "visualization": None,
            "intent": "visualization_request"
        }
    
    try:
        if chart_type.lower() == "pie":
            fig = px.pie(
                kpi_df[:-1],  # Exclude total row
                values=actual_metric,
                names='Vehicle',
                title=f'{actual_metric} Distribution Across Vehicles',
                hole=0.4
            )
            response_text = f"Here's a pie chart showing the distribution of {actual_metric} across vehicles."
        else:  # Default to bar chart
            fig = px.bar(
                kpi_df[:-1],  # Exclude total row
                x='Vehicle',
                y=actual_metric,
                title=f'{actual_metric} per Vehicle',
                color=actual_metric,
                color_continuous_scale='Viridis'
            )
            response_text = f"Here's a bar chart showing {actual_metric} for each vehicle."
        
        return {
            "response_text": response_text,
            "visualization": fig,
            "intent": "visualization_request"
        }
    except Exception as e:
        return {
            "response_text": f"I encountered an error creating the visualization: {str(e)}",
            "visualization": None,
            "intent": "visualization_request"
        }

def handle_comparison_request(intent_data, kpi_df):
    """
    Handle a request to compare metrics between vehicles
    
    Args:
        intent_data: The interpreted intent data
        kpi_df: DataFrame with KPI information
        
    Returns:
        dict: Contains response text and visualization (if any)
    """
    metric_name = intent_data.get("metric_name")
    comparison_type = intent_data.get("comparison_type", "ranking")
    
    metric_mapping = {
        "distance": "Distance (km)",
        "demand": "Demand Delivered",
        "customers": "Customers Visited",
        "utilization": "Capacity Utilization (%)",
        "capacity": "Capacity"
    }
    
    actual_metric = None
    for key, value in metric_mapping.items():
        if metric_name and key in metric_name.lower():
            actual_metric = value
            break
    
    if not actual_metric and metric_name:
        for col in kpi_df.columns:
            if metric_name.lower() in col.lower():
                actual_metric = col
                break
    
    if not actual_metric:
        return {
            "response_text": f"I couldn't compare '{metric_name}'. Available metrics are: {', '.join(kpi_df.columns.tolist())}",
            "visualization": None,
            "intent": "comparison_request"
        }
    
    vehicle_df = kpi_df[:-1].copy()
    
    if comparison_type.lower() == "max":
        max_vehicle = vehicle_df.loc[vehicle_df[actual_metric].idxmax()]
        response_text = f"The vehicle with the highest {actual_metric} is {max_vehicle['Vehicle']} with a value of {max_vehicle[actual_metric]}."
    elif comparison_type.lower() == "min":
        min_vehicle = vehicle_df.loc[vehicle_df[actual_metric].idxmin()]
        response_text = f"The vehicle with the lowest {actual_metric} is {min_vehicle['Vehicle']} with a value of {min_vehicle[actual_metric]}."
    else:  # Default to ranking
        sorted_df = vehicle_df.sort_values(by=actual_metric, ascending=False)
        
        ranking_text = "\n".join([f"{i+1}. {row['Vehicle']}: {row[actual_metric]}" for i, (_, row) in enumerate(sorted_df.iterrows())])
        response_text = f"Here's the ranking of vehicles by {actual_metric}:\n{ranking_text}"
        
        fig = px.bar(
            sorted_df,
            x='Vehicle',
            y=actual_metric,
            title=f'Ranking of Vehicles by {actual_metric}',
            color=actual_metric,
            color_continuous_scale='Viridis'
        )
        
        return {
            "response_text": response_text,
            "visualization": fig,
            "intent": "comparison_request"
        }
    
    return {
        "response_text": response_text,
        "visualization": None,
        "intent": "comparison_request"
    }

def handle_route_detail_request(intent_data, route_info, detailed_df):
    """
    Handle a request for specific route details like distances between points
    
    Args:
        intent_data: The interpreted intent data
        route_info: The route information from the solver
        detailed_df: DataFrame with detailed route information
        
    Returns:
        dict: Contains response text and visualization (if any)
    """
    vehicle_id = intent_data.get("vehicle_id")
    from_location = intent_data.get("from_location")
    to_location = intent_data.get("to_location")
    position = intent_data.get("position")
    
    if vehicle_id and not vehicle_id.lower().startswith("vehicle"):
        vehicle_id = f"Vehicle {vehicle_id}"
    
    vehicle_route = None
    for route in route_info:
        if route.get("vehicle_id") == vehicle_id:
            vehicle_route = route
            break
    
    if not vehicle_route:
        return {
            "response_text": f"I couldn't find route information for {vehicle_id}.",
            "visualization": None,
            "intent": "route_detail_request"
        }
    
    stops = vehicle_route.get("stops", [])
    
    if (position and "second" in position.lower() and "last" in position.lower() and 
        to_location and "depot" in to_location.lower()):
        
        if len(stops) < 3:  # Need at least depot -> customer -> customer -> depot
            return {
                "response_text": f"{vehicle_id} doesn't have enough stops to have a second-last customer.",
                "visualization": None,
                "intent": "route_detail_request"
            }
        
        second_last_customer = stops[-2]
        depot = stops[0]  # Assuming depot is always the first stop
        
        distance = vehicle_route.get("distances", {}).get(f"{second_last_customer['id']}_to_{depot['id']}")
        
        if distance is not None:
            return {
                "response_text": f"The distance from the second-last customer ({second_last_customer['id']}) to the depot for {vehicle_id} is {distance:.2f} km.",
                "visualization": None,
                "intent": "route_detail_request"
            }
        else:
            try:
                if detailed_df is not None and not detailed_df.empty:
                    vehicle_df = detailed_df[detailed_df['Vehicle'] == vehicle_id]
                    
                    if not vehicle_df.empty:
                        second_last_stop = vehicle_df.iloc[-2]
                        depot_stop = vehicle_df.iloc[0]
                        
                        from math import radians, sin, cos, sqrt, atan2
                        
                        def haversine(lat1, lon1, lat2, lon2):
                            R = 6371.0  # Earth radius in km
                            
                            lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
                            
                            dlat = lat2 - lat1
                            dlon = lon2 - lon1
                            
                            a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
                            c = 2 * atan2(sqrt(a), sqrt(1-a))
                            
                            distance = R * c
                            return distance
                        
                        distance = haversine(
                            second_last_stop['Latitude'], 
                            second_last_stop['Longitude'],
                            depot_stop['Latitude'],
                            depot_stop['Longitude']
                        )
                        
                        return {
                            "response_text": f"The distance from the second-last customer ({second_last_stop['CustomerID']}) to the depot for {vehicle_id} is {distance:.2f} km.",
                            "visualization": None,
                            "intent": "route_detail_request"
                        }
            except Exception as e:
                pass
    
    return {
        "response_text": f"I found the route for {vehicle_id}, but I couldn't extract the specific detail you requested. The vehicle visits these stops: {', '.join([stop['id'] for stop in stops])}.",
        "visualization": None,
        "intent": "route_detail_request"
    }

def handle_summary_request(kpi_df, route_info, vehicle_capacity):
    """
    Handle a request for an overall summary of the solution
    
    Args:
        kpi_df: DataFrame with KPI information
        route_info: The route information from the solver
        vehicle_capacity: The capacity of each vehicle
        
    Returns:
        dict: Contains response text and visualization (if any)
    """
    total_row = kpi_df.iloc[-1]
    
    total_vehicles = len(kpi_df) - 1  # Exclude total row
    active_vehicles = sum(1 for route in route_info if len(route['stops']) > 0)
    avg_stops_per_vehicle = total_row['Customers Visited'] / active_vehicles if active_vehicles > 0 else 0
    
    summary_text = f"""## Solution Summary
    
    - **Total Distance**: {total_row['Distance (km)']} km
    - **Total Customers Served**: {int(total_row['Customers Visited'])}
    - **Total Demand Delivered**: {total_row['Demand Delivered']}
    - **Overall Capacity Utilization**: {total_row['Capacity Utilization (%)']}%
    - **Vehicles Used**: {active_vehicles} out of {total_vehicles}
    - **Average Stops Per Vehicle**: {avg_stops_per_vehicle:.2f}
    """
    
    fig = go.Figure()
    
    for i, (_, row) in enumerate(kpi_df[:-1].iterrows()):
        fig.add_trace(go.Bar(
            x=[row['Vehicle']],
            y=[row['Distance (km)']],
            name=f"{row['Vehicle']} - Distance",
            marker_color='blue',
            opacity=0.7,
            text=[f"{row['Distance (km)']} km"],
            textposition='auto'
        ))
        
        fig.add_trace(go.Bar(
            x=[row['Vehicle']],
            y=[row['Capacity Utilization (%)']],
            name=f"{row['Vehicle']} - Utilization",
            marker_color='green',
            opacity=0.7,
            text=[f"{row['Capacity Utilization (%)']}%"],
            textposition='auto',
            yaxis='y2'
        ))
    
    fig.update_layout(
        title="Solution Overview: Distance and Capacity Utilization",
        xaxis_title="Vehicle",
        yaxis_title="Distance (km)",
        yaxis2=dict(
            title="Capacity Utilization (%)",
            overlaying='y',
            side='right',
            range=[0, 100]
        ),
        barmode='group',
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    return {
        "response_text": summary_text,
        "visualization": fig,
        "intent": "summary_request"
    }
