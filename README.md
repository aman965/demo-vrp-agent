# Vehicle Routing Problem (VRP) Solver

A Streamlit application for solving Capacitated Vehicle Routing Problems (CVRP) using Google OR-Tools with advanced data management, visualization, and AI-powered analysis capabilities.

## Features

### Core Functionality
- Upload customer data via CSV (CustomerID, Latitude, Longitude, Demand)
- Configure number of vehicles and vehicle capacity
- Compute optimal routes using Google OR-Tools
- Visualize routes on interactive maps using Folium
- Display comprehensive Key Performance Indicators (KPIs)
- Export results to Excel

### Hierarchical Data Management System
The application implements a three-level hierarchical data management system:

1. **Input Repository**
   - Upload and manage multiple input CSV files
   - View file metadata (name, upload date, row count)
   - Select input files for analysis

2. **Snapshots**
   - Create named references to specific input datasets
   - Add descriptions to document snapshot purpose
   - Manage multiple snapshots for different analyses
   - Access Chat Assistant and Scenario Comparison for each snapshot

3. **Scenarios**
   - Define multiple parameter configurations for each snapshot
   - Configure vehicle count and capacity per scenario
   - Run optimization with different parameters
   - Save optimization results for later comparison

### Advanced Analytics
- **KPI Dashboard**
  - Total distance traveled per vehicle
  - Total distance across all vehicles
  - Number of customers visited per vehicle
  - Demand delivered per vehicle
  - Vehicle capacity utilization percentage
  - Comprehensive KPI table with per-vehicle metrics

- **Visualizations**
  - Interactive route maps with Folium
  - Bar charts of distance per vehicle
  - Pie/bar charts of demand utilization
  - Summary cards showing total distance and delivery success

### AI-Powered Analysis
- **Chat Assistant**
  - GPT-4 powered natural language interface
  - Ask questions about optimization results
  - Request specific KPI information
  - Compare scenarios within a snapshot
  - Generate custom visualizations based on queries

- **Scenario Comparison**
  - Side-by-side comparison of multiple scenarios
  - Visual comparison of key metrics across scenarios
  - Identify optimal configurations based on different objectives
  - Export comparison results

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```bash
streamlit run app/main.py
```

## Input Format

The CSV file should contain the following columns:
- **CustomerID**: Unique identifier for each customer
- **Latitude**: Customer location latitude
- **Longitude**: Customer location longitude
- **Demand**: Customer demand (numeric)

The first row (index 0) is assumed to be the depot.

## Application Workflow

1. **Input Repository**: Upload or select an existing CSV file
2. **Snapshot Management**: Create a snapshot from the selected input file
3. **Scenario Management**: Create scenarios with different parameters for the selected snapshot
4. **Optimization**: Run the CVRP solver for a specific scenario
5. **Results Viewing**: View routes, KPIs, and visualizations for the optimization
6. **Chat Assistant**: Ask questions about the optimization results
7. **Scenario Comparison**: Compare results across multiple scenarios

## Technical Details

- Built with Streamlit for the web interface
- Uses Google OR-Tools for CVRP optimization
- Integrates OpenAI's GPT-4 for natural language processing
- Implements Folium and Plotly for interactive visualizations
- Stores data persistently in JSON format
- Provides robust error handling and logging
