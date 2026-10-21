import fitdecode 
import json

def fit_to_json(input_path, output_path):
    messages = []

    with fitdecode.FitReader(input_path) as fit:
        for frame in fit: 
            if isinstance(frame, fitdecode.FitDataMessage):
                messages.append({
                    "type": frame.name,
                    "data": {
                        field.name: field.value
                        for field in frame.fields
                    }
                })
    
    with open(output_path, "w") as f:
        json.dump(messages, f, indent=2, default=str)

fit_to_json("./data/fit_files/activity.fit", "./data/activity.json")

def semicircle_to_degrees(value):
    return value * (180 / 2**31)

def extract_gps_points(input_path):
    with open(input_path) as f:
        messages = json.load(f)

    gps_points = []

    for msg in messages:
        if msg["type"] == "record":
            data = msg["data"]

            if "position_lat" in data and "position_long" in data:
                lat = semicircle_to_degrees(data["position_lat"])
                lon = semicircle_to_degrees(data["position_long"])

                gps_points.append([lon, lat])

    return gps_points

def gps_points_to_geojson(gps_points, output_path):

    geojson = {
        "type": "Feature",
        "geometry": {
            "type": "LineString",
            "coordinates": gps_points
        },
        "properties": {}
    }

    with open(output_path, "w") as f: 
        json.dump(geojson, f, indent=2)

gps_points_to_geojson(extract_gps_points("./data/activity.json"), "./data/route.geojson")