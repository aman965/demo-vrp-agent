import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import math
import numpy as np
from io import StringIO
import re
import traceback
import os

API_KEY_AVAILABLE = False
MODEL_NAME = "gpt-3.5-turbo"  # Default model
client = None

try:
    import openai
    from openai import OpenAI
except ImportError:
    st.error("Failed to import OpenAI library. Please check your installation.")
    openai = None

try:
    api_key = st.secrets["OPENAI_API_KEY"]
    if api_key and len(api_key) > 0:
        MODEL_NAME = st.secrets.get("OPENAI_MODEL", "gpt-3.5-turbo")
        openai.api_key = api_key
        try:
            openai.Model.list()
            API_KEY_AVAILABLE = True
            st.success(f"OpenAI API key found in Streamlit secrets (legacy API). Using model: {MODEL_NAME}")
        except Exception as api_e:
            st.warning(f"Legacy API test failed: {str(api_e)}")
            try:
                client = OpenAI(api_key=api_key)
                client.models.list()
                API_KEY_AVAILABLE = True
                st.success(f"OpenAI API key found in Streamlit secrets (new client). Using model: {MODEL_NAME}")
            except Exception as client_e:
                st.warning(f"New client API test failed: {str(client_e)}")
    else:
        st.warning("OpenAI API key in Streamlit secrets is empty.")
except Exception as e:
    st.warning(f"Could not load OpenAI API key from Streamlit secrets: {str(e)}")

if not API_KEY_AVAILABLE:
    try:
        api_key = os.environ.get("vrp_demo_key")
        if api_key and len(api_key) > 0:
            openai.api_key = api_key
            try:
                openai.Model.list()
                API_KEY_AVAILABLE = True
                st.success(f"OpenAI API key found in environment variable 'vrp_demo_key' (legacy API). Using model: {MODEL_NAME}")
            except Exception:
                try:
                    client = OpenAI(api_key=api_key)
                    client.models.list()
                    API_KEY_AVAILABLE = True
                    st.success(f"OpenAI API key found in environment variable 'vrp_demo_key' (new client). Using model: {MODEL_NAME}")
                except Exception as e:
                    st.warning(f"API key from vrp_demo_key failed: {str(e)}")
        else:
            api_key = os.environ.get("streamlit_demo")
            if api_key and len(api_key) > 0:
                openai.api_key = api_key
                try:
                    openai.Model.list()
                    API_KEY_AVAILABLE = True
                    st.success(f"OpenAI API key found in environment variable 'streamlit_demo' (legacy API). Using model: {MODEL_NAME}")
                except Exception:
                    try:
                        client = OpenAI(api_key=api_key)
                        client.models.list()
                        API_KEY_AVAILABLE = True
                        st.success(f"OpenAI API key found in environment variable 'streamlit_demo' (new client). Using model: {MODEL_NAME}")
                    except Exception as e:
                        st.warning(f"API key from streamlit_demo failed: {str(e)}")
            else:
                api_key = os.environ.get("OPENAI_API_KEY")
                if api_key and len(api_key) > 0:
                    openai.api_key = api_key
                    try:
                        openai.Model.list()
                        API_KEY_AVAILABLE = True
                        st.success(f"OpenAI API key found in environment variable 'OPENAI_API_KEY' (legacy API). Using model: {MODEL_NAME}")
                    except Exception:
                        try:
                            client = OpenAI(api_key=api_key)
                            client.models.list()
                            API_KEY_AVAILABLE = True
                            st.success(f"OpenAI API key found in environment variable 'OPENAI_API_KEY' (new client). Using model: {MODEL_NAME}")
                        except Exception as e:
                            st.warning(f"API key from OPENAI_API_KEY failed: {str(e)}")
                else:
                    st.error("OpenAI API key not found. Please add OPENAI_API_KEY to your Streamlit secrets or environment variables.")
    except Exception as e:
        st.error(f"Error accessing environment variables: {str(e)}")
        API_KEY_AVAILABLE = False

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
    if not API_KEY_AVAILABLE or client is None:
        return {
            "response_text": "Sorry, I can't process your query because the OpenAI API key is not configured in Streamlit secrets. Please add the OPENAI_API_KEY to your secrets.",
            "visualization": None,
            "intent": "error"
        }
    
    try:
        context = prepare_context(route_info, kpi_df, detailed_df, vehicle_capacity)
        
        response_data = query_gpt_with_context(query, context)
        
        return process_gpt_response(response_data, kpi_df, detailed_df, context['route_info'], context['vehicle_capacity'])
        
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
    
    context = {
        "problem_description": "Capacitated Vehicle Routing Problem (CVRP) using Google OR-Tools",
        "vehicle_capacity": vehicle_capacity,
        "num_vehicles": len(route_info),
        "route_info": route_info,  # Pass the original list
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
    if not API_KEY_AVAILABLE or client is None:
        return "Sorry, I can't process your query because the OpenAI API key is not configured in Streamlit secrets. Please add the OPENAI_API_KEY to your secrets."
    
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
        - route_info: List of dictionaries, each representing a vehicle route. Each dictionary has keys: 'vehicle_id', 'stops', 'total_distance', 'total_demand', and 'route_text'.
        - kpi_df: DataFrame with KPI information (columns: {', '.join(context['kpi_columns'])})
        - detailed_df: DataFrame with detailed route information (columns: {', '.join(context['detailed_columns'])})
        
        Format your response as follows:
        1. A direct answer to the user's question
        2. If needed, include a "CODE" section with Python code that extracts the requested information
        3. If appropriate, include a "VISUALIZATION" section with instructions for creating a visualization
        
        IMPORTANT: When writing code, use descriptive variable names and make sure to define all variables before using them.
        
        Example query types you should be able to handle:
        1. "What's the total demand handled by Vehicle 2?"
        2. "How far did Vehicle 4 travel from its second last served customer to the Depot?"
        3. "Which vehicle traveled the most distance?"
        4. "What is the capacity utilization of Vehicle 3?"
        5. "Show a bar chart of demand per vehicle"
        
        For distance calculations between geographical coordinates, you can use the haversine function:
        ```python
        def haversine(lon1, lat1, lon2, lat2):
            # Calculate the great circle distance between two points 
            # on the earth (specified in decimal degrees)
            lon1, lat1, lon2, lat2 = map(math.radians, [lon1, lat1, lon2, lat2])
            dlon = lon2 - lon1
            dlat = lat2 - lat1
            a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
            c = 2 * math.asin(math.sqrt(a))
            r = 6371  # Radius of earth in kilometers
            return c * r
        ```
        """
        
        try:
            response = openai.ChatCompletion.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": query}
                ],
                temperature=0.1,
                max_tokens=1000
            )
            return response.choices[0].message.content
        except Exception as e:
            st.error(f"OpenAI API call failed: {str(e)}")
            return f"I'm sorry, I encountered an error while processing your query: {str(e)}"
        
        return response.choices[0].message.content
    
    except Exception as e:
        return f"Error querying GPT: {str(e)}"

def process_gpt_response(response_text, kpi_df, detailed_df, route_info=None, vehicle_capacity=None):
    """
    Process GPT's response to extract visualization instructions if any
    
    Args:
        response_text: GPT's response text
        kpi_df: DataFrame with KPI information
        detailed_df: DataFrame with detailed route information
        route_info: List of dictionaries with route information
        vehicle_capacity: The capacity of each vehicle
        
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
                'vehicle_capacity': vehicle_capacity,
                'pd': pd,
                'px': px,
                'go': go,
                'np': np,
                'math': math,
                'haversine': haversine,
                'StringIO': StringIO
            }
            
            exec(code_block, globals(), local_vars)
            
            if 'fig' in local_vars and (isinstance(local_vars['fig'], go.Figure) or 
                                       hasattr(local_vars['fig'], 'update_layout')):
                result["visualization"] = local_vars['fig']
                result["intent"] = "visualization"
        
        except Exception as e:
            error_msg = f"\n\nNote: There was an error executing the code: {str(e)}"
            result["response_text"] += error_msg
    
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
