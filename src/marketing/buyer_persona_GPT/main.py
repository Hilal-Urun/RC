import json
from marketing.shared import get_completion
from marketing.chatGPT_integration.main import gpt_respond
from marketing.data_from_user import get_restaurant_name, get_address
from marketing.data_from_user import get_menu_items
def sort_results(json_dict):
    prompt = f'''"check the following JSON string and rewrite it again with paying attention to fix any " \
             f"missing quotes or any mistakes found in it\n\n{json_dict}"'''
    return json.loads(get_completion(prompt, 0.2))
def gpt_buyer_persona(restaurant_id):
    prompt = f'For the following restaurant: {get_restaurant_name(restaurant_id)}, located in {get_address(restaurant_id)}, that offers' \
             f' the following menu:\n\n The Menu:\n[item_name:price in euro] \n\n {get_menu_items(restaurant_id)}\n\n' \
             'give me a buyer persona schema for a primary customer for this restaurant.\n' \
             "Return a JSON that has the following:\n" \
             "- Short description about the primary customer,\n" \
             "- An age range,\n" \
             '- Facebook interests\n\n' \
             'the JSON should be structured as follow:\n' \
             '{"simplified_buyer_persona": {"description":" ", "age_range": " ", "facebook_interests": " " }}\n\n' \
             'IMPORTANT: Keep the dictionary keys in English while your answer should be in Italian'
    return gpt_respond(prompt)

def visitatore(restaurant_id):
    prompt = f'Give me a descriptive buyer persona scheme for {get_restaurant_name(restaurant_id)} restaurant in {get_address(restaurant_id)} ' \
             f'with the following restaurant menu items and prices (item:price): \n\n {get_menu_items(restaurant_id)} \n\n' \

    prompt_final = prompt + f'Give me these information:\n' \
                            f'- Range Age.\n' \
                            f'- Gender.\n' \
                            f'- How much time they will go to restaurant per week.\n' \
                            f'- How much they spend in average at restaurant in euro.\n' \
                            f'- For how much people they reserve when they reserve to a restaurant.\n' \
                            f'- Which digital channels they use the most to find restaurants among Google, Facebook and Instagram.\n' \
                            f'- If they are sensible to discounts or not and which discount they are sensible the most.\n' \
                            f'- If they use more mobile or desktop or phone calling to reserve.\n' \
                            f'- If they prefer to do delivery or reserve to restaurant.\n' \
                            f'- How much time they will do delivery per week.\n' \
                            f'- Which is the average order for delivery.\n' \
                            f'- Which is their favorite day of the week to reserve and to order delivery.\n' \
                            f'- If they prefer launch or dinner to go to restaurant.\n' \
                            f'- If they prefer to have a romantic dinner, a casual one, a work launch or similar.\n' \
                            f'- Which are their favorite plates among the menu item i gave you in input most probably.\n\n' \
                            f'Just return JSON format. the JSON should be structured like:\n' \
                            '{"visitatore": {"age_range": "", "visits_per_week": "", "avg_spent_euro":"", ' \
                            '"avg_people_per_reservation":"", "digital_channel":"", "sensible_discount":"", ' \
                            '"device_to_reserve":"", "delivery_or_reservation":"", "avg_delivery_per_week":"",' \
                            '"avg_number_deliver_orders":"", "fav_day_week_reserve":"",' \
                            '"fav_day_week_reserve_delivery":"","lunch_or_dinner":"", "dinner_preferences":"" }}\n\n' \
                            'IMPORTANT: Keep the dictionary keys in English while your answer should be in Italian'
    return gpt_respond(prompt_final)
