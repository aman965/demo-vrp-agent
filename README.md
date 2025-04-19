# Vehicle Routing Problem (VRP) Solver

A Streamlit application for solving Capacitated Vehicle Routing Problems (CVRP) using Google OR-Tools.

## Features

- Upload customer data via CSV (CustomerID, Latitude, Longitude, Demand)
- Configure number of vehicles and vehicle capacity
- Compute optimal routes using OR-Tools
- Visualize routes on a map
- Export results to Excel

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
- CustomerID: Unique identifier for each customer
- Latitude: Customer location latitude
- Longitude: Customer location longitude
- Demand: Customer demand (numeric)

The first row (index 0) is assumed to be the depot.
