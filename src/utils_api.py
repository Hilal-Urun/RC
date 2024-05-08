import logging
from datetime import datetime
import time
from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.campaign import Campaign
from facebook_business.exceptions import FacebookError
import requests
from marketing import facebook_time_format, db, API_VERSION
from marketing.buyer_persona import get_primary_secondary_buyer_persona
from marketing.content_optimization.ad_optimization import AdCopyPersonas
from marketing.campaign.creation import create_complete_campaign_broad_adset, create_complete_campaign, \
    create_campaign_adset_existing_data, create_campaign_adset
from marketing.campaign.suggested import best_campaign
from marketing.campaign.optimization import optimize_campaign
from marketing.data_from_user import get_social_accounts
from marketing.social_media.social_media_copy_new import SocialMediaCopy
from marketing.utils import change_date, get_campaigns
from marketing.update_databases import update_collections, remove_collections_processing_true
from marketing.custom_audience.create_custom_audience import create_all_custom_lookalike_audiences, \
    create_customer_file_custom_audience
from marketing.campaign.results import update_estimated_results


def create_social_media_copy_all_goals(user_id, locations, goals_list):
    for goal in goals_list:
        try:
            result = SocialMediaCopy(goal, locations, user_id)
            complete_text = result.complete_text(n=12)
            if len(complete_text) >= 4:
                db.social_media_copy_marketing.update_one(
                    {
                        "user_id": user_id,
                        "goal": goal,
                        "processing": True
                    },
                    {
                        "$set": {
                            "date": int(time.time()),
                            "complete_text": complete_text,
                            "processing": False
                        }
                    }
                )
            else:
                db.social_media_copy_marketing.delete_one(
                    {
                        "user_id": user_id,
                        "goal": goal
                    }
                )
        except Exception as e:
            logging.exception(e)

    db.social_media_copy_marketing.update_many(
        {
            "user_id": user_id,
            "processing": True
        },
        {
            "$set": {
                "processing": False
            }
        }
    )


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


def create_ad_copy_personas_all_goals(user_id, locations, persona_goal_list):
    for buyer_persona, goal in persona_goal_list:
        try:
            result = AdCopyPersonas(buyer_persona, goal, locations, user_id)
            complete_text = result.complete_text(n=12)
            if len(complete_text) >= 4:
                db.adcopy_marketing.update_one(
                    {
                        "user_id": user_id,
                        "buyer_persona": buyer_persona,
                        "goal": goal,
                        "processing": True
                    },
                    {
                        "$set": {
                            "date": int(time.time()),
                            "complete_text": complete_text,
                            "processing": False
                        }
                    }
                )
            else:
                db.adcopy_marketing.delete_one(
                    {
                        "user_id": user_id,
                        "buyer_persona": buyer_persona,
                        "goal": goal
                    }
                )
        except Exception as e:
            logging.exception(e)

    db.adcopy_marketing.update_many(
        {
            "user_id": user_id,
            "processing": True
        },
        {
            "$set": {
                "processing": False
            }
        }
    )


def get_json_response(url):
    """ This function returns a json response for an API call """

    response = requests.get(url, data={})
    if response.status_code != 200:
        print(f"Error status code {response.status_code}.\n{url}")

        if response.status_code == 400:
            return None
    else:
        return response.json()


def buyer_persona_thread(country, user_id, access_data):
    try:
        buyerpersonas = get_primary_secondary_buyer_persona(access_data=access_data, country=country)
        db.buyerpersonas.update_one(
            {
                "user_id": user_id,
                "processing": True
            },
            {
                "$set": {
                    "processing": False,
                    "date": int(time.time()),
                    "buyerpersonas": buyerpersonas
                }
            },
        upsert=True)
    except FacebookError as fb:
        logging.exception(str(fb) + "Facebook error exception")
        db.buyerpersonas.delete_many({"user_id": user_id})
    except Exception as e:
        logging.exception(str(e) + "generic error ")
        db.buyerpersonas.delete_many({"user_id": user_id})


def data_for_running_campaigns(data, campaign_id):
    access_token = data["access_token"]
    FacebookAdsApi.init(access_token=access_token, api_version=API_VERSION)
    targeting = {}
    adset_list = Campaign(campaign_id).get_ad_sets(fields=["name", "targeting"])
    for adset in adset_list:
        if "general_audience" in adset["name"]:
            targeting["age_min"] = adset["targeting"]["age_min"]
            targeting["age_max"] = adset["targeting"]["age_max"]
            targeting["flexible_spec"] = adset["targeting"]["flexible_spec"]

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
        "processing": False
    }

    return running_campaigns_data


def create_campaign_thread(data, broad_required, mongo_campaign_id):

    if broad_required:
        campaign_id = create_complete_campaign_broad_adset(**data)
    else:
        campaign_id = create_complete_campaign(**data)

    db.running_campaigns.update_one(
        {
            "_id": mongo_campaign_id
        },
        {
            "$set": data_for_running_campaigns(data, campaign_id)
        }
    )
    db.used_copies.insert_one(
        {
            "copy": data["copy"],
            "goal": data["goal"],
            "persona": data["buyer_persona_type"],
            "type": "ad_copy",
            "restaurant_id": data["user_id"],
            "add_date": int(time.time())
        }
    )
    update_estimated_results(db.running_campaigns.find({"_id": mongo_campaign_id}), data["access_token"])
    print("finito create_campaign_thread")


def create_suggested_campaign_thread(user_id, access_token, goals):
    account_id = get_social_accounts(user_id)["facebookAdAccount"]
    existing_campaigns = get_campaigns(account_id, access_token)
    for goal in goals:
        campaign_id = ""
        try:
            for cmp in existing_campaigns:
                if f"{goal} suggerita" in cmp["name"] or f"{goal} per suggerite" in cmp["name"]:
                    cmp.api_delete()
            campaign_data = best_campaign(user_id, goal)
            if campaign_data is not None:
                is_old = True
                campaign_id = create_campaign_adset_existing_data(user_id, access_token, campaign_data, goal)
            else:
                is_old = False
                campaign_id = create_campaign_adset(user_id, access_token, goal)
                optimize_campaign(campaign_id, access_token, account_id, user_id)

            update_collections(goal, campaign_id, user_id, account_id, access_token, is_old)
            time.sleep(60)
            Campaign(campaign_id).api_update(params={"name": f"Campagna {goal} suggerita"})

        except Exception as e:
            logging.exception(e)
            remove_collections_processing_true(user_id, goal)
            if campaign_id:
                print("campagna cancellata in create_suggested_campaign")
                Campaign(campaign_id).api_delete()
        else:
            time.sleep(60)


def create_custom_audience_thread(data):
    try:
        user_id = data["user_id"]
        social_accounts = get_social_accounts(user_id)
        account_id = social_accounts["facebookAdAccount"]
        social_accounts["facebookAuthToken"] = data["access_token"]
        existing = db.audiences.find_one({"account_id": account_id})

        # if there is something in the database and is processing return immediately and doesn't do anything
        if existing is not None and existing.get("processing", False):
            return True
        # if there is something in the database and there wasn't any error
        # noinspection PyUnresolvedReferences
        if existing is not None and not existing.get("error_custom", True) and not existing.get("error_lookalike",
                                                                                                True):
            return True

        # if there is something in the database and is not processing it creates again everything (there was an error)
        if existing is not None and not existing.get("processing", False):
            db.audiences.update_one(
                {
                    "account_id": account_id
                },
                {
                    "$set": {
                        "processing": True
                    }
                }
            )

        # if it doesn't exist it adds it to database
        if existing is None:
            db.audiences.insert_one(
                {
                    "account_id": account_id,
                    "processing": True
                }
            )

        # now we create everything
        try:
            create_all_custom_lookalike_audiences(social_accounts, account_id)
            create_customer_file_custom_audience(social_accounts, user_id)
            db.audiences.update_one(
                {
                    "account_id": account_id
                },
                {
                    "$set": {
                        "processing": False
                    }
                }
            )
            return True
        except Exception as e:
            logging.exception(e)
            return False
    except Exception as e:
        logging.exception(e)
        return False

def create_social_media_copy_all_goals(user_id, locations, goals_list):
    for goal in goals_list:
        try:
            result = SocialMediaCopy(goal, locations, user_id)
            complete_text = result.complete_text(n=12)
            if len(complete_text) >= 4:
                db.social_media_copy_marketing.update_one(
                    {
                        "user_id": user_id,
                        "goal": goal,
                        "processing": True
                    },
                    {
                        "$set": {
                            "date": int(time.time()),
                            "complete_text": complete_text,
                            "processing": False
                        }
                    }
                )
            else:
                db.social_media_copy_marketing.delete_one(
                    {
                        "user_id": user_id,
                        "goal": goal
                    }
                )
        except Exception as e:
            logging.exception(e)

    db.social_media_copy_marketing.update_many(
        {
            "user_id": user_id,
            "processing": True
        },
        {
            "$set": {
                "processing": False
            }
        }
    )
