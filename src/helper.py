import logging
from facebook_business import FacebookAdsApi
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.adobjects.campaign import Campaign
from facebook_business.exceptions import FacebookError
from marketing.buyer_persona import get_primary_secondary_buyer_persona
from marketing.campaign.results import get_estimated_results, page_and_ad_insights
from marketing.campaign.optimization import optimize_campaign
from marketing.suggested_budgets_estimate import get_suggested_budgets_estimates
from marketing.update_databases import update_collections, remove_collections_processing_true
from marketing.campaign.creation import create_campaign_adset
from marketing.content_optimization.ad_optimization import AdCopyPersonas
from marketing.data_from_user import get_social_accounts
from marketing.utils import db
import time


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
            upsert=True
        )
    except FacebookError as fb:
        logging.exception(fb)
        db.buyerpersonas.delete_many({"user_id": user_id})
    except Exception as e:
        logging.exception(e)
        db.buyerpersonas.delete_many({"user_id": user_id})


def optimize_campaign_thread(req):
    optimize_campaign(campaign_id=req["campaign_id"],
                      access_token=req["access_token"],
                      account_id=req["account_id"],
                      user_id=req["user_id"],
                      goal=req["goal"])


def create_suggested_campaign_thread(goals, access_token, user_id):
    account_id = get_social_accounts(user_id)["facebookAdAccount"]
    for goal in goals:
        campaign_id = ""
        try:
            campaign_id = create_campaign_adset(user_id, access_token, goal)
            optimize_campaign(campaign_id, access_token, account_id, user_id)
            update_collections(goal, campaign_id, user_id, account_id, access_token)
            time.sleep(60)
            Campaign(campaign_id).api_update(params={"name": f"Campagna {goal} suggerita"})
        except Exception as e:
            logging.exception(e)
            remove_collections_processing_true(user_id, goal)
            if campaign_id:
                Campaign(campaign_id).api_delete()
        else:
            time.sleep(60)



def get_estimated_results_thread(account_id, access_token, campaign_id, goal):
    try:
        daily_budget = int(Campaign(campaign_id).get_ad_sets(fields=["daily_budget"])[0]["daily_budget"])
        estimate = get_estimated_results(campaign_id=campaign_id, goal=goal, access_token=access_token,
                                         budget=daily_budget)

    except FacebookError as fb:
        logging.exception(fb)
        db.goal_estimates.delete_one({
            "account_id": account_id,
            "goal": goal,
            "processing": True
        })
    except Exception as e:
        logging.exception(e)
        db.goal_estimates.delete_one({
            "account_id": account_id,
            "goal": goal,
            "processing": True
        })
    else:
        db.goal_estimates.update_one(
            {
                "account_id": account_id,
                "goal": goal,
                "processing": True
            },
            {
                "$set": {
                    "processing": False,
                    "estimated_results": estimate
                }
            }
        )


def get_estimated_results_loop_thread(account_id, access_token, goals):
    FacebookAdsApi.init(access_token=access_token)
    campaigns = list(AdAccount(account_id).get_campaigns(fields=["name"]))
    for goal in goals:
        for campaign in campaigns:
            if f"Campagna {goal} suggerita" == campaign["name"]:
                get_estimated_results_thread(account_id, access_token, campaign["id"], goal)
                time.sleep(120)
                break


def get_suggested_budgets_estimates_thread(goal, account_id, access_token):
    try:
        suggested_budgets_estimates, delivery_estimate = get_suggested_budgets_estimates(goal, account_id, access_token)

        if suggested_budgets_estimates:
            db.suggested_budgets.update_one(
                {
                    "account_id": account_id,
                    "goal": goal,
                    "processing": True
                },
                {
                    "$set": {
                        "processing": False,
                        "suggested_budgets_estimates": suggested_budgets_estimates,
                        "delivery_estimate": delivery_estimate
                    }
                }
            )
        else:
            db.suggested_budgets.delete_many(
                {
                    "account_id": account_id,
                    "goal": goal,
                    "processing": True
                }
            )

    except FacebookError as fb:
        logging.exception(fb)
        db.suggested_budgets.delete_many(
            {
                "goal": goal,
                "account_id": account_id,
                "processing": True
            }
        )

    except Exception as e:
        logging.exception(e)
        db.suggested_budgets.delete_many(
            {
                "goal": goal,
                "account_id": account_id,
                "processing": True
            }
        )


def create_ad_copy_personas_all_goals(locations, goals):
    for goal in goals:
        db.adcopy.update_one(
            {
                "locations": locations,
                "goal": goal
            },
            {
                "$set": {
                    "processing": True
                }
            },
            upsert=True
        )

    for goal in goals:
        time.sleep(60)
        try:
            result = AdCopyPersonas(goal, locations)
            complete_text = result.complete_text(n=10)
            if len(complete_text) >= 4:
                db.adcopy.update_one(
                    {
                        "locations": locations,
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
                db.adcopy.delete_one(
                    {
                        "locations": locations,
                        "goal": goal
                    }
                )
        except Exception as e:
            logging.exception(e)
            db.adcopy.delete_one(
                {
                    "locations": locations,
                    "goal": goal
                }
            )


def page_ad_insights_thread(account_id, page_id, access_token, page_token, first_time=False):
    if first_time:
        db.page_ad_insights.insert_one(
            {
                "account_id": account_id,
                "page_id": page_id,
                "page_ad_insights": {},
                "date": int(time.time())
            }
        )
    try:
        page_ad_insights = page_and_ad_insights(account_id, page_id, access_token, page_token)
        db.page_ad_insights.update_one(
            {
                "account_id": account_id,
                "page_id": page_id
            },
            {
                "$set": {
                    "page_ad_insights": page_ad_insights,
                    "date": int(time.time())
                }
            }
        )
    except FacebookError as fb:
        logging.exception(fb)
    except Exception as e:
        logging.exception(e)
        db.page_ad_insights.delete_many(
            {
                "account_id": account_id,
                "page_id": page_id
            }
        )
