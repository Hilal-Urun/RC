import os
import requests
def get_restaurant_location(restaurant_id):
    url = f'https://{restaurant_id}.themes.{os.getenv("BASE_URL_THEMES")}/api/restaurant-info'
    response = requests.get(url)  # Send GET request to the URL
    data = response.json()  # Parse the response as JSON

    lat = data['geometry']['location']['lat']
    lon = data['geometry']['location']['lng']
    # Extract the restaurant information from the data
    address = [lat, lon]
    return address
def get_weather(restaurant_id):
    address = get_restaurant_location(restaurant_id)
    address = ', '.join(f"{value}" for value in address)
    url = "https://api.weatherapi.com/v1/forecast.json"
    params = {
        "key": 'API KEY FOR WEATHERAPI.COM',
        "q":  address,
        'days': 5
    }
    response = requests.get(url, params=params)

    if response.status_code == 200:

        data = response.json()
        result = {
            'Location': data['location']['name'],
            'Temperature': data['current']['temp_c'],
            'Condition': data['current']['condition']['text'],
            'Wind Speed': data['current']['wind_kph'],
            'Humidity': data['current']['humidity'],
            'Data Last Updated': data['current']['last_updated']
        }
        return result
    else:
        print("Failed to retrieve weather data. Status code:", response.status_code)
        return None
