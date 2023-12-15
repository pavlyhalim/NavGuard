import base64
from io import BytesIO
import pandas as pd
import matplotlib.pyplot as plt
from flask import Flask, jsonify, render_template
from wordcloud import WordCloud
from functions import (
    read_data,
    filter_traffic_data,
    filter_crash_data,
    aggregate_crash_data,
    create_geo_dataframes,
    plot_on_map_feature_groups,
    analyze_construction_data,
    analyze_collision_data,
    analyze_traffic_data,
)
import folium
from folium.plugins import FastMarkerCluster
from geopy.geocoders import Nominatim
import seaborn as sns
import geopandas as gpd
import matplotlib
matplotlib.use('Agg')


app = Flask(__name__)

collision_data = pd.read_csv("collisions.csv")
construction_data = pd.read_csv("constructions.csv")
traffic_data = pd.read_csv("traffic.csv")

collision_data = collision_data[collision_data['borough'] != '0']
construction_data = construction_data[construction_data['borough'] != '0']

construction_data['data_as_of'] = pd.to_datetime(construction_data['data_as_of'])
construction_data['data_as_of'] = construction_data['data_as_of'].apply(lambda d: d.replace(year=2023))

borough_boundaries_path = 'new-york-city-boroughs.geojson'
borough_boundaries = gpd.read_file(borough_boundaries_path)

traffic_geo = gpd.GeoDataFrame(traffic_data, geometry=gpd.points_from_xy(traffic_data['longitude'], traffic_data['latitude']))

traffic_geo_with_borough = gpd.sjoin(traffic_geo, borough_boundaries, op='within')

traffic_data['borough'] = traffic_geo_with_borough['name']


@app.route('/collisions-heatmap')
def collisions_heatmap():
    return render_template('collisions_heatmap.html')


@app.route('/cluster')
def cluster_page():
    return render_template('cluster.html')

@app.route('/construction-heatmap')
def construction_heatmap():
    return render_template('construction_heatmap.html')


@app.route("/")
def home():

    year = 2022
    filtered_traffic_data = filter_traffic_data(traffic_data, year)
    filtered_crash_data = filter_crash_data(collision_data, year)

    aggregated_crash_data = aggregate_crash_data(filtered_crash_data)

    traffic_gdf, construction_gdf, collision_gdf = create_geo_dataframes(
        filtered_traffic_data, construction_data, aggregated_crash_data
    )

    map_html = (
        plot_on_map_feature_groups(traffic_gdf, construction_gdf, collision_gdf)
        .get_root()
        .render()
    )

    proj_per_boro, proj_dist, award_boro = analyze_construction_data(construction_data)

    collision_boro, pie_chart = analyze_collision_data(collision_data)
    
    construction_types_by_borough_image = construction_types_by_borough().json['image']
    construction_starts_per_month_image = construction_starts_per_month().json['image']
    casualties_by_borough_image = casualties_by_borough().json['image']
    collision_wordcloud_image = collision_wordcloud().json['image']
    traffic_volume_heatmap_image = traffic_volume_heatmap().json['image']
    average_traffic_volume_image = average_traffic_volume().json['image']
    


    (heatmaps) = analyze_traffic_data(traffic_data)

    return render_template(
        "index.html",
        map_html=map_html,
        proj_per_boro=proj_per_boro,
        proj_dist=proj_dist,
        award_boro=award_boro,
        collision_boro=collision_boro,
        pie_chart=pie_chart,
        heatmap=heatmaps,
        construction_types_by_borough_image=construction_types_by_borough_image,
        construction_starts_per_month_image=construction_starts_per_month_image,
        casualties_by_borough_image=casualties_by_borough_image,
        collision_wordcloud_image=collision_wordcloud_image,
        traffic_volume_heatmap_image=traffic_volume_heatmap_image,
        average_traffic_volume_image=average_traffic_volume_image,
        
    )

def construction_types_by_borough():
    construction_type_counts = construction_data.groupby(['borough', 'consttype']).size().unstack()
    construction_type_counts.plot(kind='bar', stacked=True, figsize=(10, 10))
    plt.title('Number of Each Construction Type by Borough')
    plt.xlabel('Borough')
    plt.ylabel('Count')
    plt.xticks(rotation=45)
    plt.legend(title='Construction Type')

    return jsonify({"image": save_plot_to_base64()})


def construction_starts_per_month():
    construction_data['data_as_of'] = pd.to_datetime(construction_data['data_as_of'])
    construction_counts = construction_data['data_as_of'].dt.to_period('M').value_counts().sort_index()

    plt.figure(figsize=(12, 6))
    construction_counts.plot(kind='bar')
    plt.title('Construction Starts Per Month')
    plt.xlabel('Month')
    plt.ylabel('Count')
    plt.xticks(rotation=45)
    plt.tight_layout()

    return jsonify({"image": save_plot_to_base64()})


def casualties_by_borough():
    borough_casualties = collision_data.groupby('borough')['number_of_persons_killed'].sum()

    plt.figure(figsize=(8, 8))
    plt.pie(borough_casualties, labels=borough_casualties.index, autopct='%1.1f%%', startangle=140, colors=['lightcoral', 'lightskyblue', 'lightgreen', 'lightyellow', 'lightpink'])
    plt.title('Distribution of Casualties Due to Traffic Collision by Borough')

    return jsonify({"image": save_plot_to_base64()})


def collision_wordcloud():
    contributing_factors = collision_data['contributing_factor_vehicle_1'].str.cat(collision_data['contributing_factor_vehicle_2'], sep=', ')
    contributing_factors = contributing_factors.dropna()
    wordcloud = WordCloud(width=800, height=400, background_color='white').generate(' '.join(contributing_factors))

    plt.figure(figsize=(10, 5))
    plt.imshow(wordcloud, interpolation='bilinear')
    plt.title('Word Cloud of Contributing Factors in Collisions')
    plt.axis('off')

    return jsonify({"image": save_plot_to_base64()})


def traffic_volume_heatmap():
    traffic_data_copy = traffic_data.copy()
    traffic_data_copy['Date'] = pd.to_datetime(traffic_data_copy['Date'])
    traffic_data_copy['DayOfWeek'] = traffic_data_copy['Date'].dt.day_name()

    day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    traffic_data_copy['DayOfWeek'] = pd.Categorical(traffic_data_copy['DayOfWeek'], categories=day_order, ordered=True)
    traffic_data_copy.columns = traffic_data_copy.columns.str.strip()

    hour_rename = {
        '_12_00_1_00_am': '00:00', '_1_00_2_00am': '01:00', '_2_00_3_00am': '02:00',
        '_3_00_4_00am': '03:00', '_4_00_5_00am': '04:00', '_5_00_6_00am': '05:00',
        '_6_00_7_00am': '06:00', '_7_00_8_00am': '07:00', '_8_00_9_00am': '08:00',
        '_9_00_10_00am': '09:00', '_10_00_11_00am': '10:00', '_11_00_12_00pm': '11:00',
        '_12_00_1_00pm': '12:00', '_1_00_2_00pm': '13:00', '_2_00_3_00pm': '14:00',
        '_3_00_4_00pm': '15:00', '_4_00_5_00pm': '16:00', '_5_00_6_00pm': '17:00',
        '_6_00_7_00pm': '18:00', '_7_00_8_00pm': '19:00', '_8_00_9_00pm': '20:00',
        '_9_00_10_00pm': '21:00', '_10_00_11_00pm': '22:00', '_11_00_12_00am': '23:00'
    }
    traffic_data_copy.rename(columns=hour_rename, inplace=True)

    hour_columns = list(hour_rename.values())
    traffic_data_long = traffic_data_copy.melt(id_vars=['DayOfWeek', 'Date'], value_vars=hour_columns, var_name='Hour', value_name='TrafficVolume')
    pivot_table = traffic_data_long.pivot_table(index='DayOfWeek', columns='Hour', values='TrafficVolume', aggfunc='mean')

    plt.figure(figsize=(18, 5))
    sns.heatmap(pivot_table, cmap='Blues', annot=False)
    plt.title('Traffic Volume Heatmap by Hour and Day of Week')
    plt.ylabel('Day of Week')
    plt.xlabel('Hour of Day')
    plt.xticks(rotation=90)
    plt.yticks(rotation=0)
    plt.tight_layout()

    return jsonify({"image": save_plot_to_base64()})


def average_traffic_volume():
    hourly_columns = [
        '_12_00_1_00_am', '_1_00_2_00am', '_2_00_3_00am', '_3_00_4_00am',
        '_4_00_5_00am', '_5_00_6_00am', '_6_00_7_00am', '_7_00_8_00am',
        '_8_00_9_00am', '_9_00_10_00am', '_10_00_11_00am', '_11_00_12_00pm',
        '_12_00_1_00pm', '_1_00_2_00pm', '_2_00_3_00pm', '_3_00_4_00pm',
        '_4_00_5_00pm', '_5_00_6_00pm', '_6_00_7_00pm', '_7_00_8_00pm',
        '_8_00_9_00pm', '_9_00_10_00pm', '_10_00_11_00pm', '_11_00_12_00am'
    ]

    average_volume_per_hour = traffic_data[hourly_columns].mean()
    hour_labels = [f'{i}:00' for i in range(24)]
    average_volume_df = pd.DataFrame({'Hour': hour_labels, 'Average_volume': average_volume_per_hour.values})

    plt.figure(figsize=(10, 6))
    sns.barplot(x='Hour', y='Average_volume', data=average_volume_df)
    sns.lineplot(x='Hour', y='Average_volume', data=average_volume_df, sort=False)
    plt.title('Average Traffic Volume per Hour of Day')
    plt.xlabel('Hour of Day')
    plt.ylabel('Average Volume')
    plt.xticks(rotation=45, ha='right')

    return jsonify({"image": save_plot_to_base64()})

def average_volume_by_borough():
    collision_data = pd.read_csv("collisions.csv")
    construction_data = pd.read_csv("constructions.csv")
    traffic_data = pd.read_csv("traffic.csv")
    borough_volume = traffic_data.groupby('borough')['Average_volume'].mean().reset_index()

    plt.figure(figsize=(12, 6))
    sns.barplot(x='borough', y='Average_volume', data=borough_volume)
    plt.title('Average Traffic Volume by Borough')
    plt.xlabel('Borough')
    plt.ylabel('Average Volume')

    return jsonify({"image": save_plot_to_base64()})

def save_plot_to_base64():
    buf = BytesIO()
    plt.savefig(buf, format="png")
    buf.seek(0)
    plot_url = base64.b64encode(buf.read()).decode('utf-8')
    buf.close()
    plt.clf()
    return plot_url



if __name__ == '__main__':
    app.run(debug=True, port=5001)

