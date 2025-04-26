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
from openai import OpenAI

API_KEY_AVAILABLE = False
MODEL_NAME = "gpt-4"  # Default model

st.info("📡 Starting GPT integration check...")
st.text("Checking OpenAI library import...")

try:
    client = None  # Initialize OpenAI client as None
except ImportError:
    st.error("❌ Failed to import OpenAI library. Please check your installation.")

try:
    api_key = st.secrets.get("OPENAI_API_KEY", "")
    MODEL_NAME = st.secrets.get("OPENAI_MODEL", "gpt-3.5-turbo")
    
    st.text(f"Loaded Model: {MODEL_NAME}")
    st.text(f"API Key Present: {'Yes' if api_key and len(api_key) > 0 else 'No'}")
    
    if api_key and len(api_key) > 0:
        client = OpenAI(api_key=api_key)
        API_KEY_AVAILABLE = True
        st.success(f"✅ OpenAI client initialized with model: {MODEL_NAME}")
    else:
        st.warning("⚠️ OpenAI API key in Streamlit secrets is empty.")
except Exception as e:
    st.warning(f"⚠️ Could not load OpenAI API key from Streamlit secrets: {str(e)}")

if not API_KEY_AVAILABLE:
    try:
        for env_var in ["OPENAI_API_KEY", "vrp_demo_key", "streamlit_demo"]:
            api_key = os.environ.get(env_var, "")
            if api_key and len(api_key) > 0:
                client = OpenAI(api_key=api_key)
                API_KEY_AVAILABLE = True
                st.success(f"✅ OpenAI API key found in environment variable '{env_var}'. Using model: {MODEL_NAME}")
                break
        
        if not API_KEY_AVAILABLE:
            st.error("❌ OpenAI API key not found. Please add OPENAI_API_KEY to your Streamlit secrets or environment variables.")
    except Exception as e:
        st.error(f"❌ Error accessing environment variables: {str(e)}")
        API_KEY_AVAILABLE = False

def process_query(query, route_info=None, kpi_df=None, detailed_df=None, vehicle_capacity=None, context=None, mode="analysis"):
    """
    Process a natural language query about the VRP solution using a context-aware approach
    
    Args:
        query: The user's natural language query
        route_info: The route information from the solver (optional for constraint mode)
        kpi_df: DataFrame with KPI information (optional for constraint mode)
        detailed_df: DataFrame with detailed route information (optional for constraint mode)
        vehicle_capacity: The capacity of each vehicle (optional for constraint mode)
        context: Additional context information about the scenario (optional)
        mode: The processing mode - "analysis" or "constraint_extraction"
        
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
        if mode == "constraint_extraction":
            return process_constraint_prompt(query, context)
            
        prepared_context = prepare_context(route_info, kpi_df, detailed_df, vehicle_capacity)
        
        if context:
            prepared_context['additional_context'] = context
        
        response_data = query_gpt_with_context(query, prepared_context)
        
        return process_gpt_response(response_data, kpi_df, detailed_df, prepared_context['route_info'], prepared_context['vehicle_capacity'])
        
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
        system_message = r"""
        You are an assistant for a Capacitated Vehicle Routing Problem (CVRP) solver application.
        
        PROBLEM DESCRIPTION:
        The application solves CVRP using Google OR-Tools. Users upload customer data with locations and demands,
        set the number of vehicles and vehicle capacity, and the solver finds optimal routes.
        
        AVAILABLE DATA:
        1. Route Information - Shows the sequence of stops for each vehicle
        """ + context['route_info_str'] + r"""
        
        2. KPI Data - Performance metrics for each vehicle
        """ + context['kpi_df_str'] + r"""
        
        3. Detailed Route Data - Detailed information about each stop
        """ + context['detailed_df_str'] + r"""
        
        4. Configuration:
        - Vehicle Capacity: """ + str(context['vehicle_capacity']) + r"""
        - Number of Vehicles: """ + str(context['num_vehicles']) + r"""
        
        """ + (f"5. Additional Context:\n{context['additional_context']}" if 'additional_context' in context else "") + r"""
        
        YOUR TASK:
        Answer the user's query about the optimization results. If the query requires calculations or data extraction,
        provide Python code that would extract the information from the available data structures.
        
        Available data structures:
        - route_info: List of dictionaries, each representing a vehicle route. Each dictionary has keys: 'vehicle_id', 'stops', 'total_distance', 'total_demand', and 'route_text'.
        - kpi_df: DataFrame with KPI information (columns: """ + ', '.join(context['kpi_columns']) + r""")
        - detailed_df: DataFrame with detailed route information (columns: """ + ', '.join(context['detailed_columns']) + r""")
        
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
        ```
        """
        
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": query}
            ],
            temperature=0.7,
            max_tokens=1500
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        traceback.print_exc()
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
    
    # Check if the query is asking for a visualization
    visualization_keywords = ['plot', 'chart', 'graph', 'visualize', 'show', 'display', 'draw']
    if any(keyword in response_text.lower() for keyword in visualization_keywords):
        result["intent"] = "visualization_request"
    
    code_match = re.search(r'```python\s*(.*?)\s*```', response_text, re.DOTALL)
    if code_match:
        code_block = code_match.group(1)
        
        try:
            try:
                import matplotlib.pyplot as plt
                plt_available = True
            except ImportError:
                plt_available = False
                
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
            
            if plt_available:
                local_vars['plt'] = plt
            
            exec(code_block, globals(), local_vars)
            
            if 'fig' in local_vars and (isinstance(local_vars['fig'], go.Figure) or 
                                       hasattr(local_vars['fig'], 'update_layout')):
                result["visualization"] = local_vars['fig']
                result["intent"] = "visualization"
            
            elif plt_available and 'plt' in local_vars and plt.get_fignums():
                try:
                    vehicle_distances = None
                    vehicle_ids = None
                    
                    for var_name in ['vehicle_distances', 'distances', 'distance_values']:
                        if var_name in local_vars and isinstance(local_vars[var_name], (list, np.ndarray, pd.Series)):
                            vehicle_distances = local_vars[var_name]
                            break
                    
                    for var_name in ['vehicle_ids', 'vehicles', 'ids']:
                        if var_name in local_vars and isinstance(local_vars[var_name], (list, np.ndarray, pd.Series)):
                            vehicle_ids = local_vars[var_name]
                            break
                    
                    if vehicle_distances is not None and vehicle_ids is not None and len(vehicle_distances) == len(vehicle_ids):
                        fig = px.bar(
                            x=vehicle_ids, 
                            y=vehicle_distances,
                            labels={'x': 'Vehicle', 'y': 'Distance (km)'},
                            title='Distance Traveled by Each Vehicle',
                            color_discrete_sequence=['skyblue']
                        )
                        fig.update_layout(
                            xaxis_title='Vehicle',
                            yaxis_title='Distance Traveled (km)'
                        )
                        result["visualization"] = fig
                        result["intent"] = "visualization"
                    elif 'kpi_df' in local_vars and not local_vars['kpi_df'].empty and 'Distance (km)' in local_vars['kpi_df'].columns:
                        fig = px.bar(
                            local_vars['kpi_df'], 
                            x='Vehicle', 
                            y='Distance (km)',
                            title='Distance Traveled by Each Vehicle',
                            color_discrete_sequence=['skyblue']
                        )
                        result["visualization"] = fig
                        result["intent"] = "visualization"
                    else:
                        fig = go.Figure()
                        
                        mpl_fig = plt.gcf()
                        
                        for ax in mpl_fig.axes:
                            if hasattr(ax, 'patches') and ax.patches:
                                x_values = []
                                y_values = []
                                for patch in ax.patches:
                                    if hasattr(patch, 'get_x') and hasattr(patch, 'get_width'):
                                        x = patch.get_x() + patch.get_width() / 2
                                        y = patch.get_height()
                                        x_values.append(x)
                                        y_values.append(y)
                                
                                if x_values and y_values:
                                    fig.add_trace(go.Bar(x=x_values, y=y_values))
                            
                            if hasattr(ax, 'lines'):
                                for line in ax.lines:
                                    x_data = line.get_xdata()
                                    y_data = line.get_ydata()
                                    if len(x_data) > 0 and len(y_data) > 0:
                                        fig.add_trace(go.Scatter(x=x_data, y=y_data, mode='lines'))
                        
                        if hasattr(ax, 'get_title') and ax.get_title():
                            fig.update_layout(title=ax.get_title())
                        if hasattr(ax, 'get_xlabel') and ax.get_xlabel():
                            fig.update_xaxes(title=ax.get_xlabel())
                        if hasattr(ax, 'get_ylabel') and ax.get_ylabel():
                            fig.update_yaxes(title=ax.get_ylabel())
                        
                        if len(fig.data) > 0:
                            result["visualization"] = fig
                            result["intent"] = "visualization"
                        else:
                            if not kpi_df.empty and 'Vehicle' in kpi_df.columns and 'Distance (km)' in kpi_df.columns:
                                fig = px.bar(
                                    kpi_df, 
                                    x='Vehicle', 
                                    y='Distance (km)',
                                    title='Distance Traveled by Each Vehicle',
                                    color_discrete_sequence=['skyblue']
                                )
                                result["visualization"] = fig
                                result["intent"] = "visualization"
                            else:
                                result["response_text"] += "\n\nNote: I couldn't create a visualization from the matplotlib figure. Please try using Plotly directly in your query."
                except Exception as viz_error:
                    result["response_text"] += f"\n\nNote: Error creating visualization: {str(viz_error)}"
                
                # Always close matplotlib figure to free memory
                plt.close()
        
        except Exception as e:
            error_msg = f"\n\nNote: There was an error executing the code: {str(e)}\n{traceback.format_exc()}"
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

def process_constraint_prompt(prompt, context=None):
    """Process a constraint prompt using GPT to extract structured constraints
    
    Args:
        prompt (str): The natural language constraint prompt
        context (str, optional): Additional context to include
        
    Returns:
        dict: Contains extracted constraints and GPT's analysis
    """
    if not API_KEY_AVAILABLE or client is None:
        return {
            "response_text": "Sorry, I can't process your query because the OpenAI API key is not configured in Streamlit secrets. Please add the OPENAI_API_KEY to your secrets.",
            "constraints": {},
            "analysis": ""
        }
    
    try:
        messages = [
            {
                "role": "system", 
                "content": """You are an assistant that helps extract structured constraints from natural language descriptions for a Vehicle Routing Problem (VRP).

Your task is to:
1. Parse the natural language description
2. Extract specific, implementable constraints into a machine-readable format
3. Provide a brief analysis of the constraints

Format your response as follows:
1. First line: A JSON object containing the extracted constraints
2. Second line: A brief summary of what constraints were found
3. Final line: A brief analysis of how the constraints will affect the solution

Example response for "Maximum distance per vehicle should be 40KM":
{"max_distance_per_vehicle": 40}
Set maximum distance per vehicle to 40KM
This constraint will ensure no vehicle travels more than 40 kilometers in their route.

Supported constraint types:
- max_distance_per_vehicle: Maximum distance a vehicle can travel (number)
- max_customers_per_vehicle: Maximum customers a vehicle can serve (number)
- capacity_limit: Override vehicle capacity (number)
- allowed_zones: Geographic zones vehicles can operate in (list)
- time_windows: Time windows for deliveries (dict)
"""
            },
            {"role": "user", "content": prompt}
        ]
        
        if context:
            messages.append({"role": "user", "content": f"Additional context:\n{context}"})
        
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            temperature=0.3,
            max_tokens=1000
        )
        
        response_text = response.choices[0].message.content
        
        # Parse response
        lines = response_text.strip().split('\n')
        
        # First line should be JSON
        try:
            import json
            constraints = json.loads(lines[0])
        except (json.JSONDecodeError, IndexError):
            constraints = {}
        
        # Get summary and analysis
        summary = lines[1] if len(lines) > 1 else ""
        analysis = lines[2] if len(lines) > 2 else ""
        
        return {
            "constraints": constraints,
            "summary": summary,
            "analysis": analysis
        }
        
    except Exception as e:
        traceback.print_exc()
        return {
            "response_text": f"Error processing constraint prompt: {str(e)}",
            "constraints": {},
            "analysis": ""
        }
