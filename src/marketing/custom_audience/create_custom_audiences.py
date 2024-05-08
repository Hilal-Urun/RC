import os
import time

from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.exceptions import FacebookError
from facebook_business.api import FacebookAdsApi
from marketing.utils import get_json_response


def create_website_ALL_VISITORS_custom_audience(account_id: str,
                                                pixel_id: str,
                                                access_token: str,
                                                retention_days=30):
    FacebookAdsApi.init(access_token=access_token)
    rule = {
        "inclusions":
            {
                "operator": "or",
                "rules": [{
                    "event_sources": [{
                        "type": "pixel",
                        "id": pixel_id
                    }],
                    "retention_seconds": int(retention_days * 86400),
                    "filter": {
                        "operator": "and",
                        "filters": [{
                            "field": "url",
                            "operator": "i_contains",
                            "value": ""}
                        ]},
                    "template": "ALL_VISITORS"}]}}

    name = f"Visitatori sito web {retention_days}GG"

    params = {
        "name": name,
        "rule": str(rule),
        "retention_days": retention_days,
        "prefill": True
    }

    custom_audience = AdAccount(account_id).create_custom_audience(params=params)

    return custom_audience["id"], name


def create_video_custom_audience(account_id: str,
                                 video_id: str,
                                 access_token: str,
                                 retention_seconds: int = 0,
                                 retention_percentage: int = 0):
    FacebookAdsApi.init(access_token=access_token)
    if retention_seconds == 3:
        event_name = "video_watched"
        _time = f"{retention_seconds}s"
    elif retention_seconds in [10, 15]:
        event_name = f"video_view_{retention_seconds}s"
        _time = f"{retention_seconds}s"
    elif retention_percentage == 95:
        event_name = "video_completed"
        _time = f"{retention_percentage} percento"
    elif retention_percentage in [25, 50, 75]:
        event_name = f"video_view_{retention_percentage}_percent"
        _time = f"{retention_percentage} percento"
    else:
        print("Invalid parameter")
        return None

    rule = [
        {
            "object_id": video_id,
            "event_name": event_name
        }
    ]

    name = f"Interazione Video per {_time}"

    params = {
        "name": name,
        "description": f"C.A. per interazione con video {video_id}",
        "rule": str(rule),
        "subtype": "ENGAGEMENT",
        "retention_days": 30,
        "prefill": True
    }

    custom_audience = AdAccount(account_id).create_custom_audience(params=params)

    return custom_audience["id"], name


def create_website_event_custom_audience(account_id, access_token, pixel_id, event_name, retention_days=30):
    """

    Args:
        account_id: str
        access_token: str
        pixel_id: str
        event_name: ["ContactsPage", "DeliveryPage", "MenuPage", "Step2Booking", "Step3Booking", "Step4Booking",
                     "BookingPage", "HomePage"]
        retention_days: int

    Returns:

    """
    FacebookAdsApi.init(access_token=access_token)
    rule = {
        "inclusions":
            {
                "operator": "or",
                "rules": [{
                    "event_sources": [{
                        "type": "pixel",
                        "id": pixel_id
                    }],
                    "retention_seconds": int(retention_days * 86400),
                    "filter": {
                        "operator": "and",
                        "filters": [{
                            "field": "event",
                            "operator": "eq",
                            "value": event_name}
                        ]},
                }]}}

    name = f"{event_name} {retention_days}GG"
    params = {
        "name": name,
        "rule": str(rule),
        "retention_days": retention_days,
        "prefill": True
    }

    custom_audience = AdAccount(account_id).create_custom_audience(params=params)

    return custom_audience["id"], name


def create_facebook_action_custom_audience(account_id, access_token, page_id, action_name, retention_days=30):
    """

    Args:
        account_id: str
        access_token: str
        page_id: str
        action_name: ["page_engaged", "page_visited", "page_post_interaction", "page_cta_clicked"]
        retention_days: int

    Returns:

    """

    FacebookAdsApi.init(access_token=access_token)

    rule = {
        "inclusions":
            {
                "operator": "or",
                "rules": [{
                    "event_sources": [{
                        "type": "page",
                        "id": page_id
                    }],
                    "retention_seconds": int(retention_days * 86400),
                    "filter": {
                        "operator": "and",
                        "filters": [{
                            "field": "event",
                            "operator": "eq",
                            "value": action_name}
                        ]}}]}}

    name = f"Interazioni pagina FB {retention_days}GG"
    params = {
        "name": name,
        "rule": str(rule),
        "retention_days": retention_days,
        "prefill": True
    }

    custom_audience = AdAccount(account_id).create_custom_audience(params=params)

    return custom_audience["id"], name


def create_instagram_action_custom_audience(account_id, access_token, ig_account, action_name, retention_days=30):
    """

    Args:
        account_id: str
        access_token: str
        ig_account: str
        action_name: ["ig_business_profile_all", "ig_business_profile_visit", "ig_business_profile_engaged",
                      "ig_business_profile_ad_saved"]
        retention_days: int

    Returns:

    """

    FacebookAdsApi.init(access_token=access_token)

    rule = {
        "inclusions":
            {
                "operator": "or",
                "rules": [{
                    "event_sources": [{
                        "type": "ig_business",
                        "id": ig_account
                    }],
                    "retention_seconds": int(retention_days * 86400),
                    "filter": {
                        "operator": "and",
                        "filters": [{
                            "field": "event",
                            "operator": "eq",
                            "value": action_name}
                        ]}}]}}
    name = f"Interazioni account IG {retention_days}GG"
    params = {
        "name": name,
        "rule": str(rule),
        "retention_days": retention_days,
        "prefill": True
    }

    custom_audience = AdAccount(account_id).create_custom_audience(params=params)

    return custom_audience["id"], name


def create_lookalike_audience(account_id, access_token, custom_audience_id, custom_audience_name):
    FacebookAdsApi.init(access_token=access_token)

    country = "IT"
    ratio = 0.01
    lookalike_spec = {
        "country": country,
        "origin": [
            {
                "id": custom_audience_id,
                "type": "custom_audience",
            }
        ],
        "ratio": ratio,
        "type": "custom_ratio"
    }

    name = f"Pubblico simile ({country}, {int(100 * ratio)})% - {custom_audience_name}"

    params = {
        "lookalike_spec": str(lookalike_spec),
        "name": name,
        "subtype": "LOOKALIKE",
        "origin_audience_id": custom_audience_id
    }

    AdAccount(account_id).create_custom_audience(params=params)


def create_all_custom_audience(user_id, pixel_id, access_token):
    url = f"{os.getenv('dashboard_backend_internal')}/pharmacist/{user_id}?socialAccounts.facebookAdAccount&" + \
          "socialAccounts.instagramAccountResourceIdentifier&socialAccounts.facebookPageResourceIdentifier"

    try:
        response = get_json_response(url)
        if response is None:
            print("There was some error")
            return False

        account_id = response["socialAccounts"].get("facebookAdAccount")
        page_id = response["socialAccounts"].get("facebookPageResourceIdentifier")
        ig_account = response["socialAccounts"].get("instagramAccountResourceIdentifier")

    except Exception as e:
        print(e)
        return False

    retention_days = [10, 30, 60]
    actions_website = ["ContactsPage", "DeliveryPage", "MenuPage", "Step2Booking",
                       "Step3Booking", "Step4Booking", "BookingPage", "HomePage"]
    actions_facebook = ["page_engaged", "page_visited", "page_post_interaction", "page_cta_clicked"]
    actions_instagram = ["ig_business_profile_all", "ig_business_profile_visit",
                         "ig_business_profile_engaged", "ig_business_profile_ad_saved"]

    try:
        for day in retention_days:
            for action_fb in actions_facebook:
                custom_id, custom_name = create_facebook_action_custom_audience(account_id, access_token,
                                                                                page_id, action_fb, day)
                time.sleep(60)
                create_lookalike_audience(account_id, access_token, custom_id, custom_name)
                time.sleep(60)
            for action_web in actions_website:
                custom_id, custom_name = create_website_event_custom_audience(account_id, access_token,
                                                                              pixel_id, action_web, day)
                time.sleep(60)
                create_lookalike_audience(account_id, access_token, custom_id, custom_name)
                time.sleep(60)
            for action_ig in actions_instagram:
                custom_id, custom_name = create_instagram_action_custom_audience(account_id, access_token,
                                                                                 ig_account, action_ig, day)
                time.sleep(60)
                create_lookalike_audience(account_id, access_token, custom_id, custom_name)
                time.sleep(60)

            custom_id, custom_name = create_website_ALL_VISITORS_custom_audience(account_id, pixel_id,
                                                                                 access_token, day)
            time.sleep(60)
            create_lookalike_audience(account_id, access_token, custom_id, custom_name)

        return True
    except FacebookError:
        return False


if __name__ == "__main__":
    token = "<ACCESS_TOKEN>"
    _id = create_facebook_action_custom_audience(account_id="act_341908961125102",
                                                 page_id="1488150164825664",
                                                 action_name="page_engaged",
                                                 access_token=token)
