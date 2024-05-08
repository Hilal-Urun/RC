import os
import requests, json
def outline(url, keys):
    response = requests.get(url)
    content = response.content
    json_content = json.loads(content)
    data = [{k: v for k, v in d.items() if
             k in keys} for d in
            json_content]
    return data

def get_products(id):
    prod_url = f"https://{id}.themes.{os.getenv('BASE_URL_THEMES')}/api/products"
    prod_list = ['_id', 'title', 'availableForDelivery', 'price', 'discounts', 'category', 'allergens']
    prod_information = outline(prod_url, prod_list)
    for item in prod_information:
        if item['_id'] == id:
            prod_info = item
    return prod_info

def get_customers(id):
    cus_url = f"https://{id}.themes.{os.getenv('BASE_URL_THEMES')}/api/customers"
    cus_list = ['_id', 'firstName', 'lastName', 'email', 'newsletterSubscribed', 'dateofbirth']
    customers_information = outline(cus_url, cus_list)
    for item in customers_information:
        if item['_id'] == id:
            customer_info = item
    return customer_info

def get_orders(id):
    order_url = f"https://{id}.themes.{os.getenv('BASE_URL_THEMES')}/api/orders"
    order_list = ['_id', 'isComplete', 'isDelivery', 'Products', 'customer']
    order_information = outline(order_url, order_list)
    for item in order_information:
        if item['_id'] == id:
            order_info = item
    return order_info

def restaurant_info(id):
    info_url = f"https://{id}.themes.{os.getenv('BASE_URL_THEMES')}/api/restaurant-info"
    info_list = ['_id', 'Name', 'Address', 'Opening hours', 'Rating', 'Menu', 'Delivery', 'Reservation', 'Instagram']
    restaurant_information = outline(info_url, info_list)
    for item in restaurant_information:
        if item['_id'] == id:
            restaurant_info = item
    return restaurant_info
