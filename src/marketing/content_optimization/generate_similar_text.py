import openai
import os
import yaml
from nltk import tokenize
import random
import emoji
from marketing.utils import get_json_response
from marketing.data_from_user import get_social_accounts
from facebook_business.adobjects.ad import Ad
from facebook_business.adobjects.adaccount import AdAccount
from marketing.shared import n_get_completion

emojies = [":heart_eyes:", ":sunglasses:", ":purple_heart:", ":blue_heart:", ":yellow_heart:", ":innocent:",
           ":revolving_hearts:", ":sparkling_heart:", ":boom:", ":sparkles:",
           ":cherry_blossom:", ":hibiscus:", ":heart_eyes_cat:"]


def similar_adcopy(text, locations=None, n=2):
    openai.api_key = os.getenv("OPENAI_API_KEY")
    if locations is not None:
        url = f"{os.getenv('gmb_dev_url')}GetLocationInformation?locationName={locations}"
        try:
            response = get_json_response(url)
            name = response["name"]
            primary_cat = response["primaryCategoryDisplaName"]
        except Exception:
            return []

        prompt = f"Scrivi una descrizione per un {primary_cat} che si chiama" \
                 f"{name} simile alla seguente: {text}"
    else:
        prompt = f"Scrivi una descrizione per un ristorante con lo stesso nome simile alla seguente: {text}"
    response = n_get_completion(prompt,0.7,n)
    output = []
    for text_ in response:
        text = text_["message"]["content"]
        text_list = tokenize.sent_tokenize(text.strip())
        final_text = ""
        emojies_ = random.sample(emojies, min(len(emojies), len(text_list)))
        for i, text in enumerate(text_list):
            text_emoji = text + emoji.emojize(emojies_[i], language="alias")
            final_text += text_emoji + "\n"
        final_text = final_text.replace("menu", "menù")
        output.append(final_text)

    return output


def change_ad_copy(ad: Ad, user_id):
    name = ad.api_get(fields=["name"])["name"]
    social_accounts = get_social_accounts(user_id)
    locations = social_accounts["gmbLocationResourceIdentifier"]
    account_id = social_accounts["facebookAdAccount"]
    # locations = None
    # account_id = "act_1787539531597931"
    old_copy = ad.get_ad_creatives(fields=["object_story_spec"])[0]["object_story_spec"]["link_data"]["message"]
    new_copy = similar_adcopy(old_copy, locations, n=1)[0]
    ad_creative_list = list(ad.get_ad_creatives(fields=["object_story_spec"]))
    for ad_creative in ad_creative_list:
        if "image" in name:
            link_data = ad_creative["object_story_spec"]["link_data"]
            link_data.update({"message": new_copy})

            object_story_spec = ad_creative["object_story_spec"]
            object_story_spec.update({"link_data": link_data})
            object_story_spec["link_data"].pop("picture", None)
            object_story_spec["link_data"].pop("image_url", None)

            params = {
                "name": "AdCreative",
                "object_story_spec": object_story_spec
            }

        elif "video" in name:
            video_data = ad_creative["object_story_spec"]["video_data"]
            video_data.update({"message": new_copy})

            object_story_spec = ad_creative["object_story_spec"]
            object_story_spec.update({"video_data": video_data})
            object_story_spec["video_data"].pop("picture", None)
            object_story_spec["video_data"].pop("image_url", None)

            params = {
                "name": "AdCreative",
                "object_story_spec": object_story_spec
            }
        elif "carousel" in name:
            link_data = ad_creative["object_story_spec"]["link_data"]
            link_data.update({"message": new_copy})
            for child_attachment in link_data["child_attachments"]:
                child_attachment.pop("picture", None)

            object_story_spec = ad_creative["object_story_spec"]
            object_story_spec.update({"link_data": link_data})
            object_story_spec["link_data"].pop("picture", None)
            object_story_spec["link_data"].pop("image_url", None)

            params = {
                "name": "AdCreative",
                "object_story_spec": object_story_spec
            }
        else:
            link_data = ad_creative["object_story_spec"]["link_data"]
            link_data.update({"message": new_copy})

            object_story_spec = ad_creative["object_story_spec"]
            object_story_spec.update({"link_data": link_data})
            object_story_spec["link_data"].pop("picture", None)
            object_story_spec["link_data"].pop("image_url", None)

            params = {
                "name": "AdCreative",
                "object_story_spec": object_story_spec
            }

        new_creative = AdAccount(account_id).create_ad_creative(params=params)
        ad.api_update(params={"creative": {"creative_id": new_creative["id"]}})
        ad_creative.api_delete()
