import os

import openai
import pandas as pd
import requests
import json
import facebook
import googlemaps


# # # THE MAIN FUNCTION TO BE USED TO MAKE EVERYTHING DONE USING ChatGPT # # #
def gpt_respond(prompt):
    try:
        # Creating the description based on the keywords entered
        openai.api_key = os.getenv("OPENAI_API_KEY")
        model_engine = "text-davinci-003"
        completions = openai.Completion.create(engine=model_engine, prompt=prompt, max_tokens=1024, n=1, stop=None,
                                               temperature=0.5)
        result = completions.choices[0].text

        return result

    except openai.OpenAIError as e:
        print(e)


# # # COMMON FUNCTIONS # # #


def get_restaurant_info(restaurant_id):
    url = f'https://{restaurant_id}.themes.{os.getenv("BASE_URL_THEMES")}/api/restaurant-info'
    response = requests.get(url)  # Send GET request to the URL
    data = response.json()  # Parse the response as JSON

    # Extract the restaurant information from the data
    restaurant_info = {
        'restaurant_name': data.get('name', 'N/A'),
        'restaurant_address': data.get('formatted_address', 'N/A'),
        'phone_number': data.get('formatted_phone_number', 'N/A')
    }

    # Getting the opening hours of the restaurant
    open_hours = data.get('opening_hours', {}).get('weekday_text', [])
    if not open_hours:
        open_hours = ['N/A']
    restaurant_info['opening_hours'] = open_hours
    return restaurant_info


def get_menu_items(restaurant_id):
    """
    Retrieve menu items from the restaurant's API and return as a list of formatted strings.

    Args:
        restaurant_id (str): The ID of the restaurant to fetch menu items from.

    Returns:
        list: A list of formatted strings, where each string represents a menu item with its name and price.
    """

    url = f'https://{restaurant_id}.themes.{os.getenv("BASE_URL_THEMES")}/api/products'
    request = requests.get(url)
    data = request.json()

    menu_items = []

    for item in data:
        name = item["title"]
        price = item["price"]
        menu_item = f"{name}: {price}"
        menu_items.append(menu_item)

    return menu_items


def get_fb_interests_names(restaurant_id):
    try:
        url = f'url to the endpoint of the buyer persona using {restaurant_id}'
        request = requests.get(url)
        data = request.json()

        # Accessing the 'primary_buyer_persona' dictionary
        primary_buyer_persona = data['buyerpersonas']['primary_buyer_persona']

        # Accessing the 'facebook_interests' list
        facebook_interests = primary_buyer_persona['facebook_interests']

        # Creating a list to store the names of items
        interests_names = []

        # Adding the names of items to the list
        for item in facebook_interests:
            interests_names.append(item['name_facebook_interest'])

        return interests_names

    except requests.RequestException as e:
        print(e)


def retrieve_order_history(restaurant_id):
    """
    Retrieves the orders history DataFrame of a given Restaurant ID from the API endpoint.

    Args:
    restaurant_id: str - The ID of the restaurant to retrieve orders history for.

    Returns:
    Orders - A list of dictionaries representing the order details for the restaurant.
    Each dictionary contains the following keys: 'order_id', 'order_date', 'order_name',
    'customer_name', 'order_items', and 'order_total_price', each with a corresponding string value.
    """

    url = f'https://{restaurant_id}.themes.{os.getenv("BASE_URL_THEMES")}/api/orders'
    request = requests.get(url)
    data = request.json()

    orders = []

    for order in data['data']:
        order_info = {
            'order_id': order['_id'],
            'order_date': order['createdAt'],
            'order_name': order['name'],
            'customer_name': order['customer']['email'],
            'order_items': order['products'][0]["additionalData"]["variation"]["name"],
            'order_total_price': order['totalPrice']
        }
        orders.append(order_info)

    return orders


def get_order_info(order_list, order_id):
    """
       Given a list of order dictionaries and an order ID, returns the order dictionary that matches the order ID.

       Args:
       order_list: A list of order dictionaries, where each dictionary contains
       the following keys: 'order_id', 'order_date', 'order_name', 'customer_name', 'order_items', and 'order_total_price',
       each with a corresponding string or float value.
       order_id: The order ID to retrieve the order dictionary for.

       Returns:
       Order - The order dictionary that matches the order ID if found, or None if not found.
       The order dictionary contains the same keys and value types as the input order dictionaries.
       """

    for order in order_list:
        if order['order_id'] == order_id:
            return order
    return None


# # # TUTORIAL RELATED FUNCTIONS # # #
# It would be in a different script, since it needs more data and it's more complicated

# # # MENU RELATED FUNCTIONS # # #

def product_description(food_item):
    """
    Generate a food item description based on the new entered item and optional keywords.

    Args:
        food_item (str): The name of the food item for which to generate a description.

    Returns:
        str: The generated description for the food item.
    """

    # To generate prompt for a food product description
    keywords = input('Is there anything you want to mention in the description? (write no if no need) ')

    if keywords.lower() == 'no':
        prompt = f'Write me a description about the following food item: \n\n {food_item}'
        # print(prompt)
    else:
        prompt = f'Write me a description about the following food item:\n {food_item} ' \
                 f'\n\nkeep in mind to mention the following keywords in the description: \n {keywords}'

    return gpt_respond(prompt)


# # # DELIVERY RELATED FUNCTIONS # # #

def analyze_order_history(restaurant_id, goal):
    """
        Analyze the order history of a given restaurant ID and provide insights based on the specified goal.

        Args:
            restaurant_id (any): Where we can retrieve the order history dataset to be analyzed.
            goal (str): The goal of the analysis, e.g. "Perform a sales comparison between the last 6 months".

        Returns:
            str: The analysis and insights generated based on the order history and goal.
        """

    order_history = retrieve_order_history(restaurant_id)

    if goal:
        prompt = f'Analyze the following dataset and give me some useful information that could be extracted ' \
                 f'from it: \n\n {order_history}' \
                 f'\n\n Also, keep in mind to analyze the dataset according to the following goal:\n\n {goal}'
    else:
        prompt = f'Analyze the following dataset and give me some useful information that could be extracted ' \
                 f'from this dataset: \n\n {order_history}'

    return gpt_respond(prompt)


def leave_a_review(restaurant_id, order_number):
    """
    Generate a custom email or message to encourage a customer to leave a review for a completed food order.

    Args:
        restaurant_id (any): The ID of the restaurant for which the review is being requested.
        order_number (any): The order number of the completed food order.

    Returns:
        str: The custom email or message generated with the request for a review.
    """

    restaurant_name = get_restaurant_info(restaurant_id)['restaurant_name']
    restaurant_address = get_restaurant_info(restaurant_id)['restaurant_address']

    review_link = f'https://www.google.com/maps/search/?api=1&query={restaurant_name}%2C+{restaurant_address}'
    review_link = review_link.replace(' ', '+').replace(',', '')
    order_data = retrieve_order_history(restaurant_id)
    customer_name = get_order_info(order_data, order_number)['order_name']
    order_items = get_order_info(order_data, order_number)['order_items']

    prompt = f'Write me a simple short message to encourage a customer to leave a review about a food order he' \
             f' ordered? followed by a catchy ending, then {restaurant_name}.\n\n' \
             'The following must be in the message:\n' \
             f'- Name of customer: {customer_name}\n' \
             f'- Link to leave the review: {review_link}\n' \
             f'- Order number & order items: {order_number}, {order_items}\n' \
             f'- Restaurant name: {restaurant_name}'

    return gpt_respond(prompt)


# # # MARKETING RELATED FUNCTIONS # # #

def ads_creation():
    """
    Generate an ad content based on keywords entered by the user.

    Returns:
        str: The generated ad content based on the entered keywords.
    """

    ad = input('Please tell me what is the ad is about? ')
    prompt = (f'Write me an ad content based on the following keywords: \n\n {ad} '
              f'\n\n Please also make sure to generate a good traffic keywords')

    return gpt_respond(prompt)


def buyer_persona(restaurant_id):
    """
        Generate a descriptive buyer persona scheme for a given restaurant ID.

        Args:
            restaurant_id (any): The ID of the restaurant.

        Returns:
            str: The generated buyer persona scheme based on the restaurant's menu items, Facebook interests, and other
                 information.
    """

    restaurant_name = get_restaurant_info(restaurant_id)['restaurant_name']
    restaurant_address = get_restaurant_info(restaurant_id)['restaurant_address']

    restaurant_menu = get_menu_items(restaurant_id)

    facebook_interests = get_fb_interests_names(restaurant_id)

    prompt = f'Give me a descriptive buyer persona scheme for {restaurant_name} restaurant in {restaurant_address} ' \
             f'with the following restaurant menu items and prices (item:price): \n\n {restaurant_menu} \n\n' \
             f'And with the following Facebook interests: \n\n {facebook_interests} \n\n'

    prompt_final = prompt + f'Give me these information:\n' \
                            f'- Range Age.\n' \
                            f'- Gender.\n' \
                            f'- How much time they will go to restaurant per week.\n' \
                            f'- How much they spend in average at restaurant.\n' \
                            f'- For how much people they reserve when they reserve to a restaurant.\n' \
                            f'- Which digital channels they use the most to find restaurants.\n' \
                            f'- If they are sensible to discounts or not and which discount they are sensible the most.\n' \
                            f'- If they use more mobile or desktop or phone calling to reserve.\n' \
                            f'- If they prefer to do delivery or reserve to restaurant.\n' \
                            f'- How much time they will do delivery per week.\n' \
                            f'- Which is the average order for delivery.\n' \
                            f'- Which is their favorite day of the week to reserve and to order delivery.\n' \
                            f'- If they prefer launch or dinner to go to restaurant.\n' \
                            f'- If they prefer to have a romantic dinner, a casual one, a work launch or similar.\n'

    return gpt_respond(prompt_final)


# # # SOCIAL MEDIA RELATED FUNCTIONS # # #

def top_posts(page_id, access_token):
    """
    Gets the top 5 most successful Facebook posts then it creates a new post based on those successful ones.

    Args:
    page_id: str - The ID of the Facebook page to retrieve top posts for.
    access_token: str - The access token for the Facebook Graph API.

    Returns:
    str - If successful, returns a string representing a post that's generated based on the top 5 most successful
    Facebook posts. If unsuccessful, returns None.
    """
    # Initialize the Graph API with the access token
    graph = facebook.GraphAPI(access_token)

    try:
        # Retrieve the posts data using the Graph API
        posts = graph.get_object(f'/{page_id}/posts?fields=id,likes.summary(total_count),comments.summary'
                                 f'(total_count),shares.count,reach,impressions')

        # Create a list to store post metrics
        post_metrics = []

        # Loop through each post and extract the metrics
        for post in posts['data']:
            post_id = post['id']
            likes = post['likes']['summary']['total_count']
            comments = post['comments']['summary']['total_count']
            shares = post['shares']['count']
            reach = post['reach']
            impressions = post['impressions']
            engagement_rate = (likes + comments + shares) / reach  # Custom success metric

            # Append the post metrics to the list
            post_metrics.append({
                'post_id': post_id,
                'engagement_rate': engagement_rate
            })

        # Sort the posts based on the custom success metric in descending order
        sorted_posts = sorted(post_metrics, key=lambda x: x['engagement_rate'], reverse=True)

        # Create a list to store the top 5 most successful posts
        top_posts = []

        # Append the top 5 most successful posts to the list
        for i in range(min(5, len(sorted_posts))):
            post = sorted_posts[i]
            top_posts.append(post)

        prompt = f'Based on the following posts that has higher engagement, write me only one post. ' \
                 f'You may include emojis: \n\n{top_posts}'

        # Return the post that's generated based on the top posts
        return gpt_respond(prompt)

    except facebook.GraphAPIError as e:
        print('Error occurred:', e)
        return None


def post_creation():
    """ FB post contents generation based on keywords entered by the user """

    post = input('please describe the post you would like to have? ')
    prompt = f'Write me a social media post about/including the following. You may use emojis: \n\n{post}'

    return gpt_respond(prompt)


# Facebook comments reply
def comment_reply(page_id, access_token):
    """
    Facebook comments reply that connect to a Facebook page and checks the comments to reply on them

    page_id: The ID of the Facebook page to which the comments belong.
    access_token: The access token required to connect to the Facebook API.
    """

    # Generate Facebook API Access
    graph = facebook.GraphAPI(access_token)

    # TO retrieve the posts of the page
    posts = graph.get_connections(page_id, 'posts')

    # loop through the posts and check if they have any comments
    while True:
        try:
            for post in posts['data']:
                post_id = post['id']
                comments = graph.get_connections(post_id, 'comments')
                has_comments = True if len(comments['data']) > 0 else False

                # loop through the comments on the current post
                for comment in comments['data']:
                    comment_id = comment['id']
                    replies = graph.get_connections(comment_id, 'comments')
                    replied = False

                    # check if you've replied to the current comment
                    for reply in replies['data']:
                        if reply['from']['name'] == "Your Name":
                            replied = True
                            break

                    # generate a reply if you haven't replied to the current comment
                    if not replied:
                        prompt = f'Give me a friendly respond based on the following social media comment: \n\n {comment}'
                        reply_text = gpt_respond(prompt)
                        graph.put_comment(comment_id, reply_text)
                        print(f"Replied to comment {comment_id} on post {post_id} with message: {reply_text}")

            posts = graph.get_connections(page_id, 'posts', after=posts['paging']['cursors']['after'])
        except KeyError:
            # When there are no more pages (i.e., no more 'after'), break out of the loop
            break


# # # EXTRA FUNCTIONS # # #
def restaurants_comparison(restaurant_name, restaurant_address, location, restaurant_type):
    """ Analysis between nearby restaurants (Restaurant Comparison), to have a brief insight on the surrounding """

    api_key = os.getenv("google_key")
    location = location
    radius = "1000"
    type = "restaurants"

    url = f"https://maps.googleapis.com/maps/api/place/nearbysearch/json?location" \
          f"={location}&radius={radius}&keyword={restaurant_type}&type={type}&key={api_key}"

    response = requests.get(url)
    data = json.loads(response.text)
    # print(data)

    restaurants_list = []
    for place in data["results"]:
        # print(place["name"])
        place_id = place["place_id"]
        place_url = f"https://maps.googleapis.com/maps/api/place/details/json?place_id={place_id}&key={api_key}"
        place_response = requests.get(place_url)
        place_data = json.loads(place_response.text)
        # print(place_data)
        restaurants_list.append({"name": place["name"], "address": place["vicinity"]})

    df = pd.DataFrame(restaurants_list)
    df = df.head(5)
    df5 = [f"{row['name']}: {row['address']}" for i, row in df.iterrows()]
    df5_string = '\n'.join(df5)
    prompt = (f'Can you give me a detailed comparison between the following restaurants '
              f'based on available online sources:  \n {df5_string} '
              f'\n\nThen compare it to my restaurant and suggest modifications to have a good customers experience:\n '
              f'{restaurant_name}: {restaurant_address}')

    return gpt_respond(prompt)


def analyze_reviews(restaurant_id):
    """ Analyze reviews and suggest steps to follow to improve the customer experience """

    api_key = os.getenv("google_key")
    gmaps = googlemaps.Client(key=api_key)

    # Retrieve the reviews using Google Places API by specify the place ID of the restaurant
    fields = ['reviews']
    place = gmaps.place(restaurant_id, fields=fields)

    # Extract the reviews from the place result
    reviews = place['result']['reviews']

    reviews_list = []

    # Loop through each review and print the text and rating
    for review in reviews:
        reviews_list.append(review['text'])

    prompt = f'Analyze the following reviews and propose steps should be followed to improve the customer experience:' \
             f'\n\n {reviews_list}'

    return gpt_respond(prompt)

