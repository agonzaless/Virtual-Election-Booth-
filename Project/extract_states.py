import json

# Read the full states file
with open('static/geojson/states.json', 'r') as f:
    all_states = json.load(f)

# State FIPS codes for our demo states
state_fips = {
    'Texas': '48',
    'California': '06',
    'Illinois': '17',
    'New York': '36',
    'Florida': '12'
}

# Extract each state
for state, fips in state_fips.items():
    state_data = {
        "type": "FeatureCollection",
        "features": [
            feature for feature in all_states['features']
            if feature['properties']['R_STATEFP'] == fips
        ]
    }

    # Save individual state file
    filename = f"static/geojson/{state.lower().replace(' ', '')}.json"
    with open(filename, 'w') as f:
        json.dump(state_data, f)

print("State files created successfully!")

