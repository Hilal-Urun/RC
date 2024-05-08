import time
import logging
import numpy as np
import pandas as pd
from facebook_business.adobjects.adsinsights import AdsInsights
from facebook_business.adobjects.page import Page
from facebook_business.api import FacebookAdsApi
from facebook_business.exceptions import FacebookError
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import DateRange
from google.analytics.data_v1beta.types import Dimension
from google.analytics.data_v1beta.types import Filter
from google.analytics.data_v1beta.types import FilterExpression
from google.analytics.data_v1beta.types import FilterExpressionList
from google.analytics.data_v1beta.types import Metric
from google.analytics.data_v1beta.types import RunReportRequest
from google.oauth2 import service_account
from sentence_transformers import util
from marketing import db, API_VERSION
from marketing.shared import get_st_model
from marketing.google_to_facebook_interests.enrich_facebook_interests import translate
from marketing.utils import get_json_response, insert_one_interest_id, \
    list_of_unique_dict, translate_google_interests, get_best_interests_indexes
from marketing.data_from_user import get_menu_api, get_ingredients_api, get_social_accounts
import os

class AccessData:
    def __init__(self, access_token="", user_id="", property_id="", location="", page_id="",
                 account_id="", page_token=""):
        self.USER_ID = user_id
        self.ACCESS_TOKEN = access_token
        self.ACCOUNT_ID = account_id
        self.PROPERTY_ID = property_id
        self.LOCATION = location
        self.PAGE_ID = page_id
        self.PAGE_TOKEN = page_token
        INFO = {
            "private_key": os.getenv("gmb_private_key"),
            "client_email": "analytics@aigot-srl-gmb-1624991991770.iam.gserviceaccount.com",
            "token_uri": "https://oauth2.googleapis.com/token"
        }
        credentials = service_account.Credentials.from_service_account_info(info=INFO)
        self.client = BetaAnalyticsDataClient(credentials=credentials)

    def get_data_from_user_id(self):
        url = f"{os.getenv('dashboard_backend_internal')}/pharmacist/{self.USER_ID}?" + \
              f"socialAccounts.googleAnalyticsPropertyId&socialAccounts.facebookAdAccount&" + \
              f"socialAccounts.gmbLocationResourceIdentifier&socialAccounts.facebookPageResourceIdentifier&" \
              f"socialAccounts.facebookPageAuthToken"

        try:
            response = get_social_accounts(self.USER_ID)
            if response is None:
                response = get_json_response(url)

            if response is not None:
                self.PROPERTY_ID = response["socialAccounts"].get("googleAnalyticsPropertyId", "")
                self.LOCATION = response["socialAccounts"].get("gmbLocationResourceIdentifier", "")
                self.PAGE_ID = response["socialAccounts"].get("facebookPageResourceIdentifier", "")
                self.ACCOUNT_ID = response["socialAccounts"].get("facebookAdAccount", "")
                self.PAGE_TOKEN = response["socialAccounts"].get("facebookPageAuthToken", "")
            else:
                self.PROPERTY_ID =""
                self.LOCATION = ""
                self.PAGE_ID = ""
                self.ACCOUNT_ID = ""
                self.PAGE_TOKEN = ""
        except:
            self.PROPERTY_ID = ""
            self.LOCATION = ""
            self.PAGE_ID = ""
            self.ACCOUNT_ID = ""
            self.PAGE_TOKEN = ""

    def to_dict(self):
        return {
            "property_id": self.PROPERTY_ID,
            "page_id": self.PAGE_ID,
            "location": self.LOCATION,
            "user_id": self.USER_ID,
            "access_token": self.ACCESS_TOKEN,
            "account_id": self.ACCOUNT_ID,
            "page_token": self.PAGE_TOKEN,
            "google_key": os.getenv("gmb_private_key")
        }


names_to_delete = ["(not set)", "unknown"]
current_directory = os.path.dirname(os.path.realpath(__file__))


class BuyerPersona:
    def __init__(self, number_users=0, age_range=None, gender=None):
        if gender is None:
            gender = []
        if age_range is None:
            age_range = []
        self.number_users = number_users
        self.age_range = age_range
        self.geo_zone = []
        self.gender = gender
        self.google_interests = []
        self.facebook_interests = []
        self.field_of_work = []
        self.instruction_level = []
        self.sector_instruction = []
        self.device_category = []
        self.income = 0
        self.family_unit = 0
        self.type_of_buyer = []
        self.type_of_user = []
        self.favourite_social = []
        self.exit_pages = []

    def __str__(self):
        place = ','.join(self.geo_zone)
        age_range = str(min(self.age_range)) + ' to ' + str(max(self.age_range))
        gender = ','.join(self.gender)
        output = 'There are ' + str(self.number_users) + ' users with ' + age_range + \
                 ' years and who are ' + gender + ' and live in ' + place
        return output

    def get_number_users(self):
        return self.number_users

    def get_age_range(self):
        return self.age_range

    def get_geo_zone(self):
        return self.geo_zone

    def get_gender(self):
        return self.gender

    def get_google_interests(self):
        return self.google_interests

    def get_facebook_interests(self):
        return self.facebook_interests

    def get_field_of_work(self):
        return self.field_of_work

    def get_instruction_level(self):
        return self.instruction_level

    def get_sector_instruction(self):
        return self.sector_instruction

    def get_device_category(self):
        return self.device_category

    def get_income(self):
        return self.income

    def get_family_unit(self):
        return self.family_unit

    def get_type_of_buyer(self):
        return self.type_of_buyer

    def get_type_of_user(self):
        return self.type_of_user

    def get_favourite_social(self):
        return self.favourite_social

    def get_exit_pages(self):
        return self.exit_pages

    def to_dict(self):

        names_google_interests = [item["name_google_interest"] for item in self.google_interests]
        names_google_interests_translated = translate_google_interests(names_google_interests)
        names_facebook_interests = [item["name_facebook_interest"] for item in self.facebook_interests]

        facebook_interests_indexes = get_best_interests_indexes(names_facebook_interests)
        facebook_interests_to_display = [names_facebook_interests[i] for i in facebook_interests_indexes]

        google_interests_indexes = get_best_interests_indexes(names_google_interests)
        google_interests_to_display = [names_google_interests[i] for i in google_interests_indexes]

        value = {
            "number_of_users": self.number_users,
            "age_min": min(self.age_range) if len(self.age_range) != 0 else 18,
            "age_max": max(self.age_range) if len(self.age_range) != 0 else 65,
            "gender": self.gender,
            "geo_zone": self.geo_zone,
            "device_category": self.device_category,
            "google_interests": names_google_interests_translated,
            "facebook_interests": self.facebook_interests,
            "facebook_interests_to_display": facebook_interests_to_display,
            "google_interests_to_display": google_interests_to_display,
            "field_of_work": self.field_of_work,
            "instruction_level": self.instruction_level,
            "sector_instruction": self.sector_instruction,
            "income": self.income,
            "family_unit": self.family_unit,
            "type_of_buyer": self.type_of_buyer,
            "type_of_user": self.type_of_user,
            "favourite_social": self.favourite_social,
            "exit_pages": self.exit_pages
        }
        return value

    def __add__(self, other):
        """ method to add two buyer personas """
        buyer_persona = BuyerPersona()

        # setting number
        number_1 = self.number_users
        number_2 = other.number_users

        number = number_1 + number_2

        buyer_persona.number_users = number

        # setting age
        age_range_1 = self.age_range
        age_range_2 = other.age_range

        if len(age_range_1) != 0 or len(age_range_2) != 0:
            min_age = min(age_range_1 + age_range_2)
            max_age = max(age_range_1 + age_range_2)

            age_range = [min_age, max_age]

        else:
            age_range = []

        buyer_persona.age_range = age_range

        # setting gender
        gender_1 = self.gender
        gender_2 = other.gender

        gender = list(set(gender_1 + gender_2))

        buyer_persona.gender = gender

        # setting geo zone

        geo_zone_1 = self.geo_zone
        geo_zone_2 = other.geo_zone

        geo_zone = list(set(geo_zone_1 + geo_zone_2))

        buyer_persona.geo_zone = geo_zone

        # setting interests

        google_interests_1 = self.google_interests
        google_interests_2 = other.google_interests

        google_interests = google_interests_1 + google_interests_2
        buyer_persona.google_interests = aggregate_dicts(google_interests)

        # setting field of work

        field_of_work_1 = self.field_of_work
        field_of_work_2 = other.field_of_work

        field_of_work = list(set(field_of_work_1 + field_of_work_2))

        buyer_persona.field_of_work = field_of_work

        # setting instruction level

        instruction_level_1 = self.instruction_level
        instruction_level_2 = other.instruction_level

        instruction_level = list(set(instruction_level_1 + instruction_level_2))

        buyer_persona.instruction_level = instruction_level

        # setting sector_instruction

        sector_instruction_1 = self.sector_instruction
        sector_instruction_2 = other.sector_instruction

        sector_instruction = list(set(sector_instruction_1 + sector_instruction_2))

        buyer_persona.sector_instruction = sector_instruction

        # setting device_category

        device_category_1 = self.device_category
        device_category_2 = other.device_category

        device_category = list(set(device_category_1 + device_category_2))

        buyer_persona.device_category = device_category

        # setting income

        income_1 = float(self.income)
        weight_1 = self.number_users

        income_2 = float(other.income)
        weight_2 = other.number_users

        try:
            income = (income_1 * weight_1 + income_2 * weight_2) / (weight_1 + weight_2)
        except ZeroDivisionError as zd:
            logging.exception(zd)
            income = 0

        buyer_persona.income = income

        # setting family_unit

        family_unit_1 = float(self.family_unit)
        weight_1 = self.number_users

        family_unit_2 = float(other.family_unit)
        weight_2 = other.number_users

        try:
            family_unit = (family_unit_1 * weight_1 + family_unit_2 * weight_2) / (weight_1 + weight_2)
        except ZeroDivisionError as zd:
            logging.exception(zd)
            family_unit = 0

        buyer_persona.family_unit = round(family_unit)

        # setting type of buyer

        type_of_buyer_1 = self.type_of_buyer
        type_of_buyer_2 = other.type_of_buyer

        type_of_buyer = list(set(type_of_buyer_1 + type_of_buyer_2))

        buyer_persona.type_of_buyer = type_of_buyer

        # setting type_of_user

        type_of_user_1 = self.type_of_user
        type_of_user_2 = other.type_of_user

        type_of_user = list(set(type_of_user_1 + type_of_user_2))

        buyer_persona.type_of_user = type_of_user

        # setting favourite_social

        favourite_social_1 = self.favourite_social
        favourite_social_2 = other.favourite_social

        favourite_social = list(set(favourite_social_1 + favourite_social_2))

        buyer_persona.favourite_social = favourite_social

        # setting exit_pages

        exit_pages_1 = self.exit_pages
        exit_pages_2 = other.exit_pages

        exit_pages = sum_exit_pages_dict(exit_pages_1, exit_pages_2)
        buyer_persona.exit_pages = exit_pages

        # setting interests

        facebook_interests_1 = self.facebook_interests
        facebook_interests_2 = other.facebook_interests

        facebook_interests = facebook_interests_1 + facebook_interests_2
        buyer_persona.facebook_interests = list_of_unique_dict(facebook_interests)

        return buyer_persona

    def set_google_interests_to_facebook_interests(self, cutoff=0.6):
        """ This function takes the interests of google and, through a
        dictionary that links google interests to facebook interests,
        set the corresponding facebook interests """

        google_to_facebook_interests = db.google_to_facebook_interests.find_one()["google_to_facebook_interests"]

        google_interests = [item["name_google_interest"] for item in self.google_interests]

        for google_interest in google_interests:
            facebook_interest = facebook_interests_from_google(google_to_facebook_interests, google_interest, cutoff)
            self.facebook_interests += facebook_interest

        self.facebook_interests = list_of_unique_dict(self.facebook_interests)

    def group_interests_by_topic(self):
        """ This method groups the interest in topic and returns the interests
        belonging to the two most popultated topics """
        interests = self.facebook_interests

        df_interests = pd.DataFrame(interests)

        interests_of_topics = []

        if not df_interests.empty:
            first_two_topics = df_interests["topic_facebook_interest"].value_counts()[:2]

            for interest in interests:
                if interest["topic_facebook_interest"] in first_two_topics:
                    interests_of_topics.append(interest)

        self.facebook_interests = interests_of_topics


#################################################################


def get_facebook_buyer_personas(page_id, access_token, page_token, save_json=False, return_dict=False):
    """ This function returns buyer persona from facebook.
    It can return buyer personas as a dictionary or save them
    in a json file"""

    dataframes = get_facebook_dataframes(page_id, access_token, page_token)
    df_fans = dataframes.get('page_fans', pd.DataFrame())
    df_gender_age = dataframes.get('page_fans_gender_age', pd.DataFrame())
    df_city = dataframes.get('page_fans_city', pd.DataFrame())
    series_city = df_city.sum()
    series_gender_age = df_gender_age.sum()
    total = 0 if df_fans.empty else int(df_fans.sum())
    gender_age_percentage = get_percentage(series_gender_age, total)
    city_percentage = get_percentage(series_city, total)

    data = []
    for item in gender_age_percentage:
        gender = item.split(".")[0]
        age = item.split(".")[1]
        if age == "65+":
            age = "65-74"
        age_min = int(age.split("-")[0])
        age_max = int(age.split("-")[1])
        perc = gender_age_percentage[item]
        data.append(
            {
                "gender": gender == "M" and "male" or "female",
                "age_min": age_min,
                "age_max": age_max,
                "percentage": perc
            })

    df = pd.DataFrame(data)
    if df.empty:
        return [BuyerPersona(), BuyerPersona()]
    df = df.sort_values(by="percentage", ascending=False, ignore_index=True)

    bp_prim = {
        "gender": df["gender"].iloc[0],
        "percentage": df["percentage"].iloc[0],
        "age_min": int(df["age_min"].iloc[0]),
        "age_max": int(df["age_max"].iloc[0])
    }

    df.drop(axis=0, index=0, inplace=True)
    df.reset_index(drop=True, inplace=True)

    for i, row in df.iterrows():
        if bp_prim["percentage"] > 0.25:
            break
        if row["gender"] == bp_prim["gender"]:
            if row["age_max"] == (bp_prim["age_min"] - 1) or row["age_min"] == (bp_prim["age_max"] + 1):
                bp_prim["percentage"] += row["percentage"]
                bp_prim["age_min"] = int(min(bp_prim["age_min"], row["age_min"]))
                bp_prim["age_max"] = int(max(bp_prim["age_max"], row["age_max"]))
                df.drop(axis=0, index=i, inplace=True)
                df.reset_index(drop=True, inplace=True)

    bp_sec = {
        "gender": df["gender"].iloc[0],
        "percentage": df["percentage"].iloc[0],
        "age_min": int(df["age_min"].iloc[0]),
        "age_max": int(df["age_max"].iloc[0])
    }

    for i, row in df.iterrows():
        if bp_sec["percentage"] > 0.25:
            break
        if row["gender"] == bp_sec["gender"]:
            if row["age_max"] == (bp_sec["age_min"] - 1) or row["age_min"] == (bp_sec["age_max"] + 1):
                bp_sec["percentage"] += row["percentage"]
                bp_sec["age_min"] = int(min(bp_sec["age_min"], row["age_min"]))
                bp_sec["age_max"] = int(max(bp_sec["age_max"], row["age_max"]))
                df.drop(axis=0, index=i, inplace=True)
                df.reset_index(drop=True, inplace=True)

    comp_val = 0
    max_city = ""
    for key, val in city_percentage.items():
        if val > comp_val:
            max_city = key
            comp_val = val
    primary_persona = BuyerPersona(number_users=int(bp_prim["percentage"] * df_fans["value"][-1]),
                                   age_range=[bp_prim["age_min"], bp_prim["age_max"]],
                                   gender=[bp_prim["gender"]])
    primary_persona.geo_zone = max_city.split(",")[:1]
    secondary_persona = BuyerPersona(number_users=int(bp_sec["percentage"] * df_fans["value"][-1]),
                                     age_range=[bp_sec["age_min"], bp_sec["age_max"]],
                                     gender=[bp_sec["gender"]])
    secondary_persona.geo_zone = max_city.split(",")[:1]

    buyer_personas = [primary_persona, secondary_persona]
    buyer_personas.sort(key=lambda bp: bp.get_number_users(), reverse=True)
    if save_json is True:
        buyer_personas_dict = [item.to_dict() for item in buyer_personas]
        db["facebook_buyer_persona"].insert_many(buyer_personas_dict)
    if return_dict is True:
        buyer_personas_dict = [item.to_dict() for item in buyer_personas]
        return buyer_personas_dict
    else:
        return buyer_personas


#################################################################


def age_to_int(age):
    if age == ["65+"]:
        return [65, 74]
    else:
        return list(map(int, age))


def run_report(client,property_id, metric_name, dimension_name, start_date=90, **kwargs):
    if kwargs:
        request = RunReportRequest(
            property=f"properties/{property_id}",
            dimensions=[Dimension(name=dimension_name)],
            metrics=[Metric(name=metric_name)],
            dimension_filter=set_segment(**kwargs),
            date_ranges=[DateRange(start_date=str(start_date) + "daysAgo", end_date="today")],
            limit=10000
        )
    else:
        request = RunReportRequest(
            property=f"properties/{property_id}",
            dimensions=[Dimension(name=dimension_name)],
            metrics=[Metric(name=metric_name)],
            date_ranges=[DateRange(start_date=str(start_date) + "daysAgo", end_date="today")],
            limit=10000
        )

    response = client.run_report(request)

    dataframes = []

    for row in response.rows:
        data = {
            response.dimension_headers[0].name: [item.value for item in row.dimension_values],
            response.metric_headers[0].name: [int(item.value) for item in row.metric_values]
        }
        dataframes.append(pd.DataFrame(data))

    if len(dataframes) != 0:
        df = pd.concat(dataframes, ignore_index=True)
        df.sort_values(by=response.metric_headers[0].name, ignore_index=True, ascending=False)

        for name in names_to_delete:
            df = df.loc[df[response.dimension_headers[0].name] != name]

        df[response.metric_headers[0].name] = df[response.metric_headers[0].name] / df[
            response.metric_headers[0].name].sum()

        if dimension_name == "userAgeBracket":
            df["userAgeBracket"] = df["userAgeBracket"].apply(lambda x: age_to_int(x.split('-')))
        elif dimension_name in ["city", "brandingInterest", "userGender", "deviceCategory", "newVsReturning"]:
            df[dimension_name] = df[dimension_name].apply(lambda x: [x])

        return df.reset_index(drop=True)

    else:
        return pd.DataFrame()


def get_total_users(client, property_id, start_date=90):
    request = RunReportRequest(
        property=f"properties/{property_id}",
        metrics=[Metric(name="totalUsers")],
        dimension_filter=FilterExpression(
            filter=Filter(
                field_name="country",
                string_filter=Filter.StringFilter(value="Italy"),
            )
        ),
        date_ranges=[DateRange(start_date=str(start_date) + "daysAgo", end_date="today")],
        limit=10000
    )

    response = client.run_report(request)

    if response.rows:
        # Check if the list is not empty before accessing its elements
        return int(response.rows[0].metric_values[0].value)
    else:
        # Handle the case when there are no rows in the response
        return 0


def get_metric_buyer_persona(client, property_id, metric, start_date=90, **kwargs):
    dimensions = ["userAgeBracket", "userGender", "city", "deviceCategory", "newVsReturning", "brandingInterest"]

    dataframes = {}

    for dimension in dimensions:
        dataframes[dimension] = run_report(client, property_id, metric, dimension, **kwargs)

    total_users = get_total_users(client, property_id, start_date)
    df_interests = dataframes[dimensions[5]]

    len_interests = min(15, len(df_interests))

    if len_interests > 0:
        names_google_interests = dataframes[dimensions[5]].iloc[:15].sum()[dimensions[5]]
        names_google_interests = [preprocessing(interest) for interest in names_google_interests]

        google_interests = [
            {
                "name_google_interest": name,
                "encoded_google_interest": get_st_model().encode(name)
            }
            for name in names_google_interests
        ]
    else:
        google_interests = []

    buyer_personas = buyer_personas_from_dataframes(dataframes, total_users, google_interests, metric)

    return buyer_personas


def get_google_buyer_personas(client, property_id, return_dict=False, **kwargs):
    metrics = ["totalUsers", "eventCount"]

    buyer_personas_users = get_metric_buyer_persona(client, property_id, metrics[0], **kwargs)
    buyer_personas_users.sort(key=lambda persona: persona.get_number_users(), reverse=True)
    buyer_personas_event = get_metric_buyer_persona(client, property_id, metrics[1], **kwargs)
    buyer_personas_event.sort(key=lambda persona: persona.get_number_users(), reverse=True)

    if return_dict is True:
        return {
            "primary_buyer_personas": [bp.to_dict() for bp in buyer_personas_users],
            "secondary_buyer_personas": [bp.to_dict() for bp in buyer_personas_event]
        }
    else:
        return {
            "primary_buyer_personas": buyer_personas_users,
            "secondary_buyer_personas": buyer_personas_event
        }


###############################


def get_facebook_dataframes(page_id, access_token, page_token, track_days=30):
    """ This function returns a dataframe with metrics specified below for a specific page """

    FacebookAdsApi.init(access_token=access_token, api_version=API_VERSION)

    metrics = ['page_fans', 'page_fans_gender_age', 'page_fans_country',
               'page_fans_city', 'page_fans_by_like_source']
    end_date = str(int(time.time()))
    start_date = str(int(time.time()) - int(track_days * 86400))

    params = {
        "metric": metrics,
        "since": start_date,
        "until": end_date
    }

    try:
        page_access_token = Page(page_id).api_get(fields=["access_token"])["access_token"]
        FacebookAdsApi.init(access_token=page_access_token, api_version=API_VERSION)
        response = Page(page_id).get_insights(params=params)
        data = [r.export_all_data() for r in response]

    except FacebookError as fb:
        logging.exception(fb)
        data = []

    if data:
        dataframes = {}
        for metric in data:
            key = metric['name']
            if key not in dataframes.keys():
                val = flat_dict_to_df(metric)
                dataframes[key] = val
        return dataframes
    else:
        return {}


def get_total_likes(page_id, page_token):
    if page_token is None:
        return 0
    FacebookAdsApi.init(access_token=page_token, api_version=API_VERSION)

    metrics = ['page_fans']
    until = str(int(time.time()))
    since = str(int(time.time()) - int(86400))

    params = {
        "metric": metrics,
        "since": since,
        "until": until
    }

    try:
        fields = [
            AdsInsights.Field.spend,
            AdsInsights.Field.impressions,
            AdsInsights.Field.clicks,
            AdsInsights.Field.outbound_clicks,
        ]
        page_access_token = Page(page_id).api_get(fields=["access_token"])["access_token"]
        FacebookAdsApi.init(access_token=page_access_token, api_version=API_VERSION)
        response = Page(page_id).get_insights(params=params,fields=fields)
        data = [r.export_all_data() for r in response]

    except FacebookError as fb:
        logging.exception(fb)
        return 0
    except Exception as e:
        logging.exception(e)
        return 0
    if data:
        try:
            if data and "values" in data[0] and data[0]["values"]:
                output = data[0]["values"][0]["value"]
            else:
                output = 0

        except FacebookError as fb:
            logging.exception(fb)
            output = 0
        except Exception as e:
            logging.exception(e)
            output = 0

        return output

    else:
        return 0


######################################


def get_percentage(series, total):
    """ This function returns percentages of a series with
    respect to total """
    percentage_dict = (series / total).to_dict()
    return percentage_dict


def col_names(values):
    """ This function returns an array with the names of all variables
    inside a response """

    keys = []
    for item in values:
        value = item['value']
        keys.append(list(value.keys()))
    flat_list = [item for sublist in keys for item in sublist]
    flat_list = set(flat_list)
    flat_list = list(flat_list)
    return flat_list


def flat_dict_to_df(response):
    """
    This function returns a dataframe from a response
    where some data are 'hidden', for example
    > input: response={'x':1,{'var': y, 'val': 2}
    > output: dataframe('x': 1, 'y': 2)
    """

    values = response['values']
    if isinstance(values[0]['value'], dict):
        columns_names = col_names(values)
        columns_names.append('end_time')
        df_facebook = pd.DataFrame(columns=columns_names)

        for value in values:
            row = value['value']
            row['end_time'] = value['end_time']
            df_next = pd.DataFrame(row, index=[0])
            df_facebook = pd.concat([df_facebook, df_next])
    else:
        df_facebook = pd.DataFrame(values)

    df_facebook['end_time'] = pd.to_datetime(df_facebook['end_time'])
    df_facebook.set_index('end_time', inplace=True)
    df_facebook.fillna(0)
    return df_facebook


def preprocessing(google_interest):
    google_interest = google_interest.replace("&", "and")
    google_interest = google_interest.replace("/", " ")
    google_interest = google_interest.replace("’", "'")

    return google_interest


def facebook_interests_from_google(google_to_facebook_interests, google_interest, cutoff):
    select_google_interest = [elem for elem in google_to_facebook_interests if
                              elem["name_google_interest"] == google_interest]

    if len(select_google_interest) == 0:
        print("This google interest is not in the file google_to_facebook_interests.")
        facebook_interests = []

    else:
        facebook_interests = [item for item in select_google_interest[0]["facebook_interests"]
                              if item["similarity"] > cutoff]

    return facebook_interests


def similarity_interests_value(bp_1, bp_2):
    """ This function returns the similarity between interests """

    interests_1_encoded = np.array([interest["encoded_google_interest"] for interest in bp_1.google_interests])
    interests_2_encoded = np.array([interest["encoded_google_interest"] for interest in bp_2.google_interests])

    if len(interests_1_encoded) == 0 or len(interests_2_encoded) == 0:
        similarity_index = 0

    else:

        tensor = util.pytorch_cos_sim(interests_1_encoded, interests_2_encoded)

        similarity_index = tensor.max(dim=1)[0].numpy().mean()

    return similarity_index


def similarity_age_value(bp_1, bp_2):
    """ We define similarity as ~e^{-tot_diff/10} where tot_diff is for example
    age_range_1 = [25, 34]
    age_range_2 = [35, 44]
    tot_diff = (35-25)+(44-34)= 20
    similarity = e^{-2} = 13.5 % """

    age_range_1 = np.array(bp_1.age_range)
    age_range_2 = np.array(bp_2.age_range)

    tot_diff = np.abs(np.sum(age_range_1 - age_range_2))

    similarity_age = np.exp(-tot_diff / 10)

    return similarity_age


def aggregate_buyer_persona(bp_1, bp_2, similarity_threshold=0.65):
    """ This function returns a similarity index between two buyer personas """
    similarity_interests = similarity_interests_value(bp_1, bp_2)
    similarity_age = similarity_age_value(bp_1, bp_2)

    similarity_buyer_persona = 0.85 * similarity_interests + 0.15 * similarity_age

    if (similarity_buyer_persona >= similarity_threshold) and len(bp_1.geo_zone + bp_2.geo_zone) <= 2:
        return bp_1 + bp_2
    else:
        return None


def aggregate_personas_one_time(personas):
    """ This function takes as input an array of buyer personas and returns
    a list with the aggregated personas (i.e. with similarity > threshold similarity index) """

    for i, persona_1 in enumerate(personas):
        for j, persona_2 in enumerate(personas):
            if i != j:
                buyer_persona = aggregate_buyer_persona(persona_1, persona_2)
                if buyer_persona is not None:
                    personas = [personas[k] for k in range(len(personas)) if k not in [i, j]]
                    personas.append(buyer_persona)
                    return personas


def aggregate_personas(personas):
    initial = personas

    while True:
        final = aggregate_personas_one_time(initial)

        if final is None:
            break
        else:
            initial = final

    output = [bp for bp in sorted(initial, key=lambda persona: persona.get_number_users(), reverse=True)]

    return output


def aggregate_dicts_one_time(list_of_dicts):
    for i, dict1 in enumerate(list_of_dicts):
        for j, dict2 in enumerate(list_of_dicts):
            if i != j and dict1["name_google_interest"] == dict2["name_google_interest"]:
                new_elem = {
                    "name_google_interest": dict1["name_google_interest"],
                    "encoded_google_interest": dict1["encoded_google_interest"],
                }
                list_of_dicts = [list_of_dicts[k] for k in range(len(list_of_dicts)) if k not in [i, j]]
                list_of_dicts.append(new_elem)

                return list_of_dicts


def aggregate_dicts(list_of_dicts):
    initial = list_of_dicts

    while True:
        final = aggregate_dicts_one_time(initial)

        if final is None:
            break

        else:
            initial = final

    return initial


def sum_exit_pages_dict(dicts_1, dicts_2):
    all_pages = list(set([item["page_name"] for item in dicts_1] +
                         [item["page_name"] for item in dicts_1]))

    new_array = []

    for name in all_pages:
        new_dict = {"page_name": name}

        if name in [item["page_name"] for item in dicts_1]:
            select_item = [item for item in dicts_1 if item["page_name"] == name][0]
            val_1 = select_item["number_of_users"]
        else:
            val_1 = 0

        if name in [item["page_name"] for item in dicts_2]:
            select_item = [item for item in dicts_2 if item["page_name"] == name][0]
            val_2 = select_item["number_of_users"]
        else:
            val_2 = 0

        new_dict["number_of_users"] = val_1 + val_2

        new_array.append(new_dict)

    return new_array


def sum_buyerpersonas(persona1, persona2):
    """ This function sums a facebook buyer persona and a Google buyer persona i.e.
    if age, gender and geo zone are equals then we add together the number of users """
    age_condition = is_contained_age_range(persona1.age_range, persona2.age_range)
    gender_condition = is_contained(persona1.gender, persona2.gender)
    geo_condition = is_contained(persona1.geo_zone, persona2.geo_zone)

    if age_condition and gender_condition and geo_condition:
        return persona1 + persona2


def english_to_italian(city):
    if city == "Milan":
        return "Milano"
    elif city == "Rome":
        return "Roma"
    elif city == "Naples":
        return "Napoli"
    elif city == "Florence":
        return "Firenze"
    elif city == "Turin":
        return "Torino"
    elif city == "Venice":
        return "Venezia"
    elif city == "Genoa":
        return "Genova"
    elif city == "Padua":
        return "Padova"
    else:
        return city


def find_indices(lst, val):
    indices = []

    for i, elem in enumerate(lst):
        if val == elem:
            indices.append(i)

    return indices


def process_list(indices):
    output_list = []

    # flatten and take only unique values

    flatten = [i for elem in indices for i in elem]

    # now I take only the unique element preserving the order

    for elem in flatten:
        if elem not in output_list:
            output_list.append(elem)

    return output_list


def find_facebook_interests(query, access_token):
    """ This function returns a list of suggested interests if no one is found """

    output = []
    url = f"https://graph.facebook.com/{API_VERSION}/search?type=adinterest&q={query}&access_token={access_token}"
    try:
        suggestion_list = get_json_response(url)["data"]
    except FacebookError as fb:
        logging.exception(fb)
        suggestion_list = []

    for interest in suggestion_list:
        new_elem = {"name_facebook_interest": interest["name"],
                    "id_facebook_interest": interest["id"],
                    "topic_facebook_interest": interest.get("topic", "NoTopicFound"),
                    "audience_size": int((interest["audience_size_lower_bound"] +
                                          interest["audience_size_upper_bound"]) / 2),
                    "name_facebook_interest_translated": translate(interest["name"], interest["id"])}
        output.append(new_elem)

    for elem in output:
        insert_one_interest_id(db["facebook_interests"], elem)

    new_output = []
    for elem in output:
        new_output.append(
            {
                "name_facebook_interest": elem["name_facebook_interest"],
                "id_facebook_interest": int(elem["id_facebook_interest"]),
                "topic_facebook_interest": elem["topic_facebook_interest"]
            }
        )

    return list_of_unique_dict(new_output)[:5]


def get_interests_from_menu_func(menu, access_token, is_processed=False, cutoff=0.75):
    """ This method finds the facebook interests related to the menu.
    I assume the menu is something like ["pizza margherita", "bistecca alla fiorentina"] """
    output = []
    count = 0
    for item in menu:
        output += find_facebook_interests(query=item, access_token=access_token)
        count += 1
        if count % 20 == 0:
            time.sleep(60)

    if not is_processed:
        with open(current_directory + "/google_to_facebook_interests/stopwords.txt", "r") as f:
            stopwords = f.readlines()
            for i, elem in enumerate(stopwords):
                stopwords[i] = elem.replace("\n", "")
        menu = [item for elem in menu for item in elem.split()]
        menu = [word for word in menu if word not in stopwords]
        output += get_interests_from_menu_func(menu, access_token, is_processed=True)

    return output


def get_interests_from_ingredients_func(ingredient_list, access_token, cutoff=0.75):
    """ This method finds the facebook interests related to the ingredients.
    I assume the ingredients is something like ["pizza", "carne"] """

    output = []
    count = 0
    for ingredient in ingredient_list:
        facebook_interests_similar = find_facebook_interests(query=ingredient, access_token=access_token)
        count += 1
        if count % 20 == 0:
            time.sleep(60)

        output += facebook_interests_similar

    return output


# ============================================================= #


def get_primary_secondary_buyer_persona(access_data=None, **kwargs):
    user_id = access_data.USER_ID
    access_token = access_data.ACCESS_TOKEN
    page_id = access_data.PAGE_ID
    property_id = access_data.PROPERTY_ID
    location = access_data.LOCATION
    client = access_data.client
    page_token = access_data.PAGE_TOKEN
    if user_id:
        ingredients = get_ingredients_api(user_id)
        menu = get_menu_api(user_id)
    else:
        ingredients = []
        menu = []

    if property_id:
        try:
            personas_google = get_google_buyer_personas(client, property_id, **kwargs)
            primary_google = personas_google["primary_buyer_personas"]
            secondary_google = personas_google["secondary_buyer_personas"]
        except Exception as e:
            logging.exception(e)
            primary_google = [BuyerPersona()]
            secondary_google = [BuyerPersona()]
    else:
        primary_google = [BuyerPersona()]
        secondary_google = [BuyerPersona()]

    if access_token and page_id:
        try:
            personas_facebook = get_facebook_buyer_personas(page_id, access_token, page_token)
        except Exception as e:
            logging.exception(e)
            personas_facebook = [BuyerPersona()] * 2
    else:
        personas_facebook = [BuyerPersona()] * 2

    interests_menu_ingredients = []

    if len(ingredients) > 0:
        interests_menu_ingredients += get_interests_from_ingredients_func(ingredients, access_token)

    if len(menu) > 0:
        interests_menu_ingredients += get_interests_from_menu_func(menu, access_token)

    gmb_interests = get_interests_from_gmb(location, access_token)
    if len(gmb_interests)>0:
        interests = list_of_unique_dict(interests_menu_ingredients + gmb_interests)
    else:
        interests = list_of_unique_dict(interests_menu_ingredients)

    interests = enrich_facebook_interests(interests, access_token)

    primary_personas = []

    if len(primary_google) == 0:
        primary_google = [BuyerPersona()]

    if len(personas_facebook) == 0:
        personas_facebook = [BuyerPersona()]

    for persona_google in primary_google:
        persona = sum_buyerpersonas(personas_facebook[0], persona_google)
        if persona is not None:
            primary_personas.append(persona)

    primary_personas = [persona for persona in
                        sorted(primary_personas, reverse=True, key=lambda x: x.get_number_users())]

    secondary_personas = []

    for persona_google in secondary_google:
        persona = sum_buyerpersonas(personas_facebook[1], persona_google)
        if persona is not None:
            secondary_personas.append(persona)

    secondary_personas = [persona for persona in
                          sorted(secondary_personas, reverse=True, key=lambda x: x.get_number_users())]

    first_persona = get_persona(primary_personas)
    first_persona.facebook_interests = list_of_unique_dict(first_persona.facebook_interests +
                                                           interests_menu_ingredients)
    second_persona = get_persona(secondary_personas)
    second_persona.facebook_interests = list_of_unique_dict(second_persona.facebook_interests +
                                                            interests_menu_ingredients)

    first_persona.set_google_interests_to_facebook_interests()
    first_persona.facebook_interests = same_type_interests(first_persona.facebook_interests)
    first_persona.facebook_interests = list_of_unique_dict(first_persona.facebook_interests + interests)
    # first_persona.group_interests_by_topic()

    second_persona.set_google_interests_to_facebook_interests()
    second_persona.facebook_interests = same_type_interests(second_persona.facebook_interests)
    second_persona.facebook_interests = list_of_unique_dict(second_persona.facebook_interests + interests)
    # second_persona.group_interests_by_topic()

    first_persona.facebook_interests = [item for item in first_persona.facebook_interests.copy()
                                        if "food" in item["topic_facebook_interest"].lower()]

    second_persona.facebook_interests = [item for item in second_persona.facebook_interests.copy()
                                         if "food" in item["topic_facebook_interest"].lower()]

    first_persona_dict = first_persona.to_dict()
    second_persona_dict = second_persona.to_dict()

    if property_id:
        try:
            website_users = get_total_users(client, property_id, start_date=30)
        except Exception as e:
            logging.exception(e)
            website_users = 0
    else:
        website_users = 0

    try:
        facebook_likes = get_total_likes(page_id, page_token)
    except FacebookError as fb:
        logging.exception(fb)
        facebook_likes = 0
    except Exception as e:
        logging.exception(e)
        facebook_likes = 0

    output_dict = {
        "description": "Primary and secondary buyer persona",
        "primary_buyer_persona": first_persona_dict,
        "secondary_buyer_persona": second_persona_dict,
        "facebook_likes": facebook_likes,
        "website_users": website_users,
        "menu": menu
    }
    return output_dict


def set_segment(**kwargs):
    expressions = []

    for item in kwargs.items():
        filter_expression = FilterExpression(
            filter=Filter(
                field_name=str(item[0]),
                string_filter=Filter.StringFilter(
                    match_type=Filter.StringFilter.MatchType.EXACT,
                    value=item[1],
                )
            )
        )
        expressions.append(filter_expression)

    dimension_filter = FilterExpression(
        and_group=FilterExpressionList(
            expressions=expressions
        )
    )
    return dimension_filter


def is_contained_age_range(age_1, age_2):
    """ This function returns true if age_1 is contained in age_2 or vice-versa.
    If not returns false """

    if len(age_1) == 0 or len(age_2) == 0:
        return True

    if min(age_1) >= min(age_2) and max(age_1) <= max(age_2):
        return True

    elif min(age_2) >= min(age_1) and max(age_2) <= max(age_1):
        return True

    else:
        return False


def is_contained(arr_1, arr_2):
    """ Check if all elements of an array are contained in the other """
    arr_contained = arr_1 if len(arr_1) <= len(arr_2) else arr_2

    arr_to_contain = arr_2 if len(arr_1) <= len(arr_2) else arr_1

    cond = True

    for elem in arr_contained:
        if elem not in arr_to_contain:
            cond = False
            break

    return cond


def buyer_personas_from_dataframes(dataframes, total_users, google_interests, metric):
    buyer_personas = []
    for i_age in range(len(dataframes["userAgeBracket"])):
        for i_gender in range(len(dataframes["userGender"])):
            for i_city in range(30):
                for i_device in range(len(dataframes["deviceCategory"])):
                    for i_type in range(len(dataframes["newVsReturning"])):
                        tot_percentage = dataframes["userAgeBracket"][metric][i_age] * \
                                         dataframes["userGender"][metric][i_gender] * \
                                         dataframes["city"][metric][i_city] * \
                                         dataframes["deviceCategory"][metric][i_device] * \
                                         dataframes["newVsReturning"][metric][i_type]
                        tot_users_buyer_persona = int(tot_percentage * total_users)

                        bp = BuyerPersona(number_users=tot_users_buyer_persona,
                                          age_range=dataframes["userAgeBracket"]["userAgeBracket"][i_age],
                                          gender=dataframes["userGender"]["userGender"][i_gender])
                        bp.geo_zone = dataframes["city"]["city"][i_city]
                        bp.device_category = dataframes["deviceCategory"]["deviceCategory"][i_device]
                        bp.type_of_user = dataframes["newVsReturning"]["newVsReturning"][i_type]
                        bp.google_interests = google_interests

                        buyer_personas.append(bp)

    return buyer_personas


def get_persona(personas):
    persona_output = BuyerPersona()
    for i, persona in enumerate(personas):
        persona_output += persona
        if i == 10:
            break
    return persona_output


def check_conditions_buyer_persona(user_id, access_data):
    threshold_likes = 0.2       #A threshold for facebook likes change
    threshold_users = 0.3       #A threshold for website users change
    access_token = access_data.ACCESS_TOKEN
    page_id = access_data.PAGE_ID
    client = access_data.client
    property_id = access_data.PROPERTY_ID

    #Check if there is an existing buyer persona for the current user id
    processing = db.buyerpersonas.find_one({"user_id": user_id, "processing": True})
    if processing is not None:
        return False        #If one is being processed, no need to create new one
    else:
        bp_coll = db.buyerpersonas.find_one({"user_id": user_id, "processing": False})
        if bp_coll is not None:
            bp = bp_coll["buyerpersonas"]
            keys = list(bp.keys())
            if "menu" not in keys or "facebook_likes" not in keys or "website_users" not in keys:
                return False

            else:
                old_facebook_likes = bp["facebook_likes"]
                old_website_users = bp["website_users"]
                old_menu = bp["menu"]

                try:
                    new_facebook_likes = get_total_likes(page_id, access_token)
                except Exception as e:
                    logging.exception(e)
                    new_facebook_likes = 0

                try:
                    new_website_users = get_total_users(client, property_id, start_date=30)
                except Exception as e:
                    logging.exception(e)
                    new_website_users = 0

                new_menu = get_menu_api(user_id)

                if new_menu != old_menu:
                    return True
                elif np.abs(new_website_users - old_website_users) / (old_website_users + 1) < threshold_users:
                    return True
                elif np.abs(new_facebook_likes - old_facebook_likes) / (old_facebook_likes + 1) < threshold_likes:
                    return True

                else:
                    return False

        else:
            return True


def get_interests_from_gmb(location, access_token, cutoff=0.75):
    url = f"{os.getenv('gmb_api_aigot')}GetLocationInformation?locationName={location}"

    response = get_json_response(url)
    facebook_interests = []

    if response is not None:

        type_of_business = response["primaryCategoryDisplayName"]
        secondary_category = response["secondaryCategoryDisplayName"]

        if secondary_category is not None:
            input_interests = [type_of_business] + secondary_category
        else:
            input_interests = [type_of_business]


        for interest in input_interests:

            facebook_interests_similar = find_facebook_interests(query=interest, access_token=access_token)
            facebook_interests += facebook_interests_similar

    return list_of_unique_dict(facebook_interests)


def enrich_facebook_interests(interests, access_token, len_suggested=5):
    """ This method takes the facebook interests and enriches them """
    output = []
    count = 0
    if len(interests) != 0:
        interests_name = [item["name_facebook_interest"] for item in interests]

        for i, name in enumerate(interests_name):
            suggested_interests = []

            if len(suggested_interests) != 0:
                output += suggested_interests[0]

            else:
                count += 1
                print(f"Run the pipeline for enriching interests. It seems that {name} is new.")
                output += find_facebook_interests(name, access_token)
                if count % 20 == 0:
                    time.sleep(60)

    for i in range(len(output)):
        output[i]["id_facebook_interest"] = int(output[i]["id_facebook_interest"])

    return list_of_unique_dict(output)


def same_type_interests(interests):
    output = []
    for interest in interests:
        if not isinstance(interest["topic_facebook_interest"], str):
            interest["topic_facebook_interest"] = str(interest["topic_facebook_interest"])
        if not isinstance(interest["name_facebook_interest"], str):
            interest["topic_facebook_interest"] = str(interest["topic_facebook_interest"])
        if not isinstance(interest["id_facebook_interest"], int):
            interest["id_facebook_interest"] = int(interest["id_facebook_interest"])

        output.append(interest)

    return output