import re
import emoji

address_tag = r'\<AD+RES+\>|\< AD+RES+\>|\<AD+RES+ \>|\< AD+RES+ \>'
phone_tag = r'\<PHONE\>|\< PHONE\>|\<PHONE \>|\< PHONE \>'
website_tag = r'\<WEBSITE\>|\< WEBSITE\>|\<WEBSITE \>|\< WEBSITE \>'
instagram_tag = r'\<INSTAGRAM\>|\< INSTAGRAM\>|\<INSTAGRAM \>|\< INSTAGRAM \>'
facebook_tag = r'\<FACEBO+K\>|\< FACEBO+K\>|\<FACEBO+K \>|\< FACEBO+K \>'
openHours_tag = r'<OPEN[a-z]* HOUR[S]*>|\< OPEN[a-z]* HOUR[S]*>|<OPEN[a-z]* HOUR[S]* >|< OPEN[a-z]* HOUR[S]* >'
closeHours_tag = r'<CLOS[a-z]* HOUR[S]*>|< CLOS[a-z]* HOUR[S]*>|<CLOS[a-z]* HOUR[S]* >|< CLOS[a-z]* HOUR[S]* >'
openDay_tag = r'\<OPEN[a-z]* DAY[S]*\>|\< OPEN[a-z]* DAY[S]*\>|\<OPEN[a-z]* DAY[S]* \>|\< OPEN[a-z]* DAY[S]* \>'
closeDay_tag = r'\<CLOS[a-z]* DAY[S]*\>|\< CLOS[a-z]* DAY[S]*\>|\<CLOS[a-z]* DAY[S]* \>|\< CLOS[a-z]* DAY[S]* \>'
whatsapp_tag = r'\<WHATSAP+\>|\< WHATSAP+\>|\<WHATSAP+ \>|\< WHATSAP+ \>'


class ReplaceTags:
    def findTags(self, text):
        tags = []
        match = re.compile(r'<.*?>', re.DOTALL)
        tags.append(match.findall(text))
        return tags

    def replace_tags(self, tag, text, toText):
        for i in re.findall(tag, text, re.IGNORECASE):
            text = text.replace(i, toText)
        return text

    def search_tags(self, text, website_link, address, phone, whatsapp, instagram, facebook,
                    openHour=None, closeHour=None, openDay=None, closeDay=None, lunch_and_dinner_dict={}):
        tags = self.findTags(text)
        for tag in tags[0]:
            if re.match(website_tag, tag, re.IGNORECASE):
                text = self.replace_tags(tag, text, website_link)
            if re.match(address_tag, tag, re.IGNORECASE):
                text = self.replace_tags(tag, text, address)
            if re.match(whatsapp_tag, tag, re.IGNORECASE):
                text = self.replace_tags(tag, text, whatsapp)
            if re.match(phone_tag, tag, re.IGNORECASE):
                text = self.replace_tags(tag, text, phone)
            if re.match(instagram_tag, tag, re.IGNORECASE):
                text = self.replace_tags(tag, text, instagram)
            if re.match(facebook_tag, tag, re.IGNORECASE):
                text = self.replace_tags(tag, text, facebook)

        text = text.split(";")[0]

        ending_string = lunch_dinner_string(lunch_and_dinner_dict)

        return text + ending_string


def lunch_dinner_string(lunch_and_dinner_dict):
    open_lunch = []
    open_dinner = []
    closed_lunch = []
    closed_dinner = []

    for key, val in lunch_and_dinner_dict.items():
        if "pranzo" in val:
            open_lunch.append(key)
        else:
            closed_lunch.append(key)

        if "cena" in val:
            open_dinner.append(key)
        else:
            closed_dinner.append(key)

    lunch_string = ""
    dinner_string = ""

    if 4 >= len(open_lunch) > 0:
        first_article = open_lunch[0] == "domenica" and "la " or "il "
        lunch_string = first_article + open_lunch[0]
        for i in range(len(open_lunch) - 2):
            lunch_string += ", " + open_lunch[i + 1]
        if len(open_lunch) > 1:
            lunch_string += " e " + open_lunch[-1]
    elif 7 > len(open_lunch) > 4:
        first_article = closed_lunch[0] == "domenica" and "la " or "il "
        first_day = first_article + closed_lunch[0]
        lunch_string = f"tutti i giorni tranne {first_day}"
        for i in range(len(closed_lunch) - 2):
            lunch_string += ", " + closed_lunch[i + 1]
        if len(closed_lunch) > 1:
            lunch_string += " e " + closed_lunch[-1]
    elif len(open_lunch) == 7:
        lunch_string = "tutti i giorni"

    if 4 >= len(open_dinner) > 0:
        first_article = open_dinner[0] == "domenica" and "la " or "il "
        dinner_string = first_article + open_dinner[0]
        for i in range(len(open_dinner) - 2):
            dinner_string += ", " + open_dinner[i + 1]
        if len(open_dinner) > 1:
            dinner_string += " e " + open_dinner[-1]
    elif 7 > len(open_dinner) > 4:
        first_article = closed_dinner[0] == "domenica" and "la " or "il "
        first_day = first_article + closed_dinner[0]
        dinner_string = f"tutti i giorni tranne {first_day}"
        for i in range(len(closed_dinner) - 2):
            dinner_string += ", " + closed_dinner[i + 1]
        if len(closed_dinner) > 1:
            dinner_string += " e " + closed_dinner[-1]

    elif len(open_dinner) == 7:
        dinner_string = "tutti i giorni"

    lunch_dinner = "\nVienici a trovare"

    if lunch_string and dinner_string:
        lunch_dinner += f"\n{emoji.emojize(':point_right:', language='alias')} A pranzo {lunch_string}\n" \
                        f"{emoji.emojize(':point_right:', language='alias')} A cena {dinner_string}"
    if lunch_string and not dinner_string:
        lunch_dinner += f"\n{emoji.emojize(':point_right:', language='alias')} A pranzo {lunch_string}"
    if not lunch_string and dinner_string:
        lunch_dinner += f"\n{emoji.emojize(':point_right:', language='alias')} A cena {dinner_string}"

    return lunch_dinner
