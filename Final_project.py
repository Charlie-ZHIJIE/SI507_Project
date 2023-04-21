#
# Name:Zhijie Xu
#
import csv
import math
import os
import time
from datetime import datetime, timedelta
import json
from io import StringIO

from flask import Flask, render_template, request, jsonify, send_from_directory, render_template_string
import mplcursors
import requests
import networkx as nx
import matplotlib.pyplot as plt
from diskcache import Cache


cache = Cache(directory=".cache")
# API keys
FLIGHTSTATS_APP_ID = "76c17a96"
FLIGHTSTATS_APP_KEY = "a5f1d9697ca04c999a178cf8c7a40854"
NOAA_API_KEY = 'YxapKqtuzRCMTiycgacGdCbFSSxumDVg'

# Mapping between airport codes and station IDs TOP100 busy Airport in America
#tranfer to using json file

# Get real-time flight information
# Function to get real-time flight information
def get_flight_delay_data(airport):
    cache_key = f"flight_delay_data:{airport}"
    if cache_key in cache:
        return cache[cache_key]
    url = f"https://api.flightstats.com/flex/delayindex/rest/v1/json/airports/{airport}/"
    params = {
        "appId": FLIGHTSTATS_APP_ID,
        "appKey": FLIGHTSTATS_APP_KEY,
    }
    data = requests.get(url, params=params).json()
    data = data['delayIndexes']
    flights = {}
    for airport in data:
        flight_data = {}
        airport_name = airport["airport"]["fs"]
        flight_data["flights"] = airport["flights"]
        flight_data['observations'] = airport["observations"]
        flight_data['canceled'] = airport["canceled"]
        flight_data['onTime'] = airport["onTime"]
        flight_data['delayed15'] = airport["delayed15"]
        flight_data['delayed30'] = airport["delayed30"]
        flight_data['delayed45'] = airport["delayed45"]
        flight_data['averageDelay'] = (15 * int(airport["delayed15"]) + 30 * int(airport["delayed30"]) + 45 * int(
            airport["delayed45"])) / int(airport["flights"] + 1)
        flights[airport_name] = flight_data
    cache.set(cache_key, flights, expire=3600)  # Cache for 1 hour
    return flights

# Function to get NOAA weather data for a specific station ID
def get_noaa_data(station_id):
    cache_key = f"noaa_data:{station_id}"
    if cache_key in cache:
        return cache[cache_key]
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=7)
    # Build the API request URL
    url = f"https://www.ncei.noaa.gov/access/services/data/v1?dataset=daily-summaries&dataTypes=TMAX,TMIN,PRCP&stations={station_id}&startDate={start_date}&endDate={end_date}&includeAttributes=true&includeStationName=true&format=json&units=metric&limit=1000&token={NOAA_API_KEY}"
    # Send the API request and process the response
    response = requests.get(url).json()
    cache.set(cache_key, response, expire=3600)  # Cache for 1 hour
    return response

# Function to get historical weather data for the past 7 days
def get_historical_weather_data(station_id):
    data = get_noaa_data(station_id)
    return data

# Function to get live weather data and forecast for multiple airports
def get_flight_weatherdata_andForecast(airports):
    result = []
    flight_data_combine = {}
    for airport in airports:
        url = f"https://api.flightstats.com/flex/weather/rest/v1/json/all/{airport}/"
        params = {
            "appId": FLIGHTSTATS_APP_ID,
            "appKey": FLIGHTSTATS_APP_KEY,
        }
        data = requests.get(url, params=params).json()
        flight_data = {}
        airport_name = airport
        flight_data["conditions"] = data["metar"]['conditions']
        flight_data['temperatureCelsius'] = data["metar"]['temperatureCelsius']
        # flight_data['forecasts'] = data['taf']['forecasts']
        flight_data_combine[airport_name] = flight_data
        result.append(flight_data_combine)
    return flight_data_combine

def calculate_flight_time(origin, destination, avg_speed=800.0):
    data_url = "https://ourairports.com/data/airports.csv"
    csv_data = fetch_airport_data(data_url)

    if csv_data:
        airports = parse_airport_data(csv_data)
        iata_code = origin  # IATA code for Los Angeles International Airport (LAX)
        coordinates = get_airport_coordinates(iata_code, airports)
    if csv_data:
        airports = parse_airport_data(csv_data)
        iata_code = destination
        coordinates1 = get_airport_coordinates(iata_code, airports)
    # Get the latitude and longitude for the origin and destination airports
    origin_lat, origin_lon = coordinates
    destination_lat, destination_lon = coordinates1

    # Convert latitude and longitude from degrees to radians
    origin_lat_rad = math.radians(origin_lat)
    origin_lon_rad = math.radians(origin_lon)
    destination_lat_rad = math.radians(destination_lat)
    destination_lon_rad = math.radians(destination_lon)

    # Calculate the great-circle distance using the spherical law of cosines
    distance = math.acos(math.sin(origin_lat_rad) * math.sin(destination_lat_rad) +
                         math.cos(origin_lat_rad) * math.cos(destination_lat_rad) *
                         math.cos(origin_lon_rad - destination_lon_rad)) * 6371

    # Estimate the flight time based on the distance and average speed
    time_hours = distance / avg_speed

    return time_hours

# next 3 function is using calculate average time for flight
def fetch_airport_data(url):
    response = requests.get(url)

    if response.status_code == 200:
        return response.text
    else:
        print(f"Error fetching airport data: {response.status_code}")
        return None

def parse_airport_data(csv_data):
    airports = {}
    reader = csv.DictReader(StringIO(csv_data))

    for row in reader:
        iata_code = row["iata_code"]
        if iata_code and len(iata_code) == 3:
            airports[iata_code] = {
                "name": row["name"],
                "latitude": float(row["latitude_deg"]),
                "longitude": float(row["longitude_deg"]),
            }

    return airports

def get_airport_coordinates(iata_code, airports):
    if iata_code in airports:
        return airports[iata_code]["latitude"], airports[iata_code]["longitude"]
    else:
        print(f"Airport with IATA code '{iata_code}' not found.")
        return None

# Function to create a network graph based on delay and weather data
def create_network_graph(delay_data, his_weather_data, liveandforecast_weather_data, airport_codes):
    graph = {'vertices': {}, 'edges': {}}

    # Add vertices (airports)
    for airport in airport_codes:
        #print(airport)
        #print(his_weather_data[airport])
        graph['vertices'][airport] = {
            'history_weather_last7day': his_weather_data[airport],
            'live_weather': liveandforecast_weather_data[airport]["conditions"]
            # 'forecast_weather': liveandforecast_weather_data[airport]["forecasts"]
        }

    # Add edges (flight connections) with attributes
    for airport in airport_codes:
        for airport_in in airport_codes:
            if airport_in != airport:
                graph['edges'][str(airport) + "-" + str(airport_in)] = delay_data[airport]["averageDelay"] + \
                                                                       delay_data[airport_in]["averageDelay"]
    return graph

# Function to draw a network graph and save it as an image file
def draw_graph(graph, airport_codes):
    # Create an empty directed graph
    G = nx.DiGraph()
    # Add vertices (nodes) with weather attributes
    for airport in airport_codes:
        data = []
        his_data_sum = ""
        del (graph['vertices'][airport]['live_weather']['wind']['directionIsVariable'])
        for item in graph['vertices'][airport]['history_weather_last7day']:
            #print(item)
            if 'TMAX' in item:
                his_data = "his date " + item['DATE'] + '\n' + "his TMAX " + item['TMAX'] + '\n' + 'his TMIN' + item[
                    'TMIN'] + '\n' + 'his PRCP' + item['PRCP'] + '\n'
                his_data_sum = his_data_sum + str(his_data)
        #print(graph['vertices'][airport]['history_weather_last7day'][3])
        data.append(
            "live wind: " + str(graph['vertices'][airport]['live_weather']['wind']) + '\n' + "live visibility: " + str(
                graph['vertices'][airport]['live_weather']['visibility']) + '\n' + "live skyConditions: " + str(
                graph['vertices'][airport]['live_weather']['skyConditions']) + '\n' + "live weatherConditions: " + str(
                graph['vertices'][airport]['live_weather'][
                    'weatherConditions']) + '\n' + "live pressureInchesHg: " + str(
                graph['vertices'][airport]['live_weather']['pressureInchesHg']) + '\n')
        graph['vertices'][airport]['live_weather']
        G.add_node(airport, weather=data[0] + his_data_sum)
    # Add edges with attributes (average delay and weather preference)
    for airport in airport_codes:
        for airport_in in airport_codes:
            if airport_in != airport:
                check = str(airport_in + '-' + airport)
                G.add_edge(airport, airport_in, avg_delay=graph['edges'][check], weather='live')

    # Draw the graph
    plt.figure(figsize=(15, 15))
    pos = nx.spring_layout(G, seed=52)
    nx.draw(G, pos, with_labels=True, node_color="lightblue", font_size=8, font_weight='bold', node_size=2000)
    edge_labels = nx.get_edge_attributes(G, 'avg_delay')
    nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels)
    # Add weather information to node labels
    node_weather = nx.get_node_attributes(G, 'weather')
    for node, weather in node_weather.items():
        x, y = pos[node]
        if x < 0:
            x_change = 0.2
        elif x > 0.5:
            x_change = -0.2
        else:
            x_change = 0
        if y > 0.9:
            y_change = 0.35
        elif y < -0.9:
            y_change = -0.35
        else:
            y_change = 0
        plt.text(x + x_change, y + 0.03 - y_change, weather, fontsize=8, ha='center')
    # Show the graph
    plt.title("Airport Connections with Weather Information")
    # Add interactive tooltips
    mplcursors.cursor(hover=True)
    # Save the figure as a PNG file and return the filename
    filename = "airport_graph.png"
    plt.savefig(filename, dpi=300)
    return filename

# Function to draw and show a network graph (useful for debugging and commandline interface)
def draw_graph_show(graph, airport_codes):
    # Create an empty directed graph
    G = nx.DiGraph()
    # Add vertices (nodes) with weather attributes
    for airport in airport_codes:
        data = []
        his_data_sum = ""
        del (graph['vertices'][airport]['live_weather']['wind']['directionIsVariable'])
        for item in graph['vertices'][airport]['history_weather_last7day']:
            if 'TMAX' in item:
                his_data = "his date " + item['DATE'] + '\n' + "his TMAX " + item['TMAX'] + '\n' + 'his TMIN' + item[
                    'TMIN'] + '\n' + 'his PRCP' + item['PRCP'] + '\n'
                his_data_sum = his_data_sum + str(his_data)
        #print(graph['vertices'][airport]['history_weather_last7day'][3])
        data.append(
            "live wind: " + str(graph['vertices'][airport]['live_weather']['wind']) + '\n' + "live visibility: " + str(
                graph['vertices'][airport]['live_weather']['visibility']) + '\n' + "live skyConditions: " + str(
                graph['vertices'][airport]['live_weather']['skyConditions']) + '\n' + "live weatherConditions: " + str(
                graph['vertices'][airport]['live_weather'][
                    'weatherConditions']) + '\n' + "live pressureInchesHg: " + str(
                graph['vertices'][airport]['live_weather']['pressureInchesHg']) + '\n')
        graph['vertices'][airport]['live_weather']
        G.add_node(airport, weather=data[0] + his_data_sum)
    # Add edges with attributes (average delay and weather preference)
    for airport in airport_codes:
        for airport_in in airport_codes:
            if airport_in != airport:
                check = str(airport_in + '-' + airport)
                G.add_edge(airport, airport_in, avg_delay=graph['edges'][check], weather='live')

    # Draw the graph
    plt.figure(figsize=(15, 15))
    pos = nx.spring_layout(G, seed=52)
    nx.draw(G, pos, with_labels=True, node_color="lightblue", font_size=8, font_weight='bold', node_size=2000)
    edge_labels = nx.get_edge_attributes(G, 'avg_delay')
    nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels)
    # Add weather information to node labels
    node_weather = nx.get_node_attributes(G, 'weather')
    for node, weather in node_weather.items():
        x, y = pos[node]
        if x < 0:
            x_change = 0.2
        elif x > 0.5:
            x_change = -0.2
        else:
            x_change = 0
        if y > 0.9:
            y_change = 0.35
        elif y < -0.9:
            y_change = -0.35
        else:
            y_change = 0
        plt.text(x + x_change, y + 0.03 - y_change, weather, fontsize=8, ha='center')
    # Show the graph
    plt.title("Airport Connections with Weather Information")
    plt.show()

# Function to periodically update the cache for the provided airport codes
def update_cache_periodically(airport_codes):
    while True:
        for airport in airport_codes:
            print(f"Updating cache for airport {airport}")
            get_flight_delay_data(airport)
            get_noaa_data(airport)
            get_flight_weatherdata_andForecast([airport])

        time.sleep(3600)  # Update cache every 1 hour

# Function to load airport and station mapping from a JSON file
def load_airport_station_mapping_graph():
    with open("airport_station_mapping.json", "r") as f:
        mapping = json.load(f)
    return mapping

def analysis_flightTime_delay(delay_data, his_weather_data, liveandforecast_weather_data, airport_codes):
    graph = {'vertices': {}, 'edges': {}}

    # Add vertices (airports)
    for airport in airport_codes:
        #print(airport)
        #print(his_weather_data[airport])
        graph['vertices'][airport] = {
            'history_weather_last7day': his_weather_data[airport],
            'live_weather': liveandforecast_weather_data[airport]["conditions"]
            # 'forecast_weather': liveandforecast_weather_data[airport]["forecasts"]
        }

    # Add edges (flight connections) with attributes
    for airport in airport_codes:
        for airport_in in airport_codes:
            if airport_in != airport:
                dat = delay_data[airport]["averageDelay"] + delay_data[airport_in]["averageDelay"]
                flight_time = calculate_flight_time(airport, airport_in)
                dat_res = "delay time" + str(dat) + "flight time" + str(flight_time * 60)
                graph['edges'][str(airport) + "-" + str(airport_in)] = dat_res
    return graph

def main():
    mapping = load_airport_station_mapping_graph()
    print("Welcome to SI507 final project")
    airports_input = input("Enter airports(at least two airports Example:LAX,SFO) ")
    airport_codes = airports_input.split(",")
    historical_weather_data = {}
    for item in airport_codes:
        historical_weather_data[item] = get_historical_weather_data(mapping[item])
    print("historical_weather_data:")
    print(historical_weather_data)
    flight_delay_data = get_flight_delay_data(airport_codes)
    print("flight_delay_data:")
    print(flight_delay_data)
    flight_weatherdata_andForecast = get_flight_weatherdata_andForecast(airport_codes)
    print("flight_weatherdata_andForecast:")
    print(flight_weatherdata_andForecast)
    graph = create_network_graph(flight_delay_data, historical_weather_data, flight_weatherdata_andForecast, airport_codes)
    draw_graph_show(graph, airport_codes)
    airports_input = input("Enter airports With flight time(at least two airports Example:LAX,SFO) ")
    airport_codes = airports_input.split(",")
    historical_weather_data = {}
    for item in airport_codes:
        historical_weather_data[item] = get_historical_weather_data(mapping[item])
    print("historical_weather_data:")
    print(historical_weather_data)
    flight_delay_data = get_flight_delay_data(airport_codes)
    print("flight_delay_data:")
    print(flight_delay_data)
    flight_weatherdata_andForecast = get_flight_weatherdata_andForecast(airport_codes)
    print("flight_weatherdata_andForecast:")
    print(flight_weatherdata_andForecast)
    graph_flighttime = analysis_flightTime_delay(flight_delay_data, historical_weather_data, flight_weatherdata_andForecast, airport_codes)
    draw_graph_show(graph_flighttime, airport_codes)
    return airport_codes




app = Flask(__name__)
# @app.route('/')
# def home():
#     return '<h1>Welcome!</h1>'


@app.route('/')
def index():
    return render_template('/index.html')

@app.route('/get_data', methods=['POST'])
def get_data():
    mapping = load_airport_station_mapping_graph()
    graph_filename = ""
    airport_code = request.form.get('airport_code')
    airport_codes = airport_code.split(",")
    print(airport_codes)
    historical_weather_data = {}
    for item in airport_codes:
        print(item)
        historical_weather_data[item] = get_historical_weather_data(mapping[item])
    flight_delay_data = get_flight_delay_data(airport_codes)
    flight_weatherdata_andForecast = get_flight_weatherdata_andForecast(airport_codes)
    print(flight_delay_data)
    if len(airport_codes) >1:
        graph = create_network_graph(flight_delay_data, historical_weather_data, flight_weatherdata_andForecast, airport_codes)
        graph_filename = draw_graph(graph, airport_codes)

    # Render the result as an HTML page
    template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Airport Weather and Delays</title>
</head>
<body>
    <h1>Airport Weather and Delays</h1>
    <p>Delay Data: {{ data }}</p>
    <p>flight_weather historical Data: {{ data1 }}</p>
    <p>flight_weather live Data: {{ data2 }}</p>
    <img src="{{ url_for('serve_graph_image', filename=graph_filename) }}" alt="Graph Image">
</body>
</html>
    """
    return render_template_string(template, data=flight_delay_data, data1=historical_weather_data, data2=flight_weatherdata_andForecast, graph_filename=graph_filename)


@app.route('/graph_image/<path:filename>')
def serve_graph_image(filename):
    return send_from_directory(os.path.join(app.root_path), filename)


if __name__ == '__main__':
    app.run(debug=True)
    # airport_codes = main()
    # update_cache_periodically(airport_codes)