import json
import openai
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import math
import numpy as np
from io import StringIO
import re

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
            api_key = os.environ.get("OPENAI_API_KEY")
            if api_key:
                openai.api_key = api_key
                API_KEY_AVAILABLE = True
                st.success("OpenAI API key found in OPENAI_API_KEY environment variable. NLP features are enabled.")
            else:
                API_KEY_AVAILABLE = False
                st.error("OpenAI API key not found. Please add OPENAI_API_KEY to your Streamlit secrets or environment variables.")
    except Exception as e:
        API_KEY_AVAILABLE = False
        st.error(f"Error accessing OpenAI API key: {str(e)}. NLP features will not work.")

def process_query(query, route_info, kpi_df, detailed_df, vehicle_capacity):
    """
    Process a natural language query about the VRP solution using a context-aware approach
    
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
        st.write(f"Processing query: {query}")
        st.write(f"Route info type: {type(route_info)}")
        if isinstance(route_info, list) and len(route_info) > 0:
            st.write(f"First route keys: {route_info[0].keys()}")
        
        context = prepare_context(route_info, kpi_df, detailed_df, vehicle_capacity)
        
        response_data = query_gpt_with_context(query, context)
        
        return process_gpt_response(response_data, kpi_df, detailed_df, context['route_info'])
        
    except Exception as e:
        return {
            "response_text": f"I encountered an error while processing your query: {str(e)}",
            "visualization": None,
            "intent": "error"
        }

def prepare_context(route_info, kpi_df, detailed_df, vehicle_capacity):
    """
    Prepare context data about the CVRP problem and optimization results for GPT
    
    Args:
        route_info: The route information from the solver
        kpi_df: DataFrame with KPI information
        detailed_df: DataFrame with detailed route information
        vehicle_capacity: The capacity of each vehicle
        
    Returns:
        dict: Contains context data about the CVRP problem and optimization results
    """
    kpi_df_str = kpi_df.to_string() if not kpi_df.empty else "No KPI data available"
    detailed_df_str = detailed_df.to_string() if not detailed_df.empty else "No detailed route data available"
    
    route_info_str = "Route Information:\n"
    for route in route_info:
        vehicle_id = route['vehicle_id']
        stops = [stop['customer_id'] for stop in route['stops']]
        stops_str = "Depot → " + " → ".join(stops) + " → Depot"
        route_info_str += f"Vehicle {vehicle_id}: {stops_str}\n"
    
    route_info_dict = {}
    for route in route_info:
        vehicle_id = route['vehicle_id']
        route_info_dict[vehicle_id] = {
            'stops': route['stops'],
            'total_distance': route['total_distance'],
            'total_demand': route['total_demand'],
            'route_text': route['route_text']
        }
    
    context = {
        "problem_description": "Capacitated Vehicle Routing Problem (CVRP) using Google OR-Tools",
        "vehicle_capacity": vehicle_capacity,
        "num_vehicles": len(route_info),
        "route_info": route_info_dict,
        "route_info_str": route_info_str,
        "kpi_df_str": kpi_df_str,
        "detailed_df_str": detailed_df_str,
        "kpi_columns": kpi_df.columns.tolist() if not kpi_df.empty else [],
        "detailed_columns": detailed_df.columns.tolist() if not detailed_df.empty else []
    }
    
    return context

def query_gpt_with_context(query, context):
    """
    Query GPT with context about the CVRP problem and optimization results
    
    Args:
        query: The user's natural language query
        context: Context data about the CVRP problem and optimization results
        
    Returns:
        str: GPT's response
    """
    try:
        system_message = f"""
        You are an assistant for a Capacitated Vehicle Routing Problem (CVRP) solver application.
        
        PROBLEM DESCRIPTION:
        The application solves CVRP using Google OR-Tools. Users upload customer data with locations and demands,
        set the number of vehicles and vehicle capacity, and the solver finds optimal routes.
        
        AVAILABLE DATA:
        1. Route Information - Shows the sequence of stops for each vehicle
        {context['route_info_str']}
        
        2. KPI Data - Performance metrics for each vehicle
        {context['kpi_df_str']}
        
        3. Detailed Route Data - Detailed information about each stop
        {context['detailed_df_str']}
        
        4. Configuration:
        - Vehicle Capacity: {context['vehicle_capacity']}
        - Number of Vehicles: {context['num_vehicles']}
        
        YOUR TASK:
        Answer the user's query about the optimization results. If the query requires calculations or data extraction,
        provide Python code that would extract the information from the available data structures.
        
        Available data structures:
        - route_info: Dictionary with vehicle_id as keys and route details as values. Each route has 'stops', 'total_distance', 'total_demand', and 'route_text'.
        - kpi_df: DataFrame with KPI information (columns: {', '.join(context['kpi_columns'])})
        - detailed_df: DataFrame with detailed route information (columns: {', '.join(context['detailed_columns'])})
        
        Format your response as follows:
        1. A direct answer to the user's question
        2. If needed, include a "CODE" section with Python code that extracts the requested information
        3. If appropriate, include a "VISUALIZATION" section with instructions for creating a visualization
        
        For example, if asked "What's the total demand handled by Vehicle 2?", your response might be:
        ```
        Vehicle 2 handled a total demand of 45 units.
        
        CODE:
        ```python
        demand_from_kpi = kpi_df.loc[kpi_df['Vehicle'] == 'Vehicle 2', 'Demand Delivered'].values[0]
        print(f"Vehicle 2 demand from KPI: {demand_from_kpi}")
        
        demand_from_route = route_info[2]['total_demand']
        print(f"Vehicle 2 demand from route_info: {demand_from_route}")
        ```
        ```
        
        If asked about route details like "How far Vehicle 4 travelled from its second last served customer to Depot?",
        your response should include code to calculate this specific distance using the detailed_df or by accessing the route_info dictionary.
        """
        
        client = openai.OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4",  # Using GPT-4 as requested by the user
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": query}
            ],
            temperature=0.1,
            max_tokens=1000
        )
        
        return response.choices[0].message.content
    
    except Exception as e:
        return f"Error querying GPT: {str(e)}"

def process_gpt_response(response_text, kpi_df, detailed_df, route_info=None):
    """
    Process GPT's response to extract visualization instructions if any
    
    Args:
        response_text: GPT's response text
        kpi_df: DataFrame with KPI information
        detailed_df: DataFrame with detailed route information
        route_info: Dictionary with route information
        
    Returns:
        dict: Contains response text, visualization (if any), and intent information
    """
    result = {
        "response_text": response_text,
        "visualization": None,
        "intent": "direct_response"
    }
    
    code_match = re.search(r'```python\s*(.*?)\s*```', response_text, re.DOTALL)
    if code_match:
        code_block = code_match.group(1)
        
        try:
            local_vars = {
                'kpi_df': kpi_df,
                'detailed_df': detailed_df,
                'route_info': route_info,
                'pd': pd,
                'px': px,
                'go': go,
                'np': np,
                'math': math
            }
            
            exec(code_block, globals(), local_vars)
            
            if 'fig' in local_vars and (isinstance(local_vars['fig'], go.Figure) or 
                                       hasattr(local_vars['fig'], 'update_layout')):
                result["visualization"] = local_vars['fig']
                result["intent"] = "visualization"
        
        except Exception as e:
            result["response_text"] += f"\n\nNote: There was an error executing the code: {str(e)}"
    
    return result

def haversine(lon1, lat1, lon2, lat2):
    """
    Calculate the great circle distance between two points 
    on the earth (specified in decimal degrees)
    """
    lon1, lat1, lon2, lat2 = map(math.radians, [lon1, lat1, lon2, lat2])
    
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    r = 6371  # Radius of earth in kilometers
    return c * r
