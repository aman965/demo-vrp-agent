import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from scenario_manager import get_scenarios_for_snapshot, get_scenario_by_id

def scenario_comparison_ui(snapshot_id, snapshot_name):
    """
    Display the scenario comparison UI for a specific snapshot.
    
    Args:
        snapshot_id: ID of the snapshot to compare scenarios for
        snapshot_name: Name of the snapshot for display purposes
    """
    st.title("Scenario Comparison")
    st.markdown(f"Comparing scenarios for snapshot: **{snapshot_name}**")
    
    scenarios = get_scenarios_for_snapshot(snapshot_id)
    
    scenarios_with_results = [s for s in scenarios if s.get("optimization_results") is not None]
    
    if len(scenarios_with_results) < 2:
        st.warning("You need at least two scenarios with results to compare. Please run optimization on more scenarios.")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Return to Snapshot Management"):
                st.session_state.app_mode = 'snapshot_management'
                st.rerun()
        with col2:
            if st.button("Return to Scenario Management"):
                st.session_state.app_mode = 'scenario_management'
                st.rerun()
        
        st.stop()
    
    scenario_options = pd.DataFrame([
        {
            "Scenario ID": s["scenario_id"],
            "Scenario Name": s["scenario_name"],
            "Vehicles": s["config"]["num_vehicles"],
            "Capacity": s["config"]["vehicle_capacity"],
            "Results Date": s["optimization_results"]["timestamp"] if s.get("optimization_results") else "N/A"
        } for s in scenarios_with_results
    ])
    
    st.subheader("Select Scenarios to Compare")
    st.dataframe(scenario_options, use_container_width=True)
    
    selected_scenario_indices = st.multiselect(
        "Choose scenarios to compare:",
        options=list(range(len(scenarios_with_results))),
        format_func=lambda i: scenarios_with_results[i]["scenario_name"],
        default=list(range(min(2, len(scenarios_with_results))))
    )
    
    if len(selected_scenario_indices) < 2:
        st.warning("Please select at least two scenarios to compare.")
        st.stop()
    
    selected_scenarios = [scenarios_with_results[i] for i in selected_scenario_indices]
    
    comparison_data = []
    for scenario in selected_scenarios:
        results = scenario.get("optimization_results", {})
        if results:
            comparison_data.append({
                "Scenario Name": scenario["scenario_name"],
                "Vehicles": scenario["config"]["num_vehicles"],
                "Capacity": scenario["config"]["vehicle_capacity"],
                "Total Distance (km)": results.get("total_distance", 0),
                "Total Customers": results.get("total_customers", 0),
                "Total Demand": results.get("total_demand", 0),
                "Capacity Utilization (%)": results.get("capacity_utilization", 0)
            })
    
    if not comparison_data:
        st.error("Could not extract comparison data from the selected scenarios.")
        st.stop()
    
    st.subheader("Scenario Comparison")
    comparison_df = pd.DataFrame(comparison_data)
    st.dataframe(comparison_df, use_container_width=True)
    
    st.subheader("Comparison Visualizations")
    
    tab1, tab2, tab3 = st.tabs(["Distance", "Demand", "Utilization"])
    
    with tab1:
        distance_fig = px.bar(
            comparison_df,
            x="Scenario Name",
            y="Total Distance (km)",
            title="Total Distance Comparison",
            color="Scenario Name",
            text_auto='.2f'
        )
        distance_fig.update_layout(xaxis_title="Scenario", yaxis_title="Total Distance (km)")
        st.plotly_chart(distance_fig, use_container_width=True)
    
    with tab2:
        demand_fig = px.bar(
            comparison_df,
            x="Scenario Name",
            y="Total Demand",
            title="Total Demand Comparison",
            color="Scenario Name",
            text_auto=True
        )
        demand_fig.update_layout(xaxis_title="Scenario", yaxis_title="Total Demand")
        st.plotly_chart(demand_fig, use_container_width=True)
    
    with tab3:
        util_fig = px.bar(
            comparison_df,
            x="Scenario Name",
            y="Capacity Utilization (%)",
            title="Capacity Utilization Comparison",
            color="Scenario Name",
            text_auto='.2f'
        )
        util_fig.update_layout(xaxis_title="Scenario", yaxis_title="Capacity Utilization (%)")
        st.plotly_chart(util_fig, use_container_width=True)
    
    st.subheader("Multi-Metric Comparison")
    
    radar_df = comparison_df.copy()
    metrics = ["Total Distance (km)", "Total Customers", "Total Demand", "Capacity Utilization (%)"]
    
    for metric in metrics:
        max_val = radar_df[metric].max()
        if max_val > 0:  # Avoid division by zero
            radar_df[f"{metric} (normalized)"] = radar_df[metric] / max_val
    
    fig = go.Figure()
    
    for _, row in radar_df.iterrows():
        fig.add_trace(go.Scatterpolar(
            r=[row[f"{metric} (normalized)"] for metric in metrics],
            theta=metrics,
            fill='toself',
            name=row["Scenario Name"]
        ))
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 1]
            )
        ),
        title="Multi-Metric Comparison (Normalized)"
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Return to Snapshot Management"):
            st.session_state.app_mode = 'snapshot_management'
            st.rerun()
    with col2:
        if st.button("Return to Scenario Management"):
            st.session_state.app_mode = 'scenario_management'
            st.rerun()
