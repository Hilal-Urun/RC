## Weather API for Restaurants Club Platform

This Python script defines two functions for retrieving information about a restaurant and its corresponding weather.

### Functions:

#### `get_restaurant_locatiok`:

The `get_restaurant_location` function takes a `restaurant_id` parameter and retrieves location of the corrisponding restaurant from the ID.

#### `get_weather`:

The `get_weather` function takes a `restaurant_id` parameter and uses the `get_restaurant_location` function to retrieve the latitude and longitude of the restaurant. It then calls the WeatherAPI to retrieve weather data for that location, using the latitude and longitude as the address. The function then processes the weather data and returns a dictionary containing various weather information, such as location, temperature, wind speed, humidity, and condition.
