# SI507_Project
Here is Start point for Si 507 Final Project

#Airport Network Graph Data Structure
This repository contains a data structure to represent airports and flight connections as a network graph. It allows users to analyze the relationship between weather conditions and flight delays, as well as find the most efficient routes for purchasing airline tickets.

#Components
The data structure consists of the following components:

Vertices (Nodes): Airports
Edges: Flight connections, weighted by average delay time
Vertices Attributes: Weather conditions (historical or live, depending on user preference)

#Files
graph_constructor.py: Python script to construct the network graph from the stored data using classes.
graph.json: JSON file to store the graph structure for use in the application.
final_si507.py: main function
airport_station_mapping.json: json file saved the data for mapping airport to station
graph.png:the graph file
./templeate: html file for Flask
./cache: cache file for data


#Visualization
The graph is visualized using the Plotly library, allowing users to interactively explore the data and better understand the relationships between airports, flight connections, and weather conditions.



#Usage
#Clone the repository:
git clone https://github.com/Charlie-ZHIJIE/SI507_Project
cd SI507_Project
#Install the required dependencies:
pip install -r os, time, datetime, json, flask, mplcursors, requests, network, matplotlib, diskcache
#Run the graph_constructor.py script to generate the graph.json file:
python graph_constructor.py
#Run Main function 
You have two choice, one is command line interface with poltly, another is flask with poltly
for choice one
you need comments flask like 
    # app.run(debug=True)
    airport_codes = main()
    update_cache_periodically(airport_codes)
for choice two
you need comments command line interface like 
    app.run(debug=True)
    # airport_codes = main()
    # update_cache_periodically(airport_codes)    
python final_si507.py

#Flask Web Application
run the function
open http://127.0.0.1:5000 in browther
enter airport code you want(example:LAX,SFO,SJC)

#Command-Line Interface
The command-line interface provides a simple way for users to view airport information, flight delay times, and weather conditions from the terminal by running the Python script.
Run main function
Terminal:"Welcome to SI507 final project
Enter airports(at least two airports Example:LAX,SFO) "
Enter: LAX,SFO
Terminal will print data including historical_weather_data, flight_delay_data and flight_weatherdata_andForecast

#Interactive Network Graph (Plotly)
The Plotly network graph displays weather and flight delay relationships in an interactive way, allowing users to zoom in and explore the correlations between weather and flight delays.
graph.png

Contributing
We welcome contributions to improve the data structure and its functionalities. Please submit a pull request or open an issue to discuss your ideas.

License
This project is licensed under the MIT License.