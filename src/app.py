import itertools
import logging
import threading
import requests
import uvicorn
from datetime import datetime, timedelta
from pydantic import BaseModel
from typing import List
import time
import json
from threading import Thread
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, Response, Request, HTTPException
from facebook_business.exceptions import FacebookError, FacebookRequestError
from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.campaign import Campaign
from facebook_business.adobjects.adaccount import AdAccount
from marketing import BUYER_PERSONA_LIST, facebook_time_format, tz, ALL_GOALS, API_VERSION, ALL_GOALS_SOCIAL_MEDIA, db, \
    db_rc_pharmacies
from marketing.buyer_persona import AccessData, check_conditions_buyer_persona
from marketing.campaign.results import get_estimated_results, update_estimated_results
from marketing.content_optimization.ad_optimization import AdCopyPersonas
from marketing.sentiment_analysis.sentiment_analizer import get_sentiment_list
from marketing.utils import change_date, change_sentiment_analysis_output, \
    check_if_broad_required, get_categories, remove_deleted_campaigns
from marketing.recommendation_sys.user_rec import product_recommendation_to_users
from marketing.buyer_persona_GPT.main import visitatore, gpt_buyer_persona
from marketing.reinforcement_learning.q_learning import reinforcement_pipeline
from marketing.newsletter.newsletter_copy import NewsletterGeneration
from marketing.social_media.social_media_copy_new import SocialMediaCopy
from helper import page_ad_insights_thread
from utils_api import buyer_persona_thread, create_campaign_thread, \
    create_suggested_campaign_thread, create_custom_audience_thread, \
    data_for_running_campaigns
from marketing.image_recognition.combined_tag import matching
from marketing.image_recognition.tags_from_facebook import get_fb_page
from marketing.image_recognition.tags_from_pexels import mathing_for_pexel
from marketing.image_recognition.tags_from_unsplash import matching_for_unsplash
from marketing.data_from_user import get_menu_api, get_social_accounts
from marketing.campaign.utils_campaign import modify_campaign_with_new_data
from marketing.trends_competition.nearby_competitors.main import get_competitors_nearby
from marketing.trends_competition.food_trending.main import extract_trends
from marketing.trends_competition.food_trending.main import search_keywords
import os

app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("origins"),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "Accept",
        "Origin",
        "X-Requested-With",
        "Access-Control-Allow-Origin",
        "Access-Control-Allow-Headers",
        "Access-Control-Allow-Methods",
        "Access-Control-Allow-Credentials",
        "sentry-trace",
        "baggage"
    ]
)

@app.post('/schedule_ad_copy', status_code=200)
def schedule_ad_copy(response: Response):
    try:
        response.status_code = 200
        buyer_persona_list = BUYER_PERSONA_LIST.copy()
        goal_list = ALL_GOALS.copy()
        persona_goal_combinations = list(itertools.product(buyer_persona_list, goal_list))
        restaurant_ids_obj = db_rc_pharmacies["rc"]["pharmacies"].distinct("pharmacyOwner")
        restaurant_ids = [str(user_id) for user_id in restaurant_ids_obj]
        for each_restaurant in restaurant_ids:
            for buyer_persona, goal in persona_goal_combinations:
                """user id in here is restaurant id itself"""

                try:
                    db["ad_copy_marketing"].delete_many({"user_id": each_restaurant,
                                                         "buyer_persona": buyer_persona,
                                                         "goal": goal,
                                                         "processing": False,
                                                         "createdAt": {
                                                             "$gte": int((datetime.now()).timestamp()),
                                                             "$lt": int(
                                                                 (datetime.now() - timedelta(days=30)).timestamp())
                                                         }})
                except:
                    logging.exception("There is not such content to delete. Continuing with creation")
                try:
                    result = AdCopyPersonas(buyer_persona, goal, each_restaurant)
                except Exception as e:
                    logging.exception(f"restaurant_id: {each_restaurant}, buyer_persona: {buyer_persona}, goal: {goal}")
                    logging.exception(e)
                    continue
                complete_text = result.complete_text(n=4)
                for each_complete_text in complete_text:
                    each_complete_text.update({
                        "buyer_persona": buyer_persona,
                        "goal": goal,
                        "createdAt": int((datetime.now()).timestamp()),
                        "processing": False,
                    })
                    db["ad_copy_marketing"].insert_one(each_complete_text)
        return {"status": response.status_code}
    except Exception as e:
        response.status_code = 500
        logging.exception(e)
        return {
            "status": response.status_code,
            "error": f"{type(e).__name__} at line {e.__traceback__.tb_lineno} of {__file__}: {e}"
        }


@app.post('/schedule_social_media_copy', status_code=200)
def schedule_social_media_copy(response: Response):
    additinal_prompt = ["\n - Il testo generato deve essere breve e composto da 1 frasi",
                        "\n - Il testo generato deve essere breve e composto da 2 frase",
                        "\n - Il testo generato deve essere breve e composto da 3 frase",
                        "\n - Il testo generato deve essere lungo e composto da 4 frase"]
    try:
        response.status_code = 200
        restaurant_ids_obj = db_rc_pharmacies["rc"]["pharmacies"].distinct("pharmacyOwner")
        restaurant_ids = [str(user_id) for user_id in restaurant_ids_obj]
        goal_list = ALL_GOALS_SOCIAL_MEDIA.copy()
        for each_restaurant in restaurant_ids:
            """user id in here is restaurant id itself"""
            try:
                db["social_media_copy_marketing"].delete_many({"user_id": each_restaurant,
                                                               "processing": False,
                                                               "createdAt": {
                                                                   "$gte": int((datetime.now()).timestamp()),
                                                                   "$lt": int((datetime.now() - timedelta(
                                                                       days=30)).timestamp())
                                                               }})
            except:
                logging.exception("There is not such content to delete. Continuing with creation")

            cid = requests.get(str(os.getenv("gmb_api_aigot")) + "existingLocationChecker?googlePlaceId=" + str(
                list(db["profiles"].find())[0]["googlePlaceId"]))
            for each_goal in goal_list:
                response_list = []
                social_media_ins = SocialMediaCopy(user_id=str(each_restaurant), location=str(cid), goal=each_goal)

                def generate_and_append(prompt):
                    result = social_media_ins.complete_text(prompt)
                    response_list.append(result)

                threads = []
                for prompt in additinal_prompt:
                    thread = threading.Thread(target=generate_and_append, args=(prompt,))
                    threads.append(thread)
                    thread.start()
                for thread in threads:
                    thread.join()
                for each_complete_text in response_list:
                    each_complete_text.update(
                        {"goal": each_goal, "createdAt": int((datetime.now()).timestamp()),
                         "locations": f"locations/{str(cid)}"})
                    db["social_media_copy_marketing"].insert_one(each_complete_text)
        return {"status": response.status_code}
    except Exception as e:
        response.status_code = 500
        logging.exception(e)
        return {
            "status": response.status_code,
            "error": f"{type(e).__name__} at line {e.__traceback__.tb_lineno} of {__file__}: {e}"
        }


@app.post('/social_media_copy', status_code=200)
async def social_media_copy_f(data_json: Request, response: Response):
    data = await data_json.json()
    response.status_code = 200
    additinal_prompt = ["\n - Il testo generato deve essere breve e composto da 1 frasi",
                        "\n - Il testo generato deve essere breve e composto da 2 frase",
                        "\n - Il testo generato deve essere breve e composto da 3 frase",
                        "\n - Il testo generato deve essere lungo e composto da 4 frase"]
    try:
        query = {
            "user_id": data.get("user_id"),
            "goal": data.get("goal"),
            "processing": False
        }
        projection = {"_id": 0}
        results = list(db['social_media_copy_marketing'].find(query, projection).limit(4))
        if len(results) >= 4:
            return results
        else:
            response_list = []
            social_media_ins = SocialMediaCopy(user_id=str(data.get("user_id")), goal=data.get("goal"))

            def generate_and_append(prompt):
                result = social_media_ins.complete_text(prompt)
                response_list.append(result)

            threads = []
            for prompt in additinal_prompt:
                thread = threading.Thread(target=generate_and_append, args=(prompt,))
                threads.append(thread)
                thread.start()
            for thread in threads:
                thread.join()
            for each_complete_text in response_list:
                each_complete_text.update(
                    {"user_id": str(data.get("user_id")), "goal": data.get("goal"), "processing": False,
                     "createdAt": int((datetime.now()).timestamp())})
                db["social_media_copy_marketing"].insert_one(each_complete_text)
            return {"status": response.status_code,
                    "response": list(db['social_media_copy_marketing'].find(query, projection).limit(4))}
    except Exception as e:
        response.status_code = 500
        logging.exception(e)
        return {
            "status": response.status_code,
            "error": f"{type(e).__name__} at line {e.__traceback__.tb_lineno} of {__file__}: {e}"
        }


@app.post("/ad_copy_personas", status_code=200)
async def get_ad_copy_buyer_persona(request: Request, response: Response):
    data = await request.json()
    response.status_code = 200
    return_data = []
    try:
        query = {
            "user_id": data.get("user_id"),
            "goal": data.get("goal"),
            "buyer_persona": data.get("buyer_persona"),
            "processing": False
        }
        results = list(db['ad_copy_marketing'].find(query).limit(4))
        if len(results) == 0:
            result = AdCopyPersonas(buyer_persona=query['buyer_persona'], goal=query['goal'], user_id=query['user_id'])
            results = result.complete_text(n=4)
            for each_complete_text in results:
                each_complete_text.update(
                    {
                        "buyer_persona": query['buyer_persona'],
                        "user_id": str(data.get("user_id")),
                        "goal": query['goal'],
                        "createdAt": int((datetime.now()).timestamp()),
                        "processing": False
                    }
                )
                db["ad_copy_marketing"].insert_one(each_complete_text)
                return_data.append(each_complete_text)
        else:
            return_data = results
        for item in return_data:
            item.pop("_id")
        return {"status": response.status_code, "response": return_data}
    except Exception as e:
        response.status_code = 500
        logging.exception(e)
        return {
            "status": response.status_code,
            "error": f"{type(e).__name__} at line {e.__traceback__.tb_lineno} of {__file__}: {e}"
        }


@app.post('/newsletter_copy', status_code=200)
async def newsletter_copy(data_json: Request, response: Response):
    data = await data_json.json()
    try:
        response.status_code = 200
        collection = db["generated_copies"]
        pipeline = [
            {
                "$match": {
                    "restaurant_id": data["restaurant_id"],
                    "goal": data["goal"],
                    "is_selected": True,
                    "content_type": "newsletter",
                }
            }
        ]

        selected_copies = list(collection.aggregate(pipeline))
        if len(selected_copies) != 0:
            generated_newsletter_copies = reinforcement_pipeline(selected_copies, data["goal"], data["companyName"])
        else:
            generated_newsletter_copies = NewsletterGeneration(goal=data.get("goal"),
                                                               companyName=data.get("companyName"))
        return {"status": response.status_code, "response": generated_newsletter_copies, "goal": data["goal"],
                "time": int((datetime.now()).timestamp())}
    except Exception as e:
        logging.exception(e)
        response.status_code = 500
        return {"status": response, "response": e.__class__.__name__}


@app.post('/sentiment_analyzer', status_code=200)
async def sentiment_analyzer(data_json: Request, response: Response):
    data = await data_json.json()
    location = data["location"]
    try:
        response.status_code = 200
        db.sentiment_analysis.delete_many(
            {
                "location": location,
                "period": data["days_preset"],
                "analysis": {"$exists": False}
            }
        )
        analysis = db.sentiment_analysis.find_one(
            {
                "location": location,
                "period": data["days_preset"]
            }
        )
    except Exception as e:
        logging.exception(e)
        response.status_code = 400
        return {"status": response.status_code, "error_message": e.__class__.__name__}
    if analysis is None or analysis.get("date", 0) < int(time.time() - 86400):
        try:
            _, counts = get_sentiment_list(location, int(data["days_preset"]))
            counts_output = change_sentiment_analysis_output(counts)
            db.sentiment_analysis.update_one(
                {
                    "location": location,
                    "period": data["days_preset"]
                },
                {
                    "$set": {
                        "analysis": counts_output,
                        "date": int(time.time())
                    }
                },
                upsert=True
            )
            if all(item["value"] == 0 for item in counts_output):
                counts_output = []
            return {"status": response.status_code,
                    "response": {"data": counts_output}}
        except Exception as e:
            logging.exception(e)
            response.status_code = 500
            return {"status": response.status_code, "response_message": e.__class__.__name__}

    else:
        counts_output = analysis["analysis"]
        if all(item["value"] == 0 for item in counts_output):
            counts_output = []
        return {"status": response.status_code, "response": {"data": counts_output}}


class Product(BaseModel):
    user_id: str or None
    restaurant_id: str
    product_ids: List[str] or None


@app.post("/product_recommendation", status_code=200)
async def product_rec(data: Product, response: Response):
    try:
        response.status_code = 200
        if data:
            recommend = product_recommendation_to_users(restaurant_id=data.restaurant_id, user_id=data.user_id,
                                                        product_ids=data.product_ids)
            recommended_products_list = recommend.final_recommendation()
            return {"status": response.status_code, "response": recommended_products_list}
    except Exception as e:
        logging.exception(e)
        response.status_code = 500
        return {"status": response.status_code, "response_msg": e.__class__.__name__}


@app.get("/get_buyer_persona", status_code=200)
async def get_buyer_persona(data_json: Request, response: Response):
    try:
        data = await data_json.json()
        access_data = AccessData(user_id=data["user_id"])
        access_data.get_data_from_user_id()

        # Query buyer persona
        bp_coll = db.buyerpersonas.find_one(
            {
                "user_id": data["user_id"],
                "$or": [
                    {"processing": False},
                    {"processing": True, "buyerpersonas": {"$exists": True}}
                ]
            }
        )

        if bp_coll and "buyerpersonas" in bp_coll:
            response.status_code = 200
            return {
                "status": response.status_code,
                "success": True,
                "buyer_personas": bp_coll["buyerpersonas"]
            }
        else:
            db.buyerpersonas.delete_many({"user_id": data["user_id"]})

            raise HTTPException(
                status_code=500,
                detail="There is no buyer persona for this user"
            )

    except Exception as e:
        logging.exception(e)
        raise HTTPException(
            status_code=500,
            detail=f"{type(e).__name__} at line {e.__traceback__.tb_lineno} of {__file__}: {e}"
        )


@app.post("/create_buyer_persona", status_code=200)
async def create_buyer_persona(request: Request, response: Response):
    try:
        data = await request.json()
        access_data = AccessData(access_token=data["access_token"], user_id=data["user_id"])
        access_data.get_data_from_user_id()
        force = data.get("force", False)
        db.buyerpersonas.delete_many({
            "user_id": data["user_id"],
            "processing": True,
            "date": {"$lt": int(time.time() - 1200)}
        })
        bp = db.buyerpersonas.find_one({"user_id": data["user_id"]})
        if bp and bp.get("processing", False):
            response.status_code = 200
            return {"status": response.status_code, "success": True, "message": "Creating new buyer persona"}
        require_new_persona = check_conditions_buyer_persona(data["user_id"], access_data)
        if require_new_persona or force:
            db.buyerpersonas.update_one(
                {"user_id": data["user_id"]},
                {"$set": {"date": int(time.time()), "processing": True}})
            buyer_persona_thread(data["country"], data["user_id"], access_data)
            response.status_code = 200
            return {"status": response.status_code, "success": True, "message": "Creating new buyer persona"}
    except Exception as e:
        logging.exception(e)
        response.status_code = 500
        return {"status": response.status_code, "success": False, "error": str(e)}
    response.status_code = 200
    return {"status": response.status_code, "success": True}


@app.post("/create_campaign", status_code=200)
async def create_image_campaign(request: Request, response: Response):
    pass


@app.post("/running_campaigns", status_code=200)
async def running_campaigns(request: Request, response: Response):
    pass

@app.post("/get_estimate", status_code=200)
async def get_estimate(request: Request, response: Response):
   pass


@app.post("/suggested_campaigns", status_code=200)
async def suggested_campaigns(request: Request, response: Response):
   pass


@app.post("/get_tag_from_facebook", status_code=200)
async def get_tag_from_facebook(request: Request, response: Response):
    pass


@app.post("/campaign_social_results", status_code=200)
async def campaign_social_results(request: Request, response: Response):
    data = await request.json()
    response.status_code = 200
    try:
        access_token = data["access_token"]
        user_id = data["user_id"]

        social_accounts = get_social_accounts(user_id)
        page_token = social_accounts["facebookPageAuthToken"]
        account_id = social_accounts["facebookAdAccount"]
        page_id = social_accounts["facebookPageResourceIdentifier"]

        insights = db.page_ad_insights.find_one(
            {
                "account_id": account_id,
                "page_id": page_id
            }
        )

        if not insights:
            Thread(target=page_ad_insights_thread, args=(account_id, page_id, access_token, page_token, True)).start()
            return {
                "success": response.status_code,
                "page_ad_insights": {},
                "message": "Calculating insights"
            }

        elif insights and insights["date"] > int(time.time() - 86400):
            return {
                "success": response.status_code,
                "page_ad_insights": insights["page_ad_insights"]
            }


        elif insights and insights["date"] <= int(time.time() - 86400):
            Thread(target=page_ad_insights_thread, args=(account_id, page_id, access_token, page_token, False)).start()

            return {
                "success": response.status_code,
                "page_ad_insights": insights["page_ad_insights"],
                "message": "Calculating new insights"
            }
        else:
            return {
                "success": False,
                "page_ad_insights": {},
                "message": "An unknown error has occurred"
            }
    except FacebookError as fb:
        logging.exception(fb)
        response.status_code = 500
        return {
            "success": response.status_code,
            "error": f"{type(fb).__name__} at line {fb.__traceback__.tb_lineno} of {__file__}: {fb}"
        }


@app.post("/stop_campaign", status_code=200)
async def stop_campaign(request: Request, response: Response):
    pass

@app.post("/ended_campaign", status_code=200)
async def ended_campaigns(request: Request, response: Response):
    pass

@app.post("/show_campaign_info", status_code=200)
async def show_campaign_info(request: Request, response: Response):
    response.status_code = 200
    data = await request.json()
    try:
        campaign_id = data["campaign_id"]
        account_id = data["account_id"]

        document = db.running_campaigns.find_one(
            {
                "account_id": account_id,
                "campaign_id": campaign_id
            }
        )

        if document is not None:
            return {
                "success": response.status_code,
                "copy": document["copy"],
                "budget": document["budget"],
                "suggested_budgets": document["suggested_budgets"],
                "end_date": document["end_date"]
            }
        else:
            response.status_code = 500
            return {
                "success": response.status_code,
                "copy": "",
                "budget": "",
                "suggested_budgets": {},
                "end_date": "",
                "error_message": "The campaign is not in the database"
            }
    except Exception as e:
        logging.exception(e)
        response.status_code = 500
        return {
            "success": response.status_code,
            "copy": "",
            "budget": "",
            "suggested_budgets": {},
            "end_date": "",
            "error_message": f"{type(e).__name__} at line {e.__traceback__.tb_lineno} of {__file__}: {e}"
        }


@app.post("/modify_campaign", status_code=200)
async def modify_campaign(request: Request, response: Response):
    pass
@app.post("/create_custom_audience", status_code=200)
async def create_custom_audience(request: Request, response: Response):
    pass

@app.get("/competitors_analysis/{restaurant_id}")
def competitors_analysis(restaurant_id):
    """
    Retrieves nearby restaurants for the given restaurant_id.

    Parameters:
    - restaurant_id (str): The ID of the restaurant to retrieve nearby competitors.

    Returns:
    A dictionary containing the restaurant information, where the key is the restaurant_id.
    """
    # Call the get_competitors_nearby function with the provided restaurant_id
    analysis = get_competitors_nearby(restaurant_id)

    if analysis is None:
        return {"message": "Failed to retrieve competitors."}

    return analysis


@app.post("/gpt_buyer_persona")
async def create_buyer_persona(request: Request, response: Response):
    try:
        response.status_code = 200
        data = await request.json()
        result = gpt_buyer_persona(data["restaurant_id"])
        return {"status": response.status_code, "response": json.loads(result)}
    except Exception as e:
        logging.exception(e)
        response.status_code = 500
        return {"status": response, "response": e.__class__.__name__}

@app.post("/schedule_create_buyer_personas_description")
async def schedule_create_buyer_personas_description(response: Response):
    try:
        response.status_code = 200
        restaurant_ids_obj = db_rc_pharmacies["rc"]["pharmacies"].distinct("pharmacyOwner")
        restaurant_ids = [str(user_id) for user_id in restaurant_ids_obj]
        for each_restaurant in restaurant_ids:
            result = gpt_buyer_persona(each_restaurant)
            restaurant_current = db["buyerpersonas_description"].find_one({"user_id": each_restaurant})
            if len(restaurant_current) > 0:
                filter_criteria = {"user_id": each_restaurant}
                update_operation = {'$set': {'bp_description': result}}
                db["buyerpersonas_description"].update_one(filter_criteria, update_operation)
            else:
                restaurant_new = {"user_id": each_restaurant, "bp_description": result,
                                  "createdAt": int((datetime.now()).timestamp()), "processing": False}
                db["buyerpersonas_description"].insert_one(restaurant_new)
        return {"status": response.status_code}
    except Exception as e:
        logging.exception(e)
        response.status_code = 500
        return {"status": response, "response": e.__class__.__name__}

@app.post("/schedule_visitatore_description")
async def schedule_schedule_visitatore_description(response: Response):
    try:
        response.status_code = 200
        restaurant_ids_obj = db_rc_pharmacies["rc"]["pharmacies"].distinct("pharmacyOwner")
        restaurant_ids = [str(user_id) for user_id in restaurant_ids_obj]
        for each_restaurant in restaurant_ids:
            result = visitatore(each_restaurant)
            restaurant_current = db["buyerpersonas_description"].find_one({"user_id": each_restaurant})
            if len(restaurant_current) > 0:
                filter_criteria = {"user_id": each_restaurant}
                update_operation = {'$set': {'visitatore_description': result}}
                db["buyerpersonas_description"].update_one(filter_criteria, update_operation)
            else:
                restaurant_new = {"user_id": each_restaurant, "visitatore_description": result,
                                  "createdAt": int((datetime.now()).timestamp()), "processing": False}
                db["buyerpersonas_description"].insert_one(restaurant_new)
        return {"status": response.status_code}
    except Exception as e:
        logging.exception(e)
        response.status_code = 500
        return {"status": response, "response": e.__class__.__name__}


@app.post("/visitatore")
async def get_visitatore(request: Request, response: Response):
    try:
        response.status_code = 200
        data = await request.json()
        result = visitatore(data["restaurant_id"])
        return {"status": response.status_code, "response": json.loads(result)}
    except Exception as e:
        logging.exception(e)
        response.status_code = 500
        return {"status": response, "response": e.__class__.__name__}


if __name__ == '__main__':
    uvicorn.run("app:app", port=8000, host="0.0.0.0", reload=True)
