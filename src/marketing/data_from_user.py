import requests
import logging
import os
import pandas as pd
from bson import ObjectId
from marketing import API_VERSION
from marketing import db_rc_pharmacies

current_directory = os.path.dirname(os.path.realpath(__file__))


def index_to_plan(index):
    if index == "1":
        return "DELIVERY"
    elif index == "2":
        return "FOOTFALL"
    elif index == "3":
        return "RESERVATION"


def get_radius_for_user(user_id, objective):
    url = f"{os.getenv('dashboard_backend_internal')}/pharmacyByOwner/{user_id}?&plans.list"
    response = (requests.get(url)).json()
    plans_list = isinstance(response["plans"], dict) and response["plans"]["list"] or []
    plans_list = [index_to_plan(i) for i in plans_list]
    url_delivery = f"https://{user_id}.themes.{os.getenv('BASE_URL_THEMES')}/api/orders/delivery/settings"
    response_delivery = (requests.get(url_delivery)).json()
    radius_delivery = response_delivery[0].get("value", 5)
    plans_radius = {
        "DELIVERY": radius_delivery,
        "FOOTFALL": 2,
        "RESERVATION": 15
    }
    available_plans_radius = {}

    for plan in plans_list:
        available_plans_radius[plan] = plans_radius[plan]

    objective_plans = {
        "MARCHIO": max(available_plans_radius.values()),
        "INTERAZIONI": max(available_plans_radius.values()),
        "VISUALIZZAZIONE MENU": max(available_plans_radius.values()),
        "DELIVERY": plans_radius["DELIVERY"],
        "PRENOTAZIONI": plans_radius["RESERVATION"],
        "VISITE AL LOCALE": plans_radius["FOOTFALL"],
        "RICERCA DI PERSONALE": max(available_plans_radius.values())
    }
    return objective_plans[objective]


def get_lat_long(user_id):
    try:
        user_id_data = db_rc_pharmacies[user_id]["restaurantdatas"].find_one()
        latitude_func = user_id_data.get("geometry", {}).get("location", {}).get("lat")
        longitude_func = user_id_data.get("geometry", {}).get("location", {}).get("lng")
        return latitude_func, longitude_func
    except Exception as geometry:
        logging.exception(f"Geometry data error : {geometry}")
        return None, None


def get_maximum_reach_number(user_id):
    df = pd.read_excel(current_directory + "/densità.xlsx")
    df.set_index("Nome", inplace=True)
    lat, long = get_lat_long(user_id)
    if lat is None or long is None:
        return 50e3
    url = f"https://maps.googleapis.com/maps/api/geocode/json?latlng={lat},{long}&key={os.getenv('google_key')}"
    try:
        response = (requests.get(url)).json()
        city_list = [i for r in response["results"] for i in r["address_components"]]
        city = ""
        for item in city_list:
            if "locality" in item["types"]:
                city = item["long_name"]
                break

        if not city:
            for item in city_list:
                if "administrative_area_level_3" in item["types"]:
                    city = item["long_name"]
                    break
        if city:
            return 25 * df.loc[city, "Densità abitativa"]
        else:
            return 50e3
    except Exception as googleGeoCodeError:
        logging.exception(f"Google Geocode Api Error : {googleGeoCodeError}")
        return 50e3


def get_ingredients_api(user_id):
    try:
        product_ingredients = list(db_rc_pharmacies[user_id]["products"].find({}))
        products = [ingredient for item in product_ingredients for ingredient in item["ingredients"] if
                    ingredient.strip()]
        products = [*set(products)]
        return products
    except Exception as ingredientsError:
        logging.exception(f"Error occurs querying ingredients : {ingredientsError}")
        return []


def get_menu_api(user_id):
    try:
        menu_items = list(db_rc_pharmacies[user_id]["products"].find({}))
        products = [item["title"] for item in menu_items if item["title"].strip()]
        return products
    except Exception as menuItems:
        logging.exception(f"Error occurs querying menu : {menuItems}")
        return []


def get_menu_items(user_id):
    menu_with_prices = []
    try:
        menu_items = list(db_rc_pharmacies[user_id]["products"].find({}))
        for item in menu_items:
            name = item["title"]
            price = item["price"]
            menu_item = f"{name}: {price}"
            menu_with_prices.append(menu_item)
    except Exception as menuItems:
        logging.exception(f"Error occurs querying menu : {menuItems}")
    return menu_with_prices


def get_restaurant_name(user_id):
    try:
        restaurant = db_rc_pharmacies["rc"]["pharmacies"].find_one({"pharmacyOwner": ObjectId(user_id)})
        restaurant_name = restaurant["name"]
        return restaurant_name

    except Exception as restaurantNameError:
        logging.exception(f"Error occurs querying restaurant name : {restaurantNameError}")
        restaurant_name = ""
        return restaurant_name


def get_address(user_id):
    try:
        user_address = db_rc_pharmacies[user_id]["restaurantdatas"].find_one({})
        address = user_address["formatted_address"]
        return address
    except Exception as addressError:
        logging.exception(f"Error occurs querying address : {addressError}")
        return None


def get_pixel(user_id):
    try:
        social_accounts = db_rc_pharmacies["rc"]["pharmacists"].find({"_id": ObjectId(user_id)})
        pixel_id = social_accounts["socialAccounts"].get("pixelId", "")
        if len(pixel_id) < 1:
            url = f"{os.getenv('dashboard_backend_internal')}/pharmacist/{user_id}?socialAccounts.pixelId"
            response = (requests.get(url)).json()
            pixel_id = response["socialAccounts"].get("pixelId", "")
        return pixel_id

    except Exception as pixeIdError:
        logging.exception(f"Error occurs querying socialAccounts pixelId : {pixeIdError}")
        pixel_id = ""
        return pixel_id


def get_social_accounts(user_id):
    try:
        social_accounts = (db_rc_pharmacies["rc"]["pharmacists"].find_one({"_id": ObjectId(user_id)}))["socialAccounts"]
        if social_accounts.get("instagramAccountResourceIdentifier") is None:
            social_accounts["instagramAccountResourceIdentifier"] = get_instagram_id(
                social_accounts["facebookPageResourceIdentifier"],
                social_accounts["facebookPageAuthToken"])
        return social_accounts
    except Exception as socialAccountsError:
        logging.exception(f"Error occurs querying socialAccounts : {socialAccountsError}")
        return {}


def get_social_reason(user_id):
    try:
        social_reason = \
        (db_rc_pharmacies["rc"]["pharmacists"].find_one({"_id": ObjectId(user_id)}))["billingInformation"][
            "socialReason"]
        return social_reason
    except Exception as socialReasonError:
        logging.exception(f"Error occurs querying socialReason : {socialReasonError}")
        return ""


def get_website(user_id):
    try:
        website = f"https://{(db_rc_pharmacies['rc']['pharmacies'].find_one({'pharmacyOwner': ObjectId(user_id)}))['domain']}"
        return website
    except Exception as websiteError:
        logging.exception(f"Error occurs querying website domain : {websiteError}")
        return ""


def get_instagram_id(page_id, page_token):
    url = f"https://graph.facebook.com/{API_VERSION}/{page_id}/instagram_accounts?access_token={page_token}"
    try:
        response = requests.get(url).json()
        return response["data"][0]["id"]
    except Exception as InstagramIdError:
        logging.exception(f"Error occurs sending request to graph api for InstagramId : {InstagramIdError}")
        return None
