import pandas as pd
import json
from app.nlp_processor import process_query

# Load sample data
df = pd.read_csv('sample_data.csv')

# Prepare test data
depot = df[df['CustomerID'] == 'Depot'].iloc[0]
customers = df[df['CustomerID'] != 'Depot']

# Create sample route info
route_info = [
    {
        'vehicle_id': 1,
        'stops': [
            {'customer_id': 'C1', 'latitude': 40.7300, 'longitude': -74.0100, 'demand': 15},
            {'customer_id': 'C2', 'latitude': 40.7200, 'longitude': -73.9900, 'demand': 22},
            {'customer_id': 'C3', 'latitude': 40.7000, 'longitude': -74.0200, 'demand': 8}
        ],
        'total_distance': 5.2,
        'total_demand': 45,
        'route_text': 'Depot → C1 → C2 → C3 → Depot'
    },
    {
        'vehicle_id': 2,
        'stops': [
            {'customer_id': 'C4', 'latitude': 40.7400, 'longitude': -73.9800, 'demand': 17},
            {'customer_id': 'C5', 'latitude': 40.6900, 'longitude': -74.0300, 'demand': 12}
        ],
        'total_distance': 4.8,
        'total_demand': 29,
        'route_text': 'Depot → C4 → C5 → Depot'
    }
]

# Create KPI DataFrame
kpi_data = {
    'Vehicle': [1, 2],
    'Total Stops': [3, 2],
    'Distance (km)': [5.2, 4.8],
    'Total Demand': [45, 29],
    'Capacity Utilization (%)': [75.0, 48.3]
}
kpi_df = pd.DataFrame(kpi_data)

# Create detailed route DataFrame
detailed_data = []
for route in route_info:
    for stop in route['stops']:
        detailed_data.append({
            'Vehicle': route['vehicle_id'],
            'Stop Number': len(detailed_data) + 1,
            'Customer ID': stop['customer_id'],
            'Latitude': stop['latitude'],
            'Longitude': stop['longitude'],
            'Demand': stop['demand']
        })
detailed_df = pd.DataFrame(detailed_data)

# Test queries
test_queries = [
    "What's the total demand handled by Vehicle 1?",
    "Which vehicle traveled the most distance?",
    "Show a bar chart of demand per vehicle"
]

# Process each query
print("Testing NLP Processor...")
print("-" * 50)

for query in test_queries:
    print(f"\nQuery: {query}")
    try:
        result = process_query(query, route_info, kpi_df, detailed_df, vehicle_capacity=60)
        print("\nResponse:")
        print(result['response_text'])
        if result['visualization'] is not None:
            print("(Visualization available)")
    except Exception as e:
        print(f"Error: {str(e)}") 