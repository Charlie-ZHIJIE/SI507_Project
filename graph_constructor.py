#
# Name:Zhijie Xu
#
import os
import time
from datetime import datetime, timedelta
import json
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
            airport["delayed45"])) / int(airport["flights"])
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



# Function to load airport and station mapping from a JSON file
def load_airport_station_mapping():
    with open("airport_station_mapping.json", "r") as f:
        mapping = json.load(f)
    return mapping

def main():
    mapping = load_airport_station_mapping()
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
    print(graph)
    with open('graph.json', 'w') as json_file:
        json.dump(graph, json_file)




if __name__ == '__main__':

    main()
