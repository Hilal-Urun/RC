""" In this module there are some functions shared
among the project """
import json
import os
import time
import logging
from threading import Thread
import deepl
import numpy as np
import pandas as pd
import ssl
import urllib3
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.adobjects.adset import AdSet
from facebook_business.adobjects.campaign import Campaign
from facebook_business.api import FacebookAdsApi
from facebook_business.exceptions import FacebookError
from scipy.interpolate import interp1d
from scipy.optimize import curve_fit, brentq
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from datetime import datetime, timedelta
from marketing.shared import get_st_model
from marketing import db, tz, facebook_time_format, API_VERSION
from marketing.campaign.utils_campaign import get_targeting_buyerpersona
from marketing.data_from_user import get_radius_for_user, get_address, get_social_accounts

translator = deepl.Translator(os.getenv("DEEPL_AUTH_KEY"))
def ga_response_dataframe(response):
    row_list = []
    for report in response.get('reports', []):
        column_header = report.get('columnHeader', {})
        dimension_headers = column_header.get('dimensions', [])
        metric_headers = column_header.get('metricHeader', {}).get('metricHeaderEntries', [])
        for row in report.get('data', {}).get('rows', []):
            row_dict = {}
            dimensions = row.get('dimensions', [])
            date_range_values = row.get('metrics', [])
            for header, dimension in zip(dimension_headers, dimensions):
                row_dict[header] = dimension
            for i, values in enumerate(date_range_values):
                for metric, value in zip(metric_headers, values.get('values')):
                    if ',' in value or '.' in value:
                        row_dict[metric.get('name')] = float(value)
                    else:
                        row_dict[metric.get('name')] = int(value)
            row_list.append(row_dict)
    return pd.DataFrame(row_list)

def get_json_response(url):
    http = urllib3.PoolManager(cert_reqs='CERT_REQUIRED', ca_certs=ssl.get_default_verify_paths().openssl_cafile)
    response = http.request('GET', url)
    if response.status != 200:
        print(f"Error status code {response.status}.\n{url}")
        if response.status == 400:
            return None
    else:
        return response.data.decode('utf-8')

def insert_one_interest_id(collection, document):
    """ This function checks if the interest id in document is in the collection.
    If not the document is inserted, else is not """
    query = {"id_facebook_interest": document["id_facebook_interest"]}
    mydoc = collection.find(query)
    if len(list(mydoc)) == 0:
        collection.insert_one(document)


def list_of_unique_dict(arr_dict_1):
    new_arr = []

    for elem in arr_dict_1:
        if elem not in new_arr:
            new_arr.append(elem)

    return new_arr


def fit(t, A, tau):
    return A * (1 - np.exp(-t / tau))


def fit_data(df):
    min_elem = df[df.ne(0)].sort_values(by="spend").iloc[0]

    min_spend = min_elem["spend"]
    min_impressions = min_elem["impressions"]
    min_reach = min_elem["reach"]
    min_actions = min_elem["actions"]

    impressions_max = max(df["impressions"])
    reach_max = max(df["reach"])
    actions_max = max(df["actions"])

    tau_impressions = impressions_max * min_spend / min_impressions
    tau_reach = reach_max * min_spend / min_reach
    tau_actions = actions_max * min_spend / min_actions

    popt_spendimpres = curve_fit(fit, df['spend'].values, df['impressions'].values,
                                 p0=[max(df['impressions']), tau_impressions])[0]
    popt_spendreach = curve_fit(fit, df['spend'].values, df['reach'].values,
                                p0=[max(df['reach']), tau_reach])[0]
    popt_spendactions = curve_fit(fit, df['spend'].values, df['actions'].values,
                                  p0=[max(df['spend']), tau_actions])[0]

    return popt_spendimpres, popt_spendreach, popt_spendactions


def is_optimized(campaign_id, access_token):
    FacebookAdsApi.init(access_token=access_token, api_version=API_VERSION)
    campaign = Campaign(campaign_id)

    name = campaign.api_get(fields=["name"])["name"]

    if "ottimizzata" in name:
        return True
    else:
        return False


def get_categories(page_id_for_gmb):
    url = f"{os.getenv('gmb_api_aigot')}GetLocationInformation?locationName={page_id_for_gmb}"
    response = get_json_response(url)

    if response is not None:
        type_of_business = response["primaryCategoryDisplaName"]
        secondary_category = response["secondaryCategoryDisplayName"]

        output = {
            "primary_category": type_of_business,
            "secondary_categort": secondary_category
        }
        return output

    else:
        return {}


def min_freq_func(x, func, estimate_mau):
    return func(x) * 14 - estimate_mau


def frequency_zeros(x, func_impres, func_reach, estimate_mau, zero=0):
    return func_impres(x) * 14 / (min(func_reach(x) * 14, estimate_mau)) - zero


def find_spend(estimate_mau, df):
    f_reach = interp1d(df["spend"], df["reach"])
    spend = brentq(lambda x: f_reach(x) - estimate_mau / 10, min(df["spend"]) + 1, max(df["spend"]) - 1)
    return max(spend, 300)


def get_image_in_campaign(campaign_id, access_token):
    FacebookAdsApi.init(access_token=access_token, api_version=API_VERSION)
    ads = Campaign(campaign_id).get_ads()
    if len(ads) == 0:
        print("There isn't any ad in the campaign")
        return ""
    else:
        ad = ads[0]
        creatives = ad.get_ad_creatives(fields=["object_story_spec"])
        if len(creatives) == 0:
            print("There is no creative in this ad")
            return ""
        else:
            creative = creatives[0]
            try:
                picture = creative["object_story_spec"]["link_data"]["picture"]
            except FacebookError:
                logging.exception("")
                picture = ""
            except Exception:
                logging.exception("")
                picture = ""

            return picture


def change_reach_list(reach_list, time_ranges):
    new_output = []
    for elem in time_ranges:
        exists = False
        for data in reach_list:
            if data["date_start"] == elem["since"]:
                exists = True
                new_output.append(data)

        if not exists:
            new_output.append(
                {
                    "reach": 0,
                    "date_start": elem["since"],
                    "date_stop": elem["until"]
                })

    return new_output


def check_if_broad_required_thread(buyer_persona, user_id, goal, access_token):
    campaign_id = ""
    address = get_address(user_id)
    account_id = get_social_accounts(user_id)["facebookAdAccount"]
    try:
        print("inizio test")
        FacebookAdsApi.init(access_token=access_token, api_version=API_VERSION)
        params = {
            "name": "Test campaign for checking broad",
            "objective": "BRAND_AWARENESS",
            "special_ad_categories": [],
            "status": "PAUSED"
        }
        targeting = get_targeting_buyerpersona(buyer_persona)
        campaign_id = AdAccount(account_id).create_campaign(params=params)["id"]
        params_spec = {
            "status": "PAUSED",
            "name": "Test adset for checking broad | spec",
            "campaign_id": campaign_id,
            "daily_budget": 1000,
            "billing_event": "IMPRESSIONS",
            "optimization_goal": "AD_RECALL_LIFT",
            "bid_strategy": "LOWEST_COST_WITHOUT_CAP",
            "start_time": int(time.time()),
            "end_time": int(time.time()) + 7 * 86400,
            "targeting": {
                "geo_locations": {
                    "countries": [
                        "IT"
                    ],
                    "location_types": [
                        "home",
                        "recent"
                    ]
                },
                **targeting
            }
        }
        time.sleep(60)
        adset_id = AdAccount(account_id).create_ad_set(params=params_spec)["id"]
        print("fatto primo adset")
        try:
            mau_spec_italy = AdSet(adset_id).get_delivery_estimate()[0]["estimate_mau_lower_bound"]
        except Exception:
            logging.exception("")
            mau_spec_italy = 0

        params_broad_italy = {
            "status": "PAUSED",
            "name": "Test adset for checking broad | Italy",
            "campaign_id": campaign_id,
            "daily_budget": 1000,
            "billing_event": "IMPRESSIONS",
            "optimization_goal": "AD_RECALL_LIFT",
            "bid_strategy": "LOWEST_COST_WITHOUT_CAP",
            "start_time": int(time.time()),
            "end_time": int(time.time()) + 7 * 86400,
            "targeting": {
                "geo_locations": {
                    "countries": [
                        "IT"
                    ],
                    "location_types": [
                        "home",
                        "recent"
                    ]
                },
                "age_min": targeting["age_min"],
                "age_max": targeting["age_max"],
            }
        }
        time.sleep(60)
        adset_broad_id = AdAccount(account_id).create_ad_set(params=params_broad_italy)["id"]
        print("fatto secondo adset")
        try:
            mau_broad_italy = AdSet(adset_broad_id).get_delivery_estimate()[0]["estimate_mau_lower_bound"]
        except Exception:
            logging.exception("")
            mau_broad_italy = 1

        r = mau_spec_italy / mau_broad_italy

        if r <= 0.2:
            db.broad_required.update_one(
                {
                    "user_id": user_id,
                    "buyer_persona": buyer_persona,
                    "processing": True
                },
                {
                    "$set": {
                        "processing": False,
                        "is_required": True
                    }
                }
            )
        else:
            try:
                radius = get_radius_for_user(user_id, goal)
            except Exception:
                logging.exception("")
                radius = 5

            geo_locations = {
                "custom_locations": [
                    {
                        "address_string": address,
                        "distance_unit": "kilometer",
                        "name": address,
                        "radius": radius,
                    }
                ],
                "location_types": [
                    "home",
                    "recent"
                ]
            }

            params_spec_local = {
                "status": "PAUSED",
                "name": "Test adset for checking broad | local",
                "campaign_id": campaign_id,
                "daily_budget": 1000,
                "billing_event": "IMPRESSIONS",
                "optimization_goal": "AD_RECALL_LIFT",
                "bid_strategy": "LOWEST_COST_WITHOUT_CAP",
                "start_time": int(time.time()),
                "end_time": int(time.time()) + 7 * 86400,
                "targeting": {
                    "geo_locations": geo_locations,
                    **targeting
                }
            }
            time.sleep(60)
            adset_local_id = AdAccount(account_id).create_ad_set(params=params_spec_local)["id"]
            try:
                mau_local = AdSet(adset_local_id).get_delivery_estimate()[0]["estimate_mau_lower_bound"]
            except Exception:
                logging.exception("")
                mau_local = 0

            if mau_local < 5000:
                db.broad_required.update_one(
                    {
                        "user_id": user_id,
                        "buyer_persona": buyer_persona,
                        "processing": True
                    },
                    {
                        "$set": {
                            "processing": False,
                            "is_required": True
                        }
                    }
                )
            else:
                db.broad_required.update_one(
                    {
                        "user_id": user_id,
                        "buyer_persona": buyer_persona,
                        "processing": True
                    },
                    {
                        "$set": {
                            "processing": False,
                            "is_required": False
                        }
                    }
                )
    except FacebookError:
        logging.exception("")
        db.broad_required.delete_many(
            {
                "account_id": account_id,
                "buyer_persona": buyer_persona
            }
        )
    except Exception:
        logging.exception("")
        db.broad_required.delete_many(
            {
                "user_id": user_id,
                "buyer_persona": buyer_persona
            }
        )
    finally:
        if campaign_id:
            Campaign(campaign_id).api_delete()


def check_if_broad_required(buyer_persona, user_id, goal, access_token):
    if buyer_persona == "tourist":
        return False
    is_required = db.broad_required.find_one(
        {
            "buyer_persona": buyer_persona,
            "account_id": user_id,
            "date": {"$gt": int(time.time() - 28 * 86400)}
        }
    )
    if is_required is not None:
        if is_required["processing"] is True:
            return True
        else:
            return is_required["is_required"]

    else:
        db.broad_required.insert_one(
            {
                "user_id": user_id,
                "buyer_persona": buyer_persona,
                "processing": True
            }
        )
        Thread(target=check_if_broad_required_thread, args=(buyer_persona, user_id,
                                                            goal, access_token)).start()
        return True


def get_lat_long(address_func):
    url = 'https://maps.googleapis.com/maps/api/place/findplacefromtext/json?input=' + address_func + \
          '&inputtype=textquery&fields=formatted_address,name,rating,opening_hours,geometry&key=' \
          + os.getenv("google_key")

    long_lat_info = get_json_response(url)
    latitude_func = long_lat_info['candidates'][0]['geometry']['location']['lat']
    longitude_func = long_lat_info['candidates'][0]['geometry']['location']['lng']

    return latitude_func, longitude_func


def delete_campaigns(campaign_id_list, access_token):
    for campaign_id in campaign_id_list:
        time.sleep(120)
        FacebookAdsApi.init(access_token=access_token, api_version=API_VERSION)
        Campaign(campaign_id).api_delete()


def change_date(date: datetime):
    year = date.strftime("%Y")
    month = date.month
    months = ["GEN", "FEB", "MAR", "APR", "MAG", "GIU",
              "LUG", "AGO", "SET", "OTT", "NOV", "DIC"]
    month = months[month - 1]
    day = date.strftime("%d")
    weekday = date.weekday()
    weekdays = ["Lun", "Mar", "Mer", "Gio", "Ven", "Sab", "Dom"]
    weekday = weekdays[weekday]

    return f"{weekday}, {day} {month} {year}"


def translate_google_interests(google_interests):
    if len(google_interests) != 0:
        interests_db = db.google_interests.find({
            "$or": [{"name_google_interest": google_interest}
                    for google_interest in google_interests]
        })

        return [interest["name_google_interest_translated"] for interest in interests_db]
    else:
        return []


def add_validator_to_collection(mongo_collection):
    old_validator = mongo_collection.options().get("validator")
    with open("suggestedCampaignSchema.json") as f:
        new_validator = json.load(f)
    if new_validator == old_validator:
        pass
    else:
        pass


def remove_deleted_campaigns(account_id, access_token):
    now = int(time.time())
    FacebookAdsApi.init(access_token=access_token, api_version=API_VERSION)
    campaigns_in_running = list(db.running_campaigns.find({"account_id": account_id}))
    campaigns_in_ended = list(db.ended_campaigns.find({"account_id": account_id}))
    campaigns_fb = []

    for campaign in campaigns_in_running:
        if campaign.get("last_check", 0) < now - 86400:
            campaigns_fb = not campaigns_fb and [cmp["id"] for cmp in AdAccount(account_id).get_campaigns()] \
                           or campaigns_fb
            if campaign["campaign_id"] not in campaigns_fb:
                db.running_campaigns.delete_one({"_id": campaign["_id"]})
            else:
                db.running_campaigns.update_one(
                    {
                        "_id": campaign["_id"]
                    },
                    {
                        "$set": {"last_check": now}
                    }
                )
        else:
            db.running_campaigns.update_one(
                {
                    "_id": campaign["_id"]
                },
                {
                    "$set": {"last_check": now}
                }
            )

    for campaign in campaigns_in_ended:
        if campaign.get("last_check", 0) < now - 86400:
            campaigns_fb = not campaigns_fb and [cmp["id"] for cmp in AdAccount(account_id).get_campaigns()] \
                           or campaigns_fb
            if campaign["campaign_id"] not in campaigns_fb:
                db.ended_campaigns.delete_one({"_id": campaign["_id"]})
            else:
                db.ended_campaigns.update_one(
                    {
                        "_id": campaign["_id"]
                    },
                    {
                        "$set": {"last_check": now}
                    }
                )
        else:
            db.ended_campaigns.update_one(
                {
                    "_id": campaign["_id"]
                },
                {
                    "$set": {"last_check": now}
                }
            )


def array_to_lunch_dinner(_array):
    lunch_hour = 1300
    dinner_hour = 2000
    if len(_array) == 0:
        return []
    new_array = sorted(_array)
    if len(new_array) == 2:
        if new_array[1] > lunch_hour > new_array[0]:
            return ["pranzo"]
        elif new_array[1] > dinner_hour > new_array[0]:
            return ["cena"]
    if len(new_array) == 4:
        return ["pranzo", "cena"]
    else:
        return []


def change_input_for_ad_copy(data):
    my_out = {
        "lunedì": [],
        "martedì": [],
        "mercoledì": [],
        "giovedì": [],
        "venerdì": [],
        "sabato": [],
        "domenica": []
    }

    for item in data:
        if "MONDAY" in item.values():
            close_time = item.get("closeTime")
            open_time = item.get("openTime")
            if open_time is not None:
                open_time_to_append = open_time["hours"] * 100 + (open_time["minutes"] or 0)
                my_out["lunedì"].append(open_time_to_append)

            if close_time is not None:
                close_time_to_append = close_time["hours"] * 100 + (close_time["minutes"] or 0)
                my_out["lunedì"].append(close_time_to_append)

        elif "TUESDAY" in item.values():
            close_time = item.get("closeTime")
            open_time = item.get("openTime")
            if open_time is not None:
                open_time_to_append = open_time["hours"] * 100 + (open_time["minutes"] or 0)
                my_out["martedì"].append(open_time_to_append)

            if close_time is not None:
                close_time_to_append = close_time["hours"] * 100 + (close_time["minutes"] or 0)
                my_out["martedì"].append(close_time_to_append)

        elif "WEDNESDAY" in item.values():
            close_time = item.get("closeTime")
            open_time = item.get("openTime")
            if open_time is not None:
                open_time_to_append = open_time["hours"] * 100 + (open_time["minutes"] or 0)
                my_out["mercoledì"].append(open_time_to_append)

            if close_time is not None:
                close_time_to_append = close_time["hours"] * 100 + (close_time["minutes"] or 0)
                my_out["mercoledì"].append(close_time_to_append)

        elif "THURSDAY" in item.values():
            close_time = item.get("closeTime")
            open_time = item.get("openTime")
            if open_time is not None:
                open_time_to_append = open_time["hours"] * 100 + (open_time["minutes"] or 0)
                my_out["giovedì"].append(open_time_to_append)

            if close_time is not None:
                close_time_to_append = close_time["hours"] * 100 + (close_time["minutes"] or 0)
                my_out["giovedì"].append(close_time_to_append)

        elif "FRIDAY" in item.values():
            close_time = item.get("closeTime")
            open_time = item.get("openTime")
            if open_time is not None:
                open_time_to_append = open_time["hours"] * 100 + (open_time["minutes"] or 0)
                my_out["venerdì"].append(open_time_to_append)

            if close_time is not None:
                close_time_to_append = close_time["hours"] * 100 + (close_time["minutes"] or 0)
                my_out["venerdì"].append(close_time_to_append)

        elif "SATURDAY" in item.values():
            close_time = item.get("closeTime")
            open_time = item.get("openTime")
            if open_time is not None:
                open_time_to_append = open_time["hours"] * 100 + (open_time["minutes"] or 0)
                my_out["sabato"].append(open_time_to_append)

            if close_time is not None:
                close_time_to_append = close_time["hours"] * 100 + (close_time["minutes"] or 0)
                my_out["sabato"].append(close_time_to_append)

        elif "SUNDAY" in item.values():
            close_time = item.get("closeTime")
            open_time = item.get("openTime")
            if open_time is not None:
                open_time_to_append = open_time["hours"] * 100 + (open_time["minutes"] or 0)
                my_out["domenica"].append(open_time_to_append)

            if close_time is not None:
                close_time_to_append = close_time["hours"] * 100 + (close_time["minutes"] or 0)
                my_out["domenica"].append(close_time_to_append)

    for key, val in my_out.items():
        my_out[key] = array_to_lunch_dinner(val)

    return my_out


def get_best_interests_indexes(interests):
    if len(interests) <= 3:
        return [i for i in range(len(interests))]

    interests_translated = []
    for interest in interests:
        interests_translated.append(translator.translate_text(interest, target_lang="EN-US").text)

    encoded = get_st_model().encode(interests_translated)

    pca = PCA(n_components=2)
    principal_components = pca.fit_transform(encoded)
    df = pd.DataFrame(data=principal_components,
                      columns=['pc1', 'pc2'])

    kmeans_kwargs = {
        "init": "random",
        "n_init": 10,
        "max_iter": 300,
        "random_state": 42,
    }

    kmeans = KMeans(n_clusters=min(3, len(interests)), **kmeans_kwargs)
    kmeans.fit(df)

    centers = kmeans.cluster_centers_
    best_indexes = []
    for centroid in centers:
        distances = []
        for _, row in df.iterrows():
            point = np.array([row["pc1"], row["pc2"]])
            center = np.array(centroid)
            dist = np.sqrt(np.sum((point - center) ** 2))
            distances.append(dist)

        best_indexes.append(distances.index(min(distances)))

    return best_indexes


def change_sentiment_analysis_output(sentiment_analysis_input):
    count = {
        "❤ Innamorati,#FC6371": sentiment_analysis_input["comments_positive_counts"],
        "👍 Mi Piace, #00B27A": sentiment_analysis_input["comments_neutral_counts"],
        "😡 Arrabbiati,#114653": sentiment_analysis_input["comments_negative_counts"]
    }
    # count = {
    #     "👍 Mi Piace, #00B27A": 100,
    #     "❤ Innamorati, #FC6371": 200,
    #     "😡 Arrabbiati, #114653": 300
    # }

    data = []
    for key, val in count.items():
        data.append(
            {
                "name": key.split(",")[0],
                "value": val,
                "fill": key.split(",")[1]
            })

    return data


def change_goal_in_goalpersona(persona_and_goal):
    goal = persona_and_goal[0]
    persona = persona_and_goal[1]

    dict_goal = {
        "marchio": "brand_awareness",
        "interazioni": "interactions",
        "delivery": "delivery",
        "prenotazioni": "reservation",
        "visualiz menu": "traffic_online",
        "visite al locale": "traffic_offline"
    }

    return [dict_goal[goal], persona]

def bp_to_prompt(buyer_persona):
    output_dict = {
        "VEGAN": "ai vegani: un vegano non mangia carne, pesce, uova, latte e i suoi derivati, miele.",
        "VEGETARIAN": "ai vegetariani: i vegetariani generalmente non mangiano carne e pesce. "
                      "Alcuni potrebbero evitare alcuni tipi di derivati di origine animale.",
        "GRADUATING": "ai laureandi: studenti che stanno per sostenere l’esame di laurea o"
                      " che sono iscritti all’ultimo anno di università.",
        "JUST MARRIED": "ai novelli sposi: persone che si sono sposate negli ultimi 6 mesi.",
        "SAVER": "ai risparmiatori: utenti interessati al risparmio tramite sconti e coupon.",
        "SINGLE": "ai single: persone single, divorziate o separate.",
        "COUPLES": "alle coppie: persone conviventi, impegnate in una relazione o sposate.",
        "ANNIVERSARY": "alle persone che festeggeranno presto il loro anniversario.",
        "NONRESIDENTIAL": "ai fuorisede: persone che studiano o lavorano lontano dalla loro città di origine.",
        "COMMUTER": "ai pendolari: persone che quotidianamente si spostano in un’altra città per raggiungere "
                    "il loro luogo di studio o lavoro.",
        "BACK FROM HOLIDAY": "alle persone che sono di ritorno dalle ferie da meno di 2 settimane.",
        "JOB HUNTER": "alle persone che stanno attivamente cercando lavoro.",
        "BIRTHDAY": "alle persone che a breve compiranno gli anni.",
        "TOURIST": "ai turisti",
        "PRIMARY": "al cliente tipo del ristorante"
    }
    return output_dict[buyer_persona]


def goal_to_prompt(goal):
    output_dict = {
        "MARCHIO": "per aumentare la notorietà",
        "INTERAZIONI": "per incrementare le interazioni",
        "DELIVERY": "per promuovere il servizio di consegna",
        "PRENOTAZIONI": "per promuovere le prenotazioni",
        "VISUALIZZAZIONE MENU": "per promuovere la visualizzazione del menu",
        "VISITE AL LOCALE": "per incentivare le visite al locale",
        "RICERCA DI PERSONALE": "per la ricerca di personale"
    }
    return output_dict[goal]


def goal_to_prompt_social_media(goal):
    output_dict = {
        "branding":"per aumentare la fama",
        "reservation":"per promuovere le prenotazioni",
        "themes":"per occasioni speciali",
        "promotion":"per le promozioni",
        "delivey":"per promuovere il servizio di consegna",
        "menu":"per promuovere il menù",
        "NOTORIETÀ": "per aumentare la fama",
        "PRENOTAZIONI": "per promuovere le prenotazioni",
        "GIORNATE A TEMA": "per occasioni speciali",
        "PROMOZIONI": "per le promozioni",
        "DELIVERY": "per promuovere il servizio di consegna",
        "MENU": "per promuovere il menù"
    }
    return output_dict[goal]


def get_daily_budget_duration(campaign_id, access_token):
    FacebookAdsApi.init(access_token=access_token, api_version=API_VERSION)
    adset_list = Campaign(campaign_id).get_ad_sets(fields=["daily_budget", "start_time", "end_time"])
    daily_budget = int(Campaign(campaign_id).api_get(fields=["daily_budget"]).get("daily_budget", 0))
    duration_list = []
    count = 0
    while True:
        adset = next(adset_list, None)
        if adset is None:
            break
        daily_budget += int(adset.get("daily_budget", 0))
        start_time = datetime.strptime(adset["start_time"], facebook_time_format)
        end_time = datetime.strptime(adset.get("end_time"), facebook_time_format)

        duration_list.append((end_time - start_time).days)
        count += 1

    duration = max(duration_list)

    return daily_budget, duration


def delete_old_suggested_campaigns(user_id, access_token, old_days=7):
    if db.deletedcampaigns_check.find_one({"user_id": user_id, "processing": True}) is None:
        return None

    if db.deletedcampaigns_check.find_one({"user_id": user_id, "date": {"$gt": int(time.time() - 3600)}}) is None:
        return None

    db.deletedcampaigns_check.update_one(
        {
            "user_id": user_id
        },
        {
            "$set": {
                "processing": True,
                "date": int(time.time())
            }
        }
    )
    account_id = get_social_accounts(user_id)["facebookAdAccount"]
    FacebookAdsApi.init(access_token=access_token, api_version=API_VERSION)
    today = datetime.now(tz=tz)
    campaign_list = AdAccount(account_id).get_campaigns(fields=["name"])
    suggested_campaigns = []
    for campaign in campaign_list:
        if "suggerita" in campaign["name"]:
            suggested_campaigns.append(campaign)

    for campaign in suggested_campaigns:
        adset_list = campaign.get_ad_sets(fields=["start_time"])
        if len(adset_list) == 0:
            campaign.api_delete()
            continue
        start_time = adset_list[0]["start_time"]
        start_time_datetime = datetime.strptime(start_time, facebook_time_format)

        if start_time_datetime + timedelta(days=old_days) <= today:
            try:
                print("cancellata campagna con delete_old_suggested_campaigns")
                campaign.api_delete()
            except Exception:
                logging.exception("")

    db.deletedcampaigns_check.update_one(
        {
            "user_id": user_id
        },
        {
            "$set": {
                "processing": False,
                "date": int(time.time())
            }
        }
    )


def get_campaigns(account_id, access_token, string_in_name=None):
    FacebookAdsApi.init(access_token=access_token, api_version=API_VERSION)
    campaigns_list = list(AdAccount(account_id).get_campaigns(fields=["name"]))
    if string_in_name is not None:
        output = []
        for campaign in campaigns_list:
            if string_in_name in campaign["name"]:
                output.append(campaign)
        return output
    else:
        return campaigns_list


def get_similar_restaurants(user_id, user_list):
    location = get_social_accounts(user_id).get("gmbLocationResourceIdentifier")
    if location is None:
        return []
    target_category = get_categories(location)["primary_category"]

    matching_restaurants = []
    for user in user_list:
        location_user = get_social_accounts(user).get("gmbLocationResourceIdentifier")
        if location_user is None:
            continue
        category = get_categories(location_user)["primary_category"]
        if category == target_category:
            matching_restaurants.append(user)

    return matching_restaurants


def get_start_end_date(campaign_id, access_token) -> tuple:
    FacebookAdsApi.init(access_token=access_token, api_version=API_VERSION)
    adset_list = Campaign(campaign_id).get_ad_sets(fields=["start_time", "end_time"])
    for adset in adset_list:
        start_time = adset["start_time"]
        end_time = adset["end_time"]
        return start_time, end_time


def last_day(month, year):
    year = int(year)
    last_days = {
        "01": 31,
        "02": 28,
        "03": 31,
        "04": 30,
        "05": 31,
        "06": 30,
        "07": 31,
        "08": 31,
        "09": 30,
        "10": 31,
        "11": 30,
        "12": 31
    }
    if month == "02":
        return last_days["02"] + int(((year % 4 == 0) & (year % 100 != 0)) or (year % 400 == 0))

    return last_days.get(month, 0)


def get_campaign_data(campaign_id):
    if campaign_id is None:
        return {
            "image": None,
            "goal": None
        }
    if not isinstance(campaign_id, str):
        campaign_id = str(campaign_id)
    campaign = db.running_campaigns.find_one({"campaign_id": campaign_id}) or \
               db.ended_campaigns.find_one({"campaign_id": campaign_id}) or {}

    return {
        "image": campaign.get("image"),
        "goal": campaign.get("goal")
    }


def data_for_running_campaigns(data, campaign_id):
    if campaign_id:
        access_token = data["access_token"]
        FacebookAdsApi.init(access_token=access_token, api_version=API_VERSION)
        targeting = {}
        adset_list = Campaign(campaign_id).get_ad_sets(fields=["name", "targeting"])
        for adset in adset_list:
            if "general_audience" in adset["name"]:
                targeting = adset["targeting"].export_all_data()
    else:
        targeting = None

    start_time = data["start_time"]
    end_time = data["end_time"]
    starting_date = change_date(datetime.strptime(start_time, facebook_time_format))
    ending_date = change_date(datetime.strptime(end_time, facebook_time_format))
    hour = datetime.strptime(start_time, facebook_time_format).strftime("%H:%M:%S")

    running_campaigns_data = {
        "user_id": data["user_id"],
        "account_id": data["account_id"],
        "campaign_id": campaign_id,
        "name": f"Campagna {data['goal']}",
        "goal": data["goal"],
        "start_time": start_time,
        "end_time": end_time,
        "hour": hour,
        "startingDate": starting_date,
        "endingDate": ending_date,
        "copy": data["copy"],
        "budget": data["budget"],
        "results": {},
        "insights": {},
        "image": data["image"],
        "date": int(time.time()),
        "processing": False,
        "targeting": targeting
    }

    return running_campaigns_data
