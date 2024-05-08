import logging
import os
import random
import time
import pandas as pd
from hashlib import sha256

from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.api import FacebookAdsApi
from facebook_business.exceptions import FacebookError

from marketing import FACEBOOK_GOALS, db, API_VERSION
from marketing.utils import get_json_response

country = "IT"


def create_all_custom_lookalike_audiences(access_data, account_id):
    existing = db.audiences.find_one({"account_id": account_id})
    custom_audiences, lookalike_audiences = custom_lookalike_audience_base()
    df_custom = pd.DataFrame(custom_audiences)
    df_lookalike = pd.DataFrame(lookalike_audiences)

    existing_custom = existing.get("custom_audiences", [])
    df_existing_custom = pd.DataFrame(columns=df_custom.columns, data=existing_custom)
    existing_lookalike = existing.get("lookalike_audiences", [])
    df_existing_lookalike = pd.DataFrame(columns=df_lookalike.columns, data=existing_lookalike)

    cond_custom = df_custom["full_name"].isin(df_existing_custom["full_name"])
    df_custom[cond_custom] = df_existing_custom

    cond_lookalike = df_lookalike["full_name"].isin(df_existing_lookalike["full_name"])
    df_lookalike[cond_lookalike] = df_existing_lookalike

    error_custom = False
    for i, row in df_custom.iterrows():
        if row["id"] is None:
            try:
                custom_id = create_custom_audience(row, access_data)
                df_custom.loc[i, "id"] = custom_id
                print("creata custom audience")
                time.sleep(10)
            except FacebookError:
                logging.exception("")
                error_custom = True
                break
    db.audiences.update_one(
        {
            "account_id": account_id
        },
        {
            "$set": {
                "custom_audiences": df_custom.dropna(subset=["id"]).to_dict('records'),
                "error_custom_creation": error_custom,
                "last_update": 0
            }
        },
        upsert=True
    )
    print("database update")



def custom_lookalike_audience_base():
    retention_days = [10, 30, 60]
    # retention_days = [30]
    actions_website = ["ContactsPage", "DeliveryPage", "MenuPage", "Step2Booking",
                       "Step3Booking", "Step4Booking", "BookingPage", "HomePage"]
    actions_facebook = ["page_engaged", "page_visited", "page_post_interaction",
                        "page_cta_clicked", "page_or_post_save"]
    actions_instagram = ["ig_business_profile_all", "ig_business_profile_visit",
                         "ig_business_profile_engaged", "ig_business_profile_ad_saved"]
    ratio_list = [0.01, 0.03, 0.15]
    custom_audiences = []
    lookalike_audiences = []

    for day in retention_days:
        elem = {
            "full_name": f"Website tutti i visitatori, {day}GG",
            "name": "website tutti i visitatori",
            "retention_days": day,
            "event_name": "tutti i visitatori",
            "id": None,
            "number_weight": 0,
            "freshness_weight": 0
        }
        for goal in FACEBOOK_GOALS:
            elem[goal] = 0
        custom_audiences.append(elem)
    for action in actions_website:
        for day in retention_days:
            elem = {
                "full_name": f"Website {action}, {day}GG",
                "name": f"website {action.lower()}",
                "retention_days": day,
                "event_name": action,
                "id": None,
                "number_weight": 0,
                "freshness_weight": 0
            }
            for goal in FACEBOOK_GOALS:
                elem[goal] = 0
            custom_audiences.append(elem)
    for action in actions_facebook:
        for day in retention_days:
            elem = {
                "full_name": f"Pagina FB {action}, {day}GG",
                "name": f"pagina fb {action.lower()}",
                "retention_days": day,
                "event_name": action,
                "id": None,
                "number_weight": 0,
                "freshness_weight": 0
            }
            for goal in FACEBOOK_GOALS:
                elem[goal] = 0
            custom_audiences.append(elem)
    for action in actions_instagram:
        for day in retention_days:
            elem = {
                "full_name": f"Account IG {action}, {day}GG",
                "name": f"account ig {action.lower()}",
                "retention_days": day,
                "event_name": action,
                "id": None,
                "number_weight": 0,
                "freshness_weight": 0
            }
            for goal in FACEBOOK_GOALS:
                elem[goal] = 0
            custom_audiences.append(elem)

    for ca in custom_audiences:
        for ratio in ratio_list:
            full_name = f"Pubblico simile ({country}, {int(100 * ratio)}%) - {ca['full_name']}"
            elem = {
                "full_name": full_name,
                "origin_name": ca["full_name"],
                "origin_id": ca["id"],
                "ratio": ratio,
                "id": None,
                "number_weight": 0,
                "freshness_weight": 0
            }
            for goal in FACEBOOK_GOALS:
                elem[goal] = 0
            lookalike_audiences.append(elem)

    return custom_audiences, lookalike_audiences


def create_custom_audience(ca_data, access_data):
    rule = get_rule(ca_data, access_data)
    if rule is not None:
        params = {
            "name": ca_data["full_name"],
            "rule": str(rule),
            "retention_days": ca_data["retention_days"],
            "prefill": True
        }

        FacebookAdsApi.init(access_token=access_data["facebookAuthToken"], api_version=API_VERSION)
        custom_audience = AdAccount(access_data["facebookAdAccount"]).create_custom_audience(params=params)
        return custom_audience["id"]


def get_rule(ca_data, access_data):
    pixel_id = access_data.get("pixelId")
    page_id = access_data.get("facebookPageResourceIdentifier")
    account_ig = access_data.get("instagramAccountResourceIdentifier")
    event_source = None
    _filter = None

    if "website" in ca_data["name"]:
        if pixel_id is None:
            return None
        event_source = {"type": "pixel", "id": pixel_id}
        if "tutti i visitatori" == ca_data["event_name"]:
            _filter = {
                "field": "url",
                "operator": "i_contains",
                "value": ""
            }
        else:
            _filter = {
                "field": "event",
                "operator": "eq",
                "value": ca_data["event_name"]
            }

    elif "pagina fb" in ca_data["name"]:
        if page_id is None:
            return None
        event_source = {"type": "page", "id": page_id}
        _filter = {
            "field": "event",
            "operator": "eq",
            "value": ca_data["event_name"]
        }

    elif "account ig" in ca_data["name"]:
        if account_ig is None:
            return None
        event_source = {"type": "ig_business", "id": account_ig}
        _filter = {
            "field": "event",
            "operator": "eq",
            "value": ca_data["event_name"]
        }

    rule = {
        "event_sources": [event_source],
        "retention_seconds": int(ca_data["retention_days"] * 86400),
        "filter": {
            "operator": "and",
            "filters": [_filter]}
    }
    return {
        "inclusions":
            {
                "operator": "or",
                "rules": [rule]
            }
    }


def create_lookalike_audience(la_data, access_data):
    account_id = access_data["facebookAdAccount"]
    access_token = access_data["facebookAuthToken"]
    lookalike_spec = {
        "country": country,
        "origin": [
            {
                "id": la_data["origin_id"],
                "type": "custom_audience",
            }
        ],
        "ratio": la_data["ratio"],
        "type": "custom_ratio"
    }

    params = {
        "lookalike_spec": str(lookalike_spec),
        "name": la_data["full_name"],
        "subtype": "LOOKALIKE",
        "origin_audience_id": la_data["origin_id"]
    }
    FacebookAdsApi.init(access_token=access_token, api_version=API_VERSION)
    lookalike_audience = AdAccount(account_id).create_custom_audience(params=params)

    return lookalike_audience["id"]


def get_customer_data(user_id):
    url = f"https://{user_id}.themes.{os.getenv('BASE_URL_THEMES')}/api/customers"
    response = get_json_response(url)
    df_customers = pd.DataFrame(response)
    email_list = df_customers["email"].to_list()
    email_list_sha256 = [sha256(email.encode('utf-8')).hexdigest() for email in email_list]
    schema = "EMAIL_SHA256"
    return schema, email_list_sha256


def create_customer_file_custom_audience(access_data, user_id):
    access_token = access_data["facebookAuthToken"]
    account_id = access_data["facebookAdAccount"]
    FacebookAdsApi.init(access_token=access_token, api_version=API_VERSION)
    custom_audiences = AdAccount(account_id).get_custom_audiences(fields=["name"], params={"limit": 500})
    custom_audience = None
    for ca in custom_audiences:
        if ca["name"] == "Customer file custom audience":
            custom_audience = ca
            break
    if custom_audience is None:
        params = {
            "name": "Customer file custom audience",
            "subtype": "CUSTOM",
            "description": "Custom audience formata dalle email dei clienti",
            "customer_file_source": "USER_PROVIDED_ONLY"
        }
        custom_audience = AdAccount(account_id).create_custom_audience(params=params)

    schema, data = get_customer_data(user_id)
    session_id = random.randint(0, 2 ** 63 - 1)

    num_batch = 1 + (len(data) - 1) // 10000

    for i in range(0, num_batch):
        if i + 1 == num_batch:
            last_batch = True
        else:
            last_batch = False

        session = {
            "session_id": session_id,
            "batch_seq": i + 1,
            "last_batch_flag": last_batch,
        }

        params = {
            "session": session,
            "payload": {
                "schema": schema,
                "data": data
            }
        }
        custom_audience.create_user(params=params)
