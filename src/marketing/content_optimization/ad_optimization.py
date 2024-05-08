import os
from marketing.utils import bp_to_prompt, goal_to_prompt, get_json_response
from marketing.data_access.rc.rc_pharmacies import RestaurantInfoRetriever
import logging
from marketing.shared import extract_hashtags_return_text2
from marketing.shared import n_get_completion

class AdCopyPersonas:
    def __init__(self, buyer_persona, goal, user_id):
        self.buyer_persona = buyer_persona
        self.goal = goal
        self.user_id = user_id

        retriever = RestaurantInfoRetriever(restaurant_id=user_id)
        restaurant_info = retriever.get_restaurant_info_by_id()
        self.restraurant_info_string_for_prompt = f"""
        Name : {restaurant_info.get("name", "")}\n
        Category : {restaurant_info.get("category", "")}\n
        Website : {restaurant_info.get("website", "")}\n
        Whatsapp Number : {restaurant_info.get("whatsapp", "")}\n
        Phone Number : {restaurant_info.get("phone_number", "")}\n
        Opening Hours : {restaurant_info.get("opening_hours", "")}\n
        Address : {restaurant_info.get("address", "")}\n
        Menu : {restaurant_info.get("menu", "")}\n
        """

    def create_prompt(self):
        buyer_persona_str = bp_to_prompt(self.buyer_persona)
        goal_str = goal_to_prompt(self.goal)

        prompt = f"""
            Your task is to help a marketing team create compelling ad copy for a restaurant's online presence with 
            considering given restaurant information delimited by triple backticks and constraints. 
            The restaurant aim to attract a specific target audience described as the {buyer_persona_str}.
            The goal of these ad copy is {goal_str}. Please generate only one ad copy that can be used on the 
            restaurant's website and social media platforms and should highlight key aspects of the restaurant.
            Restaurant information : ''' {self.restraurant_info_string_for_prompt}'''

            Constraints :
            - Use emojis in the ad copy only if necessary.
            - Mention 2 products from menu.
            - Generated ad copy should be in only Italian language.
            - Create content related hashtags at the end of the ad copy.
            - Do not use restaurant info directly, use inside the generated ad text.
            """
        return prompt

    def complete_text(self, n):
        output = []
        try:
            prompt = self.create_prompt()
            text_it_list = n_get_completion(prompt,0.8, n)
            for text in text_it_list:
                hashtag, text_n = extract_hashtags_return_text2(text["message"]["content"])
                output.append({
                    "text": text_n,
                    "hashtag": hashtag
                })
        except Exception as e:
            logging.exception(e)
        return output
