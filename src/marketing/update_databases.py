import time
import logging

from facebook_business.exceptions import FacebookError
from facebook_business.adobjects.campaign import Campaign
from facebook_business.api import FacebookAdsApi

from marketing.suggested_budgets_estimate import get_suggested_budgets_estimates
from marketing.utils import db, get_daily_budget_duration, get_start_end_date
from marketing.campaign.results import get_estimated_results
from marketing import API_VERSION


def update_collections(goal, campaign_id, user_id, account_id, access_token, is_old):
    update_suggested_budgets(goal, campaign_id, user_id, account_id, access_token)
    time.sleep(60)
    update_goal_estimates(goal, campaign_id, user_id, account_id, access_token)
    time.sleep(60)
    update_suggested_campaigns(goal, campaign_id, user_id, account_id, access_token, is_old)
    time.sleep(60)
    update_optimized_interests_age(goal, campaign_id, user_id, account_id, access_token)


def remove_collections_processing_true(user_id, goal=None, collections=None):
    if collections is None:
        collections = ["suggested_budgets", "goal_estimates", "suggested_campaigns", "optimized_interests_age"]

    delete_filter = {
        "user_id": user_id,
        "processing": True
    }
    if goal is not None:
        delete_filter["goal"] = goal

    for collection in collections:
        db[collection].delete_many(delete_filter)


def update_suggested_budgets(goal, campaign_id, user_id, account_id, access_token):
    try:
        suggested_budgets_estimates, delivery_estimate = get_suggested_budgets_estimates(goal, account_id,
                                                                                         access_token, campaign_id)
        if suggested_budgets_estimates:
            db.suggested_budgets.update_one(
                {
                    "user_id": user_id,
                    "goal": goal,
                },
                {
                    "$set": {
                        "account_id": account_id,
                        "suggested_budgets_estimates": suggested_budgets_estimates,
                        "delivery_estimate": delivery_estimate,
                        "date": int(time.time())
                    }
                },
                upsert=True
            )
        else:
            db.suggested_budgets.delete_many(
                {
                    "user_id": user_id,
                    "goal": goal,
                })
    except FacebookError:
        logging.exception("")
        db.suggested_budgets.delete_many(
            {
                "user_id": user_id,
                "goal": goal
            }
        )
    except Exception:
        logging.exception("")
        db.suggested_budgets.delete_many(
            {
                "user_id": user_id,
                "goal": goal
            }
        )


def update_goal_estimates(goal, campaign_id, user_id, account_id, access_token):
    FacebookAdsApi.init(access_token=access_token, api_version=API_VERSION)
    daily_budget = Campaign(campaign_id).get_ad_sets(fields=["daily_budget"])[0]["daily_budget"]
    try:
        estimated_results = get_estimated_results(campaign_id, goal, access_token, budget=daily_budget)
        db.goal_estimates.update_one(
            {
                "user_id": user_id,
                "goal": goal
            },
            {
                "$set": {
                    "estimated_results": estimated_results,
                    "account_id": account_id,
                    "date": int(time.time())
                }
            },
            upsert=True
        )
    except FacebookError:
        print("There was some facebook related error")
        db.goal_estimates.delete_many(
            {
                "user_id": user_id,
                "goal": goal
            }
        )
    except Exception as exception:
        print(exception)
        db.goal_estimates.delete_many(
            {
                "user_id": user_id,
                "goal": goal
            }
        )


def update_suggested_campaigns(goal, campaign_id, user_id, account_id, access_token, is_old):
    estimated_results = get_estimated_results(campaign_id=campaign_id, goal=goal,
                                              access_token=access_token, budget=None)

    daily_budget, duration = get_daily_budget_duration(campaign_id, access_token)
    start_time, end_time = None, None
    if is_old:
        start_time, end_time = get_start_end_date(campaign_id, access_token)
    db.suggested_campaigns.update_one(
        {
            "user_id": user_id,
            "goal": goal,
            "processing": True
        },
        {
            "$set": {
                "processing": False,
                "account_id": account_id,
                "estimated_results": estimated_results,
                "budget": "{:.2f}".format(daily_budget / 100),
                "duration": int(duration),
                "campaign_id": campaign_id,
                "total_spend": "{:.2f}".format(duration * daily_budget / 100),
                "date": int(time.time()),
                "start_time": start_time,
                "end_time": end_time
            }
        }
    )


def update_optimized_interests_age(goal, campaign_id, user_id, account_id, access_token):
    FacebookAdsApi.init(access_token=access_token, api_version=API_VERSION)
    adset = Campaign(campaign_id).get_ad_sets()[0]

    targeting = adset.api_get(fields=["targeting"])["targeting"]
    flexible_spec = targeting["flexible_spec"]
    interests_list = [i for flex_spec in flexible_spec for i in flex_spec["interests"]]
    unique_interests = []

    for interest in interests_list:
        if interest not in unique_interests:
            unique_interests.append(interest)

    db.optimized_interests_age.update_one(
        {
            "user_id": user_id,
            "account_id": account_id,
            "goal": goal
        },
        {
            "$set": {
                "optimized_interests": unique_interests
            }
        },
        upsert=True
    )
