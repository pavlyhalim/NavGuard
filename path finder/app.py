from flask import Flask, render_template, request
import folium
import osmnx as ox
import networkx as nx
import pandas as pd
from geopy.geocoders import Nominatim
from sklearn.cluster import KMeans

app = Flask(__name__)


G_loaded = ox.load_graphml(filepath="weighted_graph.graphml")


df3 = pd.read_csv('collision_clustered.csv')
df2 = pd.read_csv('construction_clustered.csv')
df1 = pd.read_csv('traffic_clustered.csv')



for u, v, data in G_loaded.edges(data=True):
    if 'weight' in data:
        data['weight'] = float(data['weight'])


def get_coordinates(address):
    try:
        geolocator = Nominatim(user_agent="YourAppName", timeout=10)
        location = geolocator.geocode(address)
        return (location.latitude, location.longitude) if location else (None, None)
    except Exception as e:
        print(f"Error occurred during geocoding: {e}")
        return None, None


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':

        start_location = request.form.get('start_location')
        end_location = request.form.get('end_location')

        print(f'Start Location: {start_location}')
        print(f'End Location: {end_location}')


        start_lat, start_lng = get_coordinates(start_location)
        end_lat, end_lng = get_coordinates(end_location)

        print(f'Start Location: {start_lat}')
        print(f'End Location: {end_lat}')


        source_node = ox.distance.nearest_nodes(G_loaded, start_lng, start_lat)
        target_node = ox.distance.nearest_nodes(G_loaded, end_lng, end_lat)
        optimal_route = nx.shortest_path(G_loaded, source=source_node, target=target_node, weight='weight')


        map_center = [(start_lat + end_lat) / 2, (start_lng + end_lng) / 2]
        

        mymap = folium.Map(location=map_center, zoom_start=10, tiles='CartoDB positron', control_scale=True)

        for edge in G_loaded.edges:
            start_node, end_node, _ = edge
            start_coord = (G_loaded.nodes[start_node]['y'], G_loaded.nodes[start_node]['x'])
            end_coord = (G_loaded.nodes[end_node]['y'], G_loaded.nodes[end_node]['x'])
            folium.PolyLine([start_coord, end_coord], color='gray', weight=1).add_to(mymap)
            

        optimal_route_coords = [(G_loaded.nodes[node]['y'], G_loaded.nodes[node]['x']) for node in optimal_route]
        folium.PolyLine(optimal_route_coords, color='red', weight=3).add_to(mymap)


        for index, row in df1.iterrows():
            folium.Marker([row['latitude'], row['longitude']], popup=f'Traffic Volume {row["Average_volume"]}', icon=folium.Icon(color='blue')).add_to(mymap)


        for index, row in df2.iterrows():
            folium.Marker([row['latitude'], row['longitude']], popup=f'Construction Award {row["award"]}', icon=folium.Icon(color='green')).add_to(mymap)


        for index, row in df3.iterrows():
            folium.Marker([row['latitude'], row['longitude']], popup=f'Total Collision Casuality{row["total_casualties"]}', icon=folium.Icon(color='red')).add_to(mymap)


        folium.Marker([start_lat, start_lng], popup='Start Location', icon=folium.Icon(color='black')).add_to(mymap)
        folium.Marker([end_lat, end_lng], popup='End Location', icon=folium.Icon(color='black')).add_to(mymap)


        map_path = 'templates/temp_map.html'
        mymap.save(map_path)

        return render_template("temp_map.html")

    return render_template('index.html')



if __name__ == '__main__':
    app.run(debug=True ,port=5002)




