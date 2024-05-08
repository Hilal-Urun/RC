import operator
import os
import random
from functools import reduce
import dotenv
import emoji
import pandas as pd

# choosing emojis randomly according to the tags specified
def choose_emoji_random(which_emoji):
    return emoji.emojize(random.choice(which_emoji), language='alias')


def readFile(fileName):
    data = pd.read_csv(fileName)
    return data


class addChooser:
    def __init__(self, goal_persona_list):
        self.goal_persona_list = goal_persona_list

    # choosing randomly one example from the cta according to specified goals and personas
    def choose_from_cta(self):
        possible_ctas = []
        data = readFile(os.getenv("ctas"))
        copy_list = self.goal_persona_list.copy()
        # filtering data which is wanted
        query = [data[goal] == 1 for goal in copy_list]
        cta_data = data.loc[reduce(operator.and_, query)]
        for exp in cta_data["example"]:
            possible_ctas.append(exp)
        return random.choice(possible_ctas)

    # choosing randomly one example from the brand website according to specified goals and personas
    def choose_from_website(self):
        website_examples = []
        data = readFile(os.getenv('website_line'))
        copy_list = self.goal_persona_list.copy()
        copy_list.append("website_tag")
        query = [data[goal] == 1 for goal in copy_list]
        website_data = data.loc[reduce(operator.and_, query)]
        for exp in website_data["example"]:
            website_examples.append(exp)
        return random.choice(website_examples)

    # choosing randomly one example from the brand's contact numbers according to specified goals and personas
    # also did filter if user use normal phone or whatsapp or both
    def choose_from_phone(self, has_phone, has_whatsapp):
        data = readFile(os.getenv('general_phone_line'))
        if (has_phone == 1) & (has_whatsapp == 0):
            phone_examples = []
            copy_list = self.goal_persona_list.copy()
            copy_list.append("has_phone")
            copy_list2 = ["has_whatsapp", "whatsapp_phone_together"]
            query = [data[goal] == 1 for goal in copy_list] and [data[goal] == 0 for goal in copy_list2]
            has_phone_data = data.loc[reduce(operator.and_, query)]
            for exp in has_phone_data["example"]:
                phone_examples.append(exp)
            return random.choice(phone_examples)
        elif (has_phone == 1) & (has_whatsapp == 1):
            phone_examples = []
            copy_list = self.goal_persona_list.copy()
            copy_list.append("has_phone")
            copy_list.append("has_whatsapp")
            copy_list3 = ["whatsapp_phone_together"]
            query = [data[goal] == 1 for goal in copy_list] and [data[goal] == 0 for goal in copy_list3]
            phone_wp_data = data.loc[reduce(operator.and_, query)]
            for exp in phone_wp_data["example"]:
                phone_examples.append(exp)
            return random.choice(phone_examples)

    # choosing randomly one example from the brand social media according to specified goals and personas and which
    # social media account had
    def choose_from_socialMedia(self, has_facebook, has_instagram):
        data = readFile(os.getenv('social_media'))
        # if brand has only facebook account
        if (has_facebook == 1) & (has_instagram == 0):
            facebook_examples = []
            copy_list = self.goal_persona_list.copy()
            copy_list.append("has_facebook")
            copy_list2 = ["has_instagram", "has_snapchat", "has_tiktok", "has_xyz"]
            query = [data[goal] == 1 for goal in copy_list] and [data[goal] == 0 for goal in copy_list2]
            facebook_data = data.loc[reduce(operator.and_, query)]
            for exp in facebook_data["example"]:
                facebook_examples.append(exp)
            return random.choice(facebook_examples)
        # if brand has only instagram account
        elif (has_facebook == 0) & (has_instagram == 1):
            instagram_examples = []
            copy_list = self.goal_persona_list.copy()
            copy_list.append("has_instagram")
            copy_list3 = ["has_facebook", "has_snapchat", "has_tiktok", "has_xyz"]
            query = [data[goal] == 1 for goal in copy_list] and [data[goal] == 0 for goal in copy_list3]
            instagram_data = data.loc[reduce(operator.and_, query)]
            for exp in instagram_data["example"]:
                instagram_examples.append(exp)
            return random.choice(instagram_examples)
        # if brand has both facebook and instagram accounts
        elif (has_facebook == 1) & (has_instagram == 1):
            both_media = []
            copy_list = self.goal_persona_list.copy()
            copy_list.append("has_instagram")
            copy_list.append("has_facebook")
            copy_list4 = ["has_snapchat", "has_tiktok", "has_xyz"]
            query = [data[goal] == 1 for goal in copy_list] and [data[goal] == 0 for goal in copy_list4]
            both_data = data.loc[reduce(operator.and_, query)]
            for exp in both_data["example"]:
                both_media.append(exp)
            return random.choice(both_media)

    # choosing randomly one example from the brand working range according to specified goals and personas, also filtering
    # if brand wants to show only open and close hours, open and close day, open-close hour and close day, and also both info
    def choose_from_workingHours(self, hours, days):
        # data = readFile(os.path.join(path, config_object["FILEPATH"]["working_hours_line"]))
        # # if user wants to show open-close hours and open-close days
        # if (hours == 1) & (days == 1):
        #     hour_day_examples = []
        #     copy_list = self.goal_persona_list.copy()
        #     copy_list.append("has_opening_hours")
        #     copy_list.append("has_closing_hours")
        #     copy_list.append("has_opening_days")
        #     copy_list.append("has_closing_days")
        #     query = [data[goal] == 1 for goal in copy_list]
        #     hour_day_data = data.loc[reduce(operator.and_, query)]
        #     for exp in hour_day_data["example"]:
        #         hour_day_examples.append(exp)
        #     return random.choice(hour_day_examples)
        # # if user wants to show open and close hours
        # elif (hours == 1) & (days == 0):
        #     hours_example = []
        #     copy_list = self.goal_persona_list.copy()
        #     copy_list.append("has_opening_hours")
        #     copy_list.append("has_closing_hours")
        #     copy_list2 = ["has_opening_days", "has_closing_days"]
        #     query = [data[goal] == 1 for goal in copy_list] and [data[goal] == 0 for goal in copy_list2]
        #     hours_data = data.loc[reduce(operator.and_, query)]
        #     for exp in hours_data["example"]:
        #         hours_example.append(exp)
        #     return random.choice(hours_example)
        # # if user wants to show only open and closed days
        # elif (hours == 0) & (days == 1):
        #     day_example = []
        #     copy_list = self.goal_persona_list.copy()
        #     copy_list.append("has_opening_days")
        #     copy_list.append("has_closing_days")
        #     copy_list2 = ["has_opening_hours", "has_closing_hours"]
        #     query = [data[goal] == 1 for goal in copy_list] and [data[goal] == 0 for goal in copy_list2]
        #     day_data = data.loc[reduce(operator.and_, query)]
        #     for exp in day_data["example"]:
        #         day_example.append(exp)
        #     return random.choice(day_example)
        # # if user wants to show open-close hours and also closed day
        pass

    # choosing randomly one example from the brand's address according to specified goals and personas
    def choose_from_address(self):
        address_examples = []
        data = readFile(os.getenv('address_call'))
        copy_list = self.goal_persona_list.copy()
        copy_list.append("has_adress")
        query = [data[goal] == 1 for goal in copy_list]
        address_data = data.loc[reduce(operator.and_, query)]
        for exp in address_data["example"]:
            address_examples.append(exp)
        return random.choice(address_examples)

    # choosing randomly one example from the brand's reservation website according to specified goals and personas
    def choose_from_reversation(self):
        reversation_examples = []
        data = readFile(os.getenv('reserve_line'))
        copy_list = self.goal_persona_list.copy()
        copy_list.append("has_website")
        copy_list2 = ["has_whatsapp", "has_phone"]
        query = [data[goal] == 1 for goal in copy_list] and [data[goal] == 0 for goal in copy_list2]
        reversation_data = data.loc[reduce(operator.and_, query)]
        for exp in reversation_data["example"]:
            reversation_examples.append(exp)
        return random.choice(reversation_examples)

    # choosing randomly one example from the brand's delivery website according to specified goals and personas
    def choose_from_delivery(self):
        delivery_examples = []
        data = readFile(os.getenv('delivery_line'))
        copy_list = self.goal_persona_list.copy()
        copy_list.append("has_website")
        query = [data[goal] == 1 for goal in copy_list]
        delivery_data = data.loc[reduce(operator.and_, query)]
        for exp in delivery_data["example"]:
            delivery_examples.append(exp)
        return random.choice(delivery_examples)


class createTemplates(addChooser):
    # creates template 1  cta+ website + phone + social media with 3 different examples
    def template1(self, has_phone, has_wp, has_fb, has_insta):
        return f"{choose_emoji_random(os.getenv('ctas_emoji'))}{self.choose_from_cta()}{choose_emoji_random(os.getenv('ctas_emoji'))} \n{choose_emoji_random(os.getenv('website_emoji'))}{self.choose_from_website()} \n{self.choose_from_phone(has_phone, has_wp)} {choose_emoji_random(os.getenv('general_phone_emoji'))} \n{choose_emoji_random(os.getenv('social_media_emoji'))}{self.choose_from_socialMedia(has_fb, has_insta)}{choose_emoji_random(os.getenv('social_media_emoji'))} ;"

    # creates template 2 cta + adress + hours + reservation link + website + phone + social media with 3 different examples
    def template2(self, has_hours, has_days, has_fb, has_insta):
        return f"{choose_emoji_random(os.getenv('ctas_emoji'))}{self.choose_from_cta()}{choose_emoji_random(os.getenv('ctas_emoji'))}\n{choose_emoji_random(os.getenv('address_emoji'))}{self.choose_from_address()}\n{choose_emoji_random(os.getenv('working_hours_emoji'))}{self.choose_from_workingHours(has_hours, has_days)}\n{self.choose_from_reversation()} {choose_emoji_random(os.getenv('reserve_emoji'))}\n" + self.template1(
            has_hours, has_days, has_fb, has_insta)

    # creates Template 3 cta + adress + hours + delivery link + website + phone + social media with 3 different examples
    def template3(self, has_hours, has_days, has_fb, has_insta):
        return f"{choose_emoji_random(os.getenv('ctas_emoji'))}{self.choose_from_cta()}{choose_emoji_random(os.getenv('ctas_emoji'))}\n{choose_emoji_random(os.getenv('address_emoji'))}{self.choose_from_address()}\n{choose_emoji_random(os.getenv('working_hours_emoji'))}{self.choose_from_workingHours(has_hours, has_days)}\n{self.choose_from_delivery()}{choose_emoji_random(os.getenv('delivery_emoji'))}\n" + self.template1(
            has_hours, has_days, has_fb, has_insta)

    # creates template 4 cta + adress + hours + phone with 3 different examples
    def template4(self, has_hours, has_days, has_phone, has_wp):
        return f"{choose_emoji_random(os.getenv('ctas_emoji'))}{self.choose_from_cta()}{choose_emoji_random(os.getenv('ctas_emoji'))}\n{choose_emoji_random(os.getenv('address_emoji'))}{self.choose_from_address()} {choose_emoji_random(os.getenv('working_hours_emoji'))}\n{self.choose_from_workingHours(has_hours, has_days)} {choose_emoji_random(os.getenv('working_hours_emoji'))}\n{self.choose_from_phone(has_phone, has_wp)}{choose_emoji_random(os.getenv('general_phone_emoji'))} ;"
