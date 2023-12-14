# Import necessary libraries
import pandas as pd
import matplotlib.pyplot as plt
from io import BytesIO
import base64
import folium
from folium.plugins import FastMarkerCluster
from geopy.geocoders import Nominatim
import seaborn as sns
import geopandas as gpd


# Function to read data from CSV files
def read_data():
    collision_data = pd.read_csv("collisions.csv")
    construction_data = pd.read_csv("constructions.csv")
    traffic_data = pd.read_csv("traffic.csv")
    return collision_data, construction_data, traffic_data


# Function to filter traffic data for a specific year
def filter_traffic_data(traffic_data, year):
    traffic_data["Date"] = pd.to_datetime(traffic_data["Date"])
    filtered_data = traffic_data[traffic_data["Date"].dt.year == year]
    return filtered_data


# Function to filter crash data for a specific year
def filter_crash_data(collision_data, year):
    collision_data["crash_date"] = pd.to_datetime(collision_data["crash_date"])
    filtered_crash_data = collision_data[collision_data["crash_date"].dt.year == year]
    return filtered_crash_data


# Function to aggregate crash data by location
def aggregate_crash_data(filtered_crash_data):
    time_columns = filtered_crash_data.columns[7:31]
    filtered_crash_data["Average_volume"] = (
        filtered_crash_data[time_columns].sum(axis=1) / 24
    )
    aggregated_df = (
        filtered_crash_data.groupby(["borough", "latitude", "longitude"])
        .agg(
            {
                "number_of_persons_injured": "mean",
                "number_of_persons_killed": "mean",
                "number_of_cyclist_injured": "mean",
                "number_of_cyclist_killed": "mean",
                "number_of_motorist_injured": "mean",
                "number_of_motorist_killed": "mean",
            }
        )
        .reset_index()
    )
    aggregated_df["total_casualties"] = aggregated_df[
        [
            "number_of_persons_injured",
            "number_of_persons_killed",
            "number_of_cyclist_injured",
            "number_of_cyclist_killed",
            "number_of_motorist_injured",
            "number_of_motorist_killed",
        ]
    ].sum(axis=1)
    return aggregated_df[["borough", "latitude", "longitude", "total_casualties"]]


# Function to create GeoDataFrames for traffic, construction, and collision data
def create_geo_dataframes(df1, df2, df3):
    traffic_gdf = gpd.GeoDataFrame(
        df1, geometry=gpd.points_from_xy(df1["longitude"], df1["latitude"])
    )
    construction_gdf = gpd.GeoDataFrame(
        df2, geometry=gpd.points_from_xy(df2["longitude"], df2["latitude"])
    )
    collision_gdf = gpd.GeoDataFrame(
        df3, geometry=gpd.points_from_xy(df3["longitude"], df3["latitude"])
    )
    return traffic_gdf, construction_gdf, collision_gdf


# Function to visualize data on a map using Folium
def plot_on_map(data1, data2, data3, sample_size=None):
    data1 = data1.dropna(subset=["longitude", "latitude"])
    data2 = data2.dropna(subset=["longitude", "latitude"])
    data3 = data3.dropna(subset=["longitude", "latitude"])

    m = folium.Map(location=[40.7128, -74.0060], tiles="Stamen Terrain", zoom_start=12)

    collisions_cluster = FastMarkerCluster([], name="Vehicle Collisions").add_to(m)
    construction_cluster = FastMarkerCluster([], name="Construction Projects").add_to(m)
    traffic_cluster = FastMarkerCluster([], name="Traffic Projects").add_to(m)

    def add_marker_to_cluster(row, cluster, color):
        folium.CircleMarker(
            location=[row["latitude"], row["longitude"]],
            radius=5,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.6,
        ).add_to(cluster)

    if sample_size:
        data1 = data1.sample(n=min(sample_size, len(data1)))
        data2 = data2.sample(n=min(sample_size, len(data2)))
        data3 = data3.sample(n=min(sample_size, len(data3)))

    data1.apply(
        lambda row: add_marker_to_cluster(row, collisions_cluster, "red"), axis=1
    )
    data2.apply(
        lambda row: add_marker_to_cluster(row, construction_cluster, "blue"), axis=1
    )
    data3.apply(
        lambda row: add_marker_to_cluster(row, traffic_cluster, "green"), axis=1
    )

    folium.LayerControl().add_to(m)
    return m


# Function to check if a street is in the crash data
def is_street_in_crash_data(street_name, collision_data):
    on_street_mask = collision_data["on_street_name"].str.contains(
        street_name, case=False, na=False
    )
    off_street_mask = collision_data["off_street_name"].str.contains(
        street_name, case=False, na=False
    )
    return any(on_street_mask | off_street_mask)


# Function to get coordinates from an address using Geopy
def get_coordinates(address):
    geolocator = Nominatim(user_agent="YourAppName")
    location = geolocator.geocode(address)

    if location:
        return location.latitude, location.longitude
    else:
        return None, None


# Function to visualize data on a map using Folium with feature groups
# Function to visualize data on a map using Folium with feature groups
def plot_on_map_feature_groups(data1, data2, data3):
    data1 = data1.dropna(subset=["longitude", "latitude"])
    data2 = data2.dropna(subset=["longitude", "latitude"])
    data3 = data3.dropna(subset=["longitude", "latitude"])

    m = folium.Map(location=[40.7128, -74.0060], tiles="OpenStreetMap", zoom_start=12)

    collisions_group = folium.FeatureGroup(name="Vehicle Collisions")
    construction_group = folium.FeatureGroup(name="Construction Projects")
    traffic_group = folium.FeatureGroup(name="Traffic Projects")

    for _, row in data1.iterrows():
        folium.CircleMarker(
            location=[row["latitude"], row["longitude"]],
            radius=5,
            color="red",
            fill=True,
            fill_color="red",
            fill_opacity=0.6,
        ).add_to(collisions_group)

    for _, row in data2.iterrows():
        folium.CircleMarker(
            location=[row["latitude"], row["longitude"]],
            radius=5,
            color="blue",
            fill=True,
            fill_color="blue",
            fill_opacity=0.6,
        ).add_to(construction_group)

    for _, row in data3.iterrows():
        folium.CircleMarker(
            location=[row["latitude"], row["longitude"]],
            radius=5,
            color="green",
            fill=True,
            fill_color="green",
            fill_opacity=0.6,
        ).add_to(traffic_group)

    collisions_group.add_to(m)
    construction_group.add_to(m)
    traffic_group.add_to(m)

    folium.LayerControl().add_to(m)
    return m


# Function to analyze construction data and generate visualizations
def analyze_construction_data(construction_data):
    # Plot a bar chart of the number of projects per borough
    borough_counts = construction_data["boro"].value_counts()
    fig, ax = plt.subplots()
    borough_counts.plot(kind="bar", rot=45, color="skyblue", ax=ax)
    ax.set_title("Number of Projects per Borough")
    ax.set_xlabel("Borough")
    ax.set_ylabel("Number of Projects")

    buf = BytesIO()
    fig.savefig(buf, format="png")
    proj_per_boro = base64.b64encode(buf.getbuffer()).decode("ascii")

    # Distribution of project types
    project_type_counts = construction_data["consttype"].value_counts()
    fig1, ax1 = plt.subplots()
    ax1.pie(
        project_type_counts,
        labels=project_type_counts.index,
        autopct="%1.1f%%",
        startangle=90,
    )
    ax1.axis("equal")  # Equal aspect ratio ensures that pie is drawn as a circle.
    plt.title("Distribution of Project Types")

    buf = BytesIO()
    fig.savefig(buf, format="png")
    proj_dist = base64.b64encode(buf.getbuffer()).decode("ascii")

    # Average award amount by borough
    avg_award_by_borough = construction_data.groupby("boro")["award"].mean()
    normalized_avg_award = avg_award_by_borough / avg_award_by_borough.sum()
    fig2, ax2 = plt.subplots()
    normalized_avg_award.plot(kind="bar", color="skyblue")
    plt.title("Normalized Average Award Amount by Borough")
    plt.xlabel("Borough")
    plt.ylabel("Normalized Average Award Amount")

    buf = BytesIO()
    fig.savefig(buf, format="png")
    award_boro = base64.b64encode(buf.getbuffer()).decode("ascii")

    return proj_per_boro, proj_dist, award_boro


# Function to analyze collision data and generate visualizations
# Function to analyze collision data and generate visualizations
def analyze_collision_data(collision_data):
    collision_data["borough"].fillna("Unknown", inplace=True)
    borough_collisions = collision_data["borough"].value_counts()

    # Calculate total casualties by summing injury and death columns
    collision_data["total_casualties"] = (
        collision_data["number_of_persons_injured"]
        + collision_data["number_of_persons_killed"]
        + collision_data["number_of_pedestrians_injured"]
        + collision_data["number_of_pedestrians_killed"]
        + collision_data["number_of_cyclist_injured"]
        + collision_data["number_of_cyclist_killed"]
        + collision_data["number_of_motorist_injured"]
        + collision_data["number_of_motorist_killed"]
    )

    # Plot bar chart for the number of collisions per borough
    fig, ax = plt.subplots()
    plt.bar(borough_collisions.index, borough_collisions.values, color="blue")
    plt.title("Number of Collisions per Borough in New York")
    plt.xlabel("Borough")
    plt.ylabel("Number of Collisions")

    buf = BytesIO()
    fig.savefig(buf, format="png")
    collision_boro = base64.b64encode(buf.getbuffer()).decode("ascii")

    # Plot pie chart for the distribution of casualties by borough
    borough_casualties = (
        collision_data.groupby("borough")["total_casualties"].sum().reset_index()
    )
    fig3, ax3 = plt.subplots()
    plt.pie(
        borough_casualties["total_casualties"],
        labels=borough_casualties["borough"],
        autopct="%1.1f%%",
        startangle=140,
        colors=["lightcoral", "lightskyblue", "lightgreen", "lightyellow", "lightpink"],
    )
    plt.title("Distribution of Casualties by Borough")

    buf = BytesIO()
    fig3.savefig(buf, format="png")
    pie_chart = base64.b64encode(buf.getbuffer()).decode("ascii")

    return collision_boro, pie_chart


# Function to analyze traffic data and generate visualizations
def analyze_traffic_data(traffic_data):
    time_columns = traffic_data.columns[7:31]
    traffic_data["Average_volume"] = traffic_data[time_columns].sum(axis=1) / 24
    df1 = (
        traffic_data.groupby(
            ["latitude", "longitude", "Roadway_Name", "Direction", "From_St", "To_St"]
        )
        .agg({"Average_volume": "mean"})
        .reset_index()
    )
    traffic_data["hh"] = traffic_data["Date"].dt.hour
    traffic_data["mm"] = traffic_data["Date"].dt.minute

    # Format the date and time
    traffic_data["datetime_str"] = traffic_data["Date"].dt.strftime("%Y-%m-%d %H:%M")

    # Now convert this string into a datetime object
    traffic_data["datetime"] = pd.to_datetime(
        traffic_data["datetime_str"], format="%Y-%m-%d %H:%M"
    )

    traffic_data["day_of_week"] = traffic_data["datetime"].dt.day_name()

    # Ensure 'Average_volume' is the correct column name
    pivot_table = traffic_data.pivot_table(
        values="Average_volume",  # Replace with the actual column name
        index="day_of_week",
        columns=traffic_data["datetime"].dt.hour,
        aggfunc="mean",
    )

    plt.figure(figsize=(15, 7))
    sns.heatmap(pivot_table, cmap="YlGnBu")
    plt.title("Heatmap of Average Traffic Volume by Day and Hour")
    plt.xlabel("Hour of the Day")
    plt.ylabel("Day of the Week")

    buf = BytesIO()
    plt.savefig(buf, format="png")
    heatmap = base64.b64encode(buf.getvalue()).decode("ascii")

    # Bar chart for traffic volume by borough
    # Bar chart for traffic volume by borough

    # Line chart for traffic volume trends over time

    return heatmap
