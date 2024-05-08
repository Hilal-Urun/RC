from datetime import datetime, date
from marketing.add_copy.ad_copy_persona import generate_text
import pandas as pd

def age(birthday):
    birth_date = datetime.fromisoformat(birthday[:-1])
    today = date.today()
    age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
    return age

def generate_ad(product_data=None, restaurant_data=None, buyer_persona=None):
    # Generate a prompt for the ad
    prompt = f"create a creative and intriguing ad text for buyer which is {buyer_persona['age'].values[0]} years old, has {buyer_persona['dining_habits'].values[0]} dining habits," \
             f"interests are {buyer_persona['interests'].values[0]} and food preference is {buyer_persona['food_preferences'].values[0]}." \
             f"our restaurant name is {restaurant_data['name']}, {restaurant_data['name']} opening hours is {restaurant_data['Open hours']}, " \
             f"{restaurant_data['name']} instagram account is {restaurant_data['Instagram']},{restaurant_data['name']} address is {restaurant_data['address']} and have rating {restaurant_data['Ratings']}."
    if product_data is not None:
        prompt += f"Stand out our product with using product information that {product_data}"
    ad_text = generate_text(prompt)
    ad_text2 = generate_text(prompt, 300, 0.8)
    ad_text3 = generate_text(prompt, 300, 0.9)
    return [ad_text, ad_text2, ad_text3]


def generate_social_media_post(product_data=None, restaurant_data=None, buyer_persona=None):
    prompt = f"Create a relatable and engaging social media post text for our restaurant {restaurant_data['name']}. Following" \
             f"information can also be used: {restaurant_data['name']} address is {restaurant_data['address']}, instagram" \
             f"account is {restaurant_data['Instagram']}, user rating is {restaurant_data['Ratings']}, opening hours is {restaurant_data['Open hours']}." \
             f"Social media text would loved from buyer persona {buyer_persona} and should encourage sharing and " \
             f"tagging friends. "
    if product_data is not None:
        prompt = f"Create a relatable and engaging social media post text for our restaurant {restaurant_data['name']}. Following" \
                 f"information can also be used: {restaurant_data['name']} address is {restaurant_data['address']}, instagram" \
                 f"account is {restaurant_data['Instagram']}, user rating is {restaurant_data['Ratings']}, opening hours is {restaurant_data['Open hours']}." \
                 f"Social media text would loved from buyer persona {buyer_persona} and should encourage sharing and " \
                 f"tagging friends. Stand out our product {product_data}"
    post_text = generate_text(prompt)
    post_text2 = generate_text(prompt, 300, 0.8)
    post_text3 = generate_text(prompt, 400, 0.9)
    return [post_text, post_text2, post_text3]


def generate_newsletter(product_data=None, restaurant_data=None, customer_data=None, buyer_persona=None):
    prompt = f"Write a newsletter to our subscriber {customer_data}  who has {buyer_persona} persona to visit the restaurant or order online." \
             f"Highlight any updates or news about our restaurant {restaurant_data['name']} with using restaurant data {restaurant_data} and product data {product_data}"
    newsletter_text = generate_text(prompt,300)
    newsletter_text2 = generate_text(prompt, 400, 0.85)
    newsletter_text3 = generate_text(prompt, 400, 0.9)
    return [newsletter_text, newsletter_text2, newsletter_text3]
