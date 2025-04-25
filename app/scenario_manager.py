import streamlit as st
import pandas as pd
import os
import datetime
import json
import uuid
import numpy as np
from pathlib import Path
from nlp_processor import process_query
from utils.json_utils import CustomJSONEncoder
from snapshot_manager import get_snapshot_by_id
import traceback

def get_scenarios_dir():
    """Get the path to the scenarios directory, creating it if it doesn't exist."""
    repo_dir = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) / ".data" / "scenarios"
    os.makedirs(repo_dir, exist_ok=True)
    return repo_dir

def save_scenario(snapshot_id, scenario_name, num_vehicles, vehicle_capacity, constraints=None, constraint_prompt=None, constraint_analysis=None, prompt_history=None):
    """
    Save a scenario configuration to a JSON file.
    
    Args:
        snapshot_id: ID of the snapshot this scenario is based on
        scenario_name: Name of the scenario
        num_vehicles: Number of vehicles for this scenario
        vehicle_capacity: Vehicle capacity for this scenario
        constraints: Optional text constraints for this scenario
        constraint_prompt: Optional custom prompt for constraint handling
        constraint_analysis: Optional analysis of the constraint prompt
        prompt_history: Optional list of dicts containing previous prompt attempts and their analyses
        
    Returns:
        dict: Metadata about the saved scenario
    """
    if not scenario_name:
        scenario_name = f"scenario_{uuid.uuid4().hex[:8]}"
    
    scenario_id = f"scenario_{uuid.uuid4().hex[:8]}"
    
    # Extract extra_constraints from the analysis if available
    extra_constraints = None
    if constraint_analysis and isinstance(constraint_analysis, dict):
        extra_constraints = constraint_analysis.get('constraints', {})
    
    scenario_data = {
        "scenario_id": scenario_id,
        "scenario_name": scenario_name,
        "snapshot_id": snapshot_id,
        "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "config": {
            "num_vehicles": num_vehicles,
            "vehicle_capacity": vehicle_capacity,
            "extra_constraints": extra_constraints  # Add extra_constraints to config
        },
        "constraints": constraints,
        "constraint_prompt": constraint_prompt,
        "constraint_analysis": constraint_analysis,
        "prompt_history": prompt_history if prompt_history else [],
        "optimization_results": None
    }
    
    scenarios_dir = get_scenarios_dir()
    file_path = scenarios_dir / f"{scenario_id}.json"
    
    with open(file_path, "w") as f:
        json.dump(scenario_data, f, indent=2, cls=CustomJSONEncoder)
    
    return scenario_data

def get_scenarios_for_snapshot(snapshot_id):
    """
    Get all scenarios for a specific snapshot.
    
    Args:
        snapshot_id: ID of the snapshot to get scenarios for
        
    Returns:
        list: List of scenario data dictionaries
    """
    scenarios_dir = get_scenarios_dir()
    scenarios = []
    
    for file_path in scenarios_dir.glob("*.json"):
        try:
            with open(file_path, "r") as f:
                scenario_data = json.load(f)
                
            if scenario_data.get("snapshot_id") == snapshot_id:
                scenarios.append(scenario_data)
        except Exception as e:
            st.error(f"Error reading scenario file {file_path.name}: {str(e)}")
    
    scenarios.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    
    return scenarios

def add_scenario_to_snapshot(snapshot_id, scenario_id):
    """
    Add a scenario ID to a snapshot's list of scenarios.
    
    Args:
        snapshot_id: ID of the snapshot to update
        scenario_id: ID of the scenario to add
        
    Returns:
        bool: True if successful, False otherwise
    """
    from snapshot_manager import get_snapshot_by_id, update_snapshot_scenarios
    
    snapshot = get_snapshot_by_id(snapshot_id)
    if not snapshot:
        return False
    
    return update_snapshot_scenarios(snapshot_id, scenario_id)

def get_scenario_by_id(scenario_id):
    """
    Get a scenario by its ID.
    
    Args:
        scenario_id: ID of the scenario to get
        
    Returns:
        dict: Scenario data or None if not found
    """
    scenarios_dir = get_scenarios_dir()
    file_path = scenarios_dir / f"{scenario_id}.json"
    
    if not file_path.exists():
        return None
    
    try:
        with open(file_path, "r") as f:
            scenario_data = json.load(f)
        return scenario_data
    except Exception as e:
        st.error(f"Error reading scenario file {file_path.name}: {str(e)}")
        return None

def update_scenario_results(scenario_id, results):
    """
    Update a scenario with optimization results.
    
    Args:
        scenario_id: ID of the scenario to update
        results: Optimization results to save
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        scenario_data = get_scenario_by_id(scenario_id)
        if not scenario_data:
            st.error(f"Could not find scenario with ID: {scenario_id}")
            return False
        
        # Ensure all numpy/pandas objects are converted to basic Python types
        clean_results = {
            'total_distance': float(results.get('total_distance', 0)),
            'total_customers': int(results.get('total_customers', 0)),
            'total_demand': int(results.get('total_demand', 0)),
            'capacity_utilization': float(results.get('capacity_utilization', 0)),
            'route_summary': results.get('route_summary', []),
            'route_info': results.get('route_info', []),
            'kpi_df': results.get('kpi_df', []),
            'detailed_df': results.get('detailed_df', []),
            'vehicle_capacity': int(results.get('vehicle_capacity', 0)),
            'timestamp': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Add implementation notes to the last prompt history entry if it exists
        if (scenario_data.get('prompt_history') and 
            len(scenario_data['prompt_history']) > 0 and 
            results.get('solution_data', {}) and 
            results['solution_data'].get('implementation_notes')):
            
            last_prompt = scenario_data['prompt_history'][-1]
            if not last_prompt.get('implementation_notes'):
                last_prompt['implementation_notes'] = results['solution_data']['implementation_notes']
                scenario_data['prompt_history'][-1] = last_prompt
        
        scenario_data["optimization_results"] = clean_results
        
        scenarios_dir = get_scenarios_dir()
        file_path = scenarios_dir / f"{scenario_id}.json"
        
        with open(file_path, "w") as f:
            json.dump(scenario_data, f, indent=2, cls=CustomJSONEncoder)
        return True
        
    except Exception as e:
        st.error(f"Error updating scenario results: {str(e)}")
        return False

def display_constraint_feedback_ui():
    """
    Display the feedback from ChatGPT for constraint modifications in a well-formatted way.
    Includes buttons for accepting or retrying the changes.
    
    The function expects st.session_state.current_prompt_response to contain:
    {
        "prompt": str,  # User prompt
        "analysis": {
            "constraints": dict,
            "summary": str,
            "notes": str (optional)
        }
    }
    """
    if not hasattr(st.session_state, 'current_prompt_response'):
        st.warning("No constraint feedback to display.")
        return
    
    response = st.session_state.current_prompt_response
    
    # Display the original prompt
    st.subheader("Your Request")
    st.text(response["prompt"])
    
    st.subheader("ChatGPT's Analysis")
    
    # Display summary in bold
    st.markdown(f"**{response['analysis']['summary']}**")
    
    # Display constraints as bullet points
    st.subheader("Updated Constraints")
    for key, value in response['analysis']['constraints'].items():
        st.markdown(f"• **{key}**: {value}")
    
    # Display notes if present
    if 'notes' in response['analysis'] and response['analysis']['notes']:
        st.subheader("Additional Notes")
        st.markdown(f"*{response['analysis']['notes']}*")
    
    # Add buttons in columns for better layout
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("✅ Accept and Save to Scenario"):
            # Check if we have the required scenario information
            if not st.session_state.get('scenario_name'):
                st.warning("Please enter a scenario name before accepting the constraints.")
                return
            
            if not st.session_state.get('snapshot_id'):
                st.warning("No snapshot selected. Please select a snapshot first.")
                return
            
            # Add to prompt history
            if 'prompt_history' not in st.session_state:
                st.session_state.prompt_history = []
            
            st.session_state.prompt_history.append({
                'prompt': response['prompt'],
                'analysis': response['analysis'],
                'accepted': True
            })
            
            # Extract constraints for the scenario
            extra_constraints = response['analysis']['constraints']
            
            # Save the scenario with the extracted constraints
            with st.spinner("Saving scenario with constraints..."):
                scenario_data = save_scenario(
                    snapshot_id=st.session_state.snapshot_id,
                    scenario_name=st.session_state.scenario_name,
                    num_vehicles=st.session_state.get('num_vehicles', 5),
                    vehicle_capacity=st.session_state.get('vehicle_capacity', 100),
                    constraints=extra_constraints,
                    constraint_prompt=response['prompt'],
                    constraint_analysis=response['analysis'],
                    prompt_history=st.session_state.prompt_history
                )
                
                # Add the scenario to the snapshot's list of scenarios
                if add_scenario_to_snapshot(st.session_state.snapshot_id, scenario_data["scenario_id"]):
                    st.success(f"Scenario '{scenario_data['scenario_name']}' saved successfully with constraints!")
                    
                    # Clear the current prompt response to hide the feedback panel
                    if hasattr(st.session_state, 'current_prompt_response'):
                        del st.session_state.current_prompt_response
                    
                    # Rerun to refresh the UI
                    st.rerun()
                else:
                    st.error("Failed to add scenario to snapshot. Please try again.")
            
    with col2:
        if st.button("🔁 Retry with Updated Prompt"):
            st.info("Please provide an updated prompt...")
            # Store the current prompt in session state for retry
            st.session_state.retry_prompt = response['prompt']
            # Clear current response to hide feedback panel
            if hasattr(st.session_state, 'current_prompt_response'):
                del st.session_state.current_prompt_response
            st.rerun()

def scenario_management_ui(snapshot_id, snapshot_name):
    """
    Display the scenario management UI for a specific snapshot.
    
    Args:
        snapshot_id: ID of the snapshot to manage scenarios for
        snapshot_name: Name of the snapshot for display purposes
        
    Returns:
        tuple: (selected_scenario, run_optimization) if a scenario is selected and the user wants to run optimization,
               otherwise (None, False)
    """
    st.title("Scenario Management")
    st.markdown(f"Managing scenarios for snapshot: **{snapshot_name}**")
    
    # Add GPT Test Button
    if st.button("🧪 Test OpenAI API Call"):
        try:
            from nlp_processor import client, MODEL_NAME
            if client is None:
                st.error("❌ OpenAI client not initialized. Please check your API key configuration.")
            else:
                response = client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=[{"role": "user", "content": "Say hello in one sentence."}]
                )
                st.success("✅ GPT Response: " + response.choices[0].message.content)
        except Exception as e:
            st.error(f"❌ GPT API call failed: {str(e)}")
            st.error(f"Detailed error: {traceback.format_exc()}")
    
    # Display constraint feedback if available
    if hasattr(st.session_state, 'current_prompt_response'):
        display_constraint_feedback_ui()
        st.markdown("---")  # Add a separator after the feedback
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Create New Scenario")
        
        scenario_name = st.text_input("Scenario Name", placeholder="Enter a descriptive name for this scenario")
        
        num_vehicles = st.number_input(
            "Number of Vehicles",
            min_value=1,
            max_value=100,
            value=5
        )
        
        vehicle_capacity = st.number_input(
            "Vehicle Capacity",
            min_value=1,
            max_value=10000,
            value=100
        )
        
        constraints = st.text_area(
            "Additional Constraints (Optional)",
            placeholder="Enter any additional constraints or notes for this scenario",
            help="This is for documentation purposes only and doesn't affect the optimization."
        )
        
        # Check if we have a retried prompt
        default_prompt = st.session_state.get('retry_prompt', '')
        if default_prompt:
            st.info("📝 Retrying previous prompt")
            
        constraint_prompt = st.text_input(
            "Custom Constraint Prompt (optional)",
            value=default_prompt,
            placeholder="Enter a custom prompt for constraint handling",
            help="Specify custom instructions for handling constraints in natural language",
            key="constraint_prompt"
        )
        
        # Clear retry prompt after using it
        if default_prompt:
            st.session_state.retry_prompt = ''
        
        # Initialize session state for constraint analysis if not exists
        if 'constraint_analysis' not in st.session_state:
            st.session_state.constraint_analysis = None
            st.session_state.constraint_history = []
        
        # Process constraint prompt if provided
        if constraint_prompt:
            # Only process if prompt changed or Retry clicked
            if (not st.session_state.constraint_analysis or 
                constraint_prompt != st.session_state.get('last_prompt', '')):
                
                with st.spinner("Analyzing constraint prompt..."):
                    # Add previous attempts to context if they exist
                    context = f"Scenario configuration:\n- Number of vehicles: {num_vehicles}\n- Vehicle capacity: {vehicle_capacity}\n"
                    if st.session_state.constraint_history:
                        context += "\nPrevious attempts:\n"
                        for i, prev in enumerate(st.session_state.constraint_history, 1):
                            context += f"\nAttempt {i}:\n{prev['prompt']}\n"
                    
                    constraint_analysis = process_query(
                        query=constraint_prompt,
                        context=context,
                        mode="constraint_extraction"
                    )
                    
                    # Add implementation notes if constraints were extracted
                    if constraint_analysis.get('constraints'):
                        implementation_notes = []
                        for constraint in constraint_analysis['constraints']:
                            implementation_notes.append(f"- {constraint}")
                        constraint_analysis['implementation_notes'] = "\n".join(implementation_notes)
                    
                    st.session_state.constraint_analysis = constraint_analysis
                    st.session_state.last_prompt = constraint_prompt
            
            # Display GPT's interpretation immediately after analysis
            if st.session_state.constraint_analysis:
                st.markdown("---")
                st.markdown("### 🧠 GPT Interpretation")
                
                if st.session_state.constraint_analysis.get("summary"):
                    st.markdown("**" + st.session_state.constraint_analysis["summary"] + "**")
                
                if st.session_state.constraint_analysis.get("constraints"):
                    st.markdown("#### Extracted Constraints:")
                    for constraint in st.session_state.constraint_analysis["constraints"]:
                        st.markdown(f"• {constraint}")
                
                if st.session_state.constraint_analysis.get("notes"):
                    st.markdown("#### Additional Notes:")
                    st.markdown("*" + st.session_state.constraint_analysis["notes"] + "*")
                
                if st.session_state.constraint_analysis.get("implementation_notes"):
                    st.markdown("#### Implementation Details:")
                    st.markdown(st.session_state.constraint_analysis["implementation_notes"])
                
                st.markdown("---")
            
            # Add Accept and Retry buttons in columns
            col1, col2 = st.columns(2)
            with col1:
                accept = st.button("✅ Accept and Save Scenario")
            with col2:
                retry = st.button("🔁 Retry with New Prompt")
            
            if retry:
                # Store current attempt in history with accepted=False
                st.session_state.constraint_history.append({
                    'prompt': constraint_prompt,
                    'analysis': st.session_state.constraint_analysis,
                    'accepted': False
                })
                # Clear current analysis to trigger reprocessing
                st.session_state.constraint_analysis = None
                st.session_state.last_prompt = None
                st.rerun()
            
            if accept:
                with st.spinner("Saving scenario..."):
                    # Store current attempt in history with accepted=True
                    current_attempt = {
                        'prompt': constraint_prompt,
                        'analysis': st.session_state.constraint_analysis,
                        'accepted': True
                    }
                    prompt_history = st.session_state.constraint_history + [current_attempt]
                    
                    scenario_data = save_scenario(
                        snapshot_id=snapshot_id,
                        scenario_name=scenario_name,
                        num_vehicles=num_vehicles,
                        vehicle_capacity=vehicle_capacity,
                        constraints=constraints if constraints else None,
                        constraint_prompt=constraint_prompt,
                        constraint_analysis=st.session_state.constraint_analysis,
                        prompt_history=prompt_history
                    )
                    
                    # Add the scenario to the snapshot's list of scenarios
                    add_scenario_to_snapshot(snapshot_id, scenario_data["scenario_id"])
                    
                    st.success(f"Scenario '{scenario_data['scenario_name']}' saved successfully!")
                    
                    # Clear constraint history and analysis after successful save
                    st.session_state.constraint_analysis = None
                    st.session_state.constraint_history = []
                    st.session_state.last_prompt = None
                    
                    st.rerun()
        
        # Only show the regular save button if no constraint prompt is provided
        elif st.button("Save Scenario"):
            with st.spinner("Saving scenario..."):
                scenario_data = save_scenario(
                    snapshot_id=snapshot_id,
                    scenario_name=scenario_name,
                    num_vehicles=num_vehicles,
                    vehicle_capacity=vehicle_capacity,
                    constraints=constraints if constraints else None
                )
                
                # Add the scenario to the snapshot's list of scenarios
                add_scenario_to_snapshot(snapshot_id, scenario_data["scenario_id"])
                
                st.success(f"Scenario '{scenario_data['scenario_name']}' saved successfully!")
                st.rerun()
    
    with col2:
        st.subheader("What is a Scenario?")
        st.markdown("""
        A scenario is a specific configuration for solving the Vehicle Routing Problem:
        
        - **Number of Vehicles**: How many vehicles are available
        - **Vehicle Capacity**: Maximum load each vehicle can carry
        - **Constraints**: Any additional notes or constraints
        
        Create multiple scenarios to compare different configurations.
        """)
    
    st.subheader("Saved Scenarios")
    scenarios = get_scenarios_for_snapshot(snapshot_id)
    
    if not scenarios:
        st.info("No scenarios have been created yet for this snapshot. Create your first scenario above.")
        return None, False
    
    scenarios_df = pd.DataFrame([
        {
            "Scenario Name": s["scenario_name"],
            "Created": s["created_at"],
            "Vehicles": s["config"]["num_vehicles"],
            "Capacity": s["config"]["vehicle_capacity"],
            "Results": "Available" if s.get("optimization_results") else "Not Run"
        } for s in scenarios
    ])
    
    st.dataframe(scenarios_df, use_container_width=True)
    
    selected_index = st.selectbox(
        "Select a scenario to use:",
        options=range(len(scenarios)),
        format_func=lambda i: scenarios[i]["scenario_name"]
    )
    
    selected_scenario = scenarios[selected_index]
    
    st.subheader(f"Selected: {selected_scenario['scenario_name']}")
    
    # Add Debug Info Section
    with st.expander("📦 Scenario Debug Info"):
        st.json(selected_scenario)
        
        if selected_scenario.get("config", {}).get("extra_constraints"):
            st.subheader("Extra Constraints")
            st.json(selected_scenario["config"]["extra_constraints"])
        
        if selected_scenario.get("constraint_analysis"):
            st.subheader("Constraint Analysis")
            st.json(selected_scenario["constraint_analysis"])
        
        if selected_scenario.get("prompt_history"):
            st.subheader("Prompt History")
            st.container()
            for i, entry in enumerate(selected_scenario["prompt_history"]):
                st.markdown(f"""
                ---
                ### Prompt {i+1} {'✅ Accepted' if entry.get('accepted') else '❌ Rejected'}
                
                **Prompt Text:**
                ```
                {entry.get('prompt', '')}
                ```
                
                **Analysis:**
                ```json
                {json.dumps(entry.get('analysis', {}), indent=2)}
                ```
                
                {f"**Implementation Notes:**\n```\n{entry.get('implementation_notes', '')}\n```" if entry.get('implementation_notes') else ''}
                """)
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Number of Vehicles", selected_scenario["config"]["num_vehicles"])
    with col2:
        st.metric("Vehicle Capacity", selected_scenario["config"]["vehicle_capacity"])
    
    if selected_scenario.get("constraints"):
        st.markdown(f"**Constraints:** {selected_scenario['constraints']}")
    
    has_results = selected_scenario.get("optimization_results") is not None
    
    if has_results:
        st.success("This scenario has been run. You can view the results or run it again.")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("View Results"):
                st.session_state.view_scenario_results = selected_scenario["scenario_id"]
                return selected_scenario, False
        with col2:
            if st.button("Run Again", type="primary"):
                return selected_scenario, True
    else:
        if st.button("Run Optimization", type="primary"):
            return selected_scenario, True
    
    return None, False

def try_switch_page(page_name, fallback_message=None):
    """Helper function to safely switch pages with fallback."""
    try:
        st.switch_page(page_name)
    except Exception as e:
        if fallback_message:
            st.warning(fallback_message)
        else:
            st.warning(f"Unable to switch to page '{page_name}'. The page may have been moved or renamed.")
        st.error(f"Error: {str(e)}")
