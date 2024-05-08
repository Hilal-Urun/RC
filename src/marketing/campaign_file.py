""" In this module there are some functions regarding facebook campaigns """
import os
import logging

import numpy as np
import pandas as pd
import requests
from facebook_business.adobjects.ad import Ad as FacebookAd
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.adobjects.adcreative import AdCreative
from facebook_business.adobjects.adcreativelinkdata import AdCreativeLinkData
from facebook_business.adobjects.adcreativelinkdatachildattachment import AdCreativeLinkDataChildAttachment
from facebook_business.adobjects.adcreativeobjectstoryspec import AdCreativeObjectStorySpec
from facebook_business.adobjects.adcreativevideodata import AdCreativeVideoData
from facebook_business.adobjects.adimage import AdImage
from facebook_business.adobjects.adset import AdSet
from facebook_business.adobjects.campaign import Campaign as FacebookCampaign
from facebook_business.adobjects.page import Page
from facebook_business.adobjects.targeting import Targeting
from facebook_business.api import FacebookAdsApi
from facebook_business.exceptions import FacebookError

from marketing.utils import fit_data
from marketing.data_from_user import get_radius_for_user


class Ad:
    def __init__(self, facebook_ad, copy, creative, call_to_action):
        self._facebook_ad = facebook_ad
        self._copy = copy
        self._creative = creative
        self._call_to_action = call_to_action

    def get_facebook_ad(self):
        return self._facebook_ad

    def get_copy(self):
        return self._copy

    def get_creative(self):
        return self._creative

    def get_call_to_action(self):
        return self._call_to_action

    def get_insights(self):
        ad = self._facebook_ad
        try:
            insights = ad.get_insights(fields=["cost_per_conversion", "ctr", "impressions"],
                                       params={"date_preset": "last_30d"})[0].export_all_data()

        except FacebookError:
            logging.exception("")
            insights = {}

        if "impressions" in list(insights.keys()):
            if int(insights["impressions"]) < 1000:
                print("The ad need to run longer")
                return pd.DataFrame()
            else:
                insights = cost_per_conversion_to_dict(insights)
                insights["impressions"] = int(insights["impressions"])
                insights["ctr"] = float(insights["ctr"])
                return pd.DataFrame(insights)
        else:
            return pd.DataFrame()


def set_name(facebook_campaign):
    """ This method set the name of the campaign """
    if facebook_campaign is None:
        return ""
    else:
        try:
            name = facebook_campaign.api_get(fields=["name"])["name"]
        except FacebookError:
            logging.exception("")
            name = ""

    return name


def set_daily_budget(adset):
    """ This method set the daily budget of the adset inside the campaign """
    if adset is None:
        daily_budget = 0
    else:
        try:
            daily_budget = int(adset.api_get(fields=["daily_budget"])["daily_budget"])
        except FacebookError:
            logging.exception("")
            daily_budget = 0

    return daily_budget


def set_duration(adset):
    """ This method set the duration (in seconds) of the campaign """
    if adset is None:
        duration = 0
    else:
        try:
            response = adset.api_get(fields=["start_time", "end_time"], params={"date_format": "U"})
            start_time = int(response['start_time'])
            end_time = int(response['end_time']) if "end_time" in response.keys() else 14
            duration = (end_time - start_time) / 86400

        except FacebookError:
            logging.exception("")
            duration = 0

    return duration


def set_campaign_objective(facebook_campaign):
    """ This method set the campaign objective """
    if facebook_campaign is None:
        campaign_objective = ""
    else:
        try:
            campaign_objective = \
                facebook_campaign.api_get(fields=["objective"])["objective"]
        except FacebookError:
            logging.exception("")
            campaign_objective = ""

    return campaign_objective


def set_adsets(facebook_campaign):
    """ This method set the adset """
    if facebook_campaign is None:
        adsets = []
    else:
        try:
            adsets = list(facebook_campaign.get_ad_sets())
        except FacebookError:
            logging.exception("")
            adsets = []

    return adsets


def set_adset_goal(adset):
    """ This method set the optimization goal of the adset """
    if adset is None:
        adset_goal = ""
    else:
        try:
            adset_goal = adset.api_get(fields=["optimization_goal"])["optimization_goal"]
        except FacebookError:
            logging.exception("")
            adset_goal = ""

    return adset_goal


class Campaign:
    """ This class defines a campaign and there are methods
    for budget and duration optimisation, to get the best ads
    inside a campaign and to get insights """

    def __init__(self, facebook_campaign, access_token, account_id, name=None,
                 campaign_objective=None, daily_budget=None, duration=None, adsets=None):

        FacebookAdsApi.init(access_token=access_token)

        if isinstance(facebook_campaign, FacebookCampaign):

            self._facebook_campaign = facebook_campaign
            if adsets is None:
                self._adsets = set_adsets(facebook_campaign)
                adsets = self._adsets
            else:
                self._adsets = adsets
            self._ads = []
            self._account_id = account_id

            if name is None:
                self.name = set_name(facebook_campaign)
            else:
                self.name = name

            if campaign_objective is None:
                self._campaign_objective = set_campaign_objective(facebook_campaign)
            else:
                self._campaign_objective = campaign_objective

            if len(adsets) != 0:
                self._adset_goal = set_adset_goal(adsets[0])
            else:
                self._adset_goal = ""

            if daily_budget is None:
                if len(adsets) != 0:
                    self._daily_budget = set_daily_budget(adsets[0])
                else:
                    self._daily_budget = 0
            else:
                self._daily_budget = daily_budget

            if duration is None:
                if len(adsets) != 0:
                    self._duration = set_duration(adsets[0])
                else:
                    self._duration = 0
            else:
                self._duration = duration

        else:
            print("You must pass a facebook campaign class")
            self._facebook_campaign = None
            self._adsets = []
            self.name = ""
            self._daily_budget = 0
            self._duration = 0
            self._custom_audience = None
            self._buyer_persona = None
            self._geo_zone = None
            self._campaign_objective = ""
            self._adset_goal = ""
            self._ads = []
            self._metrics = []  # metrics is an array of dictionary with type and value

    # set methods

    def set_custom_audience(self, custom_audience):
        self._custom_audience = custom_audience

    def set_buyer_persona(self, buyer_persona):
        self._buyer_persona = buyer_persona

    def set_geo_zone(self, geo_zone):
        self._geo_zone = geo_zone

    def set_metrics(self, metrics):
        self._metrics = metrics

    def add_metric(self, name, value):
        self._metrics[name] = value

    # get methods

    def get_facebook_campaign(self):
        return self._facebook_campaign

    def get_facebook_campaign_id(self):

        if "id" in list(self._facebook_campaign.keys()):
            return self._facebook_campaign["id"]
        else:
            return ""

    def get_ads(self):
        return self._ads

    def get_name(self):
        return self.name

    def get_daily_budget(self):
        return self._daily_budget

    def get_duration(self):
        return self._duration

    def get_custom_audience(self):
        return self._custom_audience

    def get_buyer_persona(self):
        return self._buyer_persona

    def get_geo_zone(self):
        return self._geo_zone

    def get_campaign_objective(self):
        return self._campaign_objective

    def get_adset_goal(self):
        return self._adset_goal

    def get_adsets(self):
        return self._adsets

    def get_metrics(self):
        return self._metrics

    ############################

    def create_adset(self, user_id, adset_name, facebook_interests, address, age_min, age_max,
                     start_time, end_time, budget=None, pixel_id=None, flexible_spec=None):

        adset_goal = get_optimization_goal_from_objective(self._campaign_objective)

        campaign_id = self._facebook_campaign['id']
        account_id = self._account_id

        interests = []

        for interest in facebook_interests:
            if 6009999999999 > int(interest["id_facebook_interest"]) > 6000000000000:
                item = {
                    "name": interest["name_facebook_interest"],
                    "id": int(interest['id_facebook_interest'])
                }
                interests.append(item)

        try:
            daily_budget = self._daily_budget if budget is None else budget

            # for getting the delivery radius for the user
            try:
                radius = get_radius_for_user(user_id, adset_name.split(" ")[1])
                logging.exception("")
            except Exception:
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

            if len(interests) != 0 and flexible_spec is None:
                params = {
                    AdSet.Field.status: "ACTIVE",
                    AdSet.Field.name: adset_name,
                    AdSet.Field.campaign_id: campaign_id,
                    AdSet.Field.daily_budget: daily_budget,
                    AdSet.Field.billing_event: AdSet.BillingEvent.impressions,
                    AdSet.Field.optimization_goal: adset_goal,
                    AdSet.Field.bid_strategy: "LOWEST_COST_WITHOUT_CAP",
                    AdSet.Field.start_time: start_time,
                    AdSet.Field.end_time: end_time,
                    AdSet.Field.targeting: {
                        Targeting.Field.geo_locations: geo_locations,
                        Targeting.Field.flexible_spec: [
                            {
                                "interests": interests
                            }
                        ],
                        Targeting.Field.age_min: age_min,
                        Targeting.Field.age_max: age_max,
                    }
                }

            elif len(interests) == 0 and flexible_spec is None:
                params = {
                    AdSet.Field.status: "ACTIVE",
                    AdSet.Field.name: adset_name,
                    AdSet.Field.campaign_id: campaign_id,
                    AdSet.Field.daily_budget: daily_budget,
                    AdSet.Field.billing_event: AdSet.BillingEvent.impressions,
                    AdSet.Field.optimization_goal: adset_goal,
                    AdSet.Field.bid_strategy: "LOWEST_COST_WITHOUT_CAP",
                    AdSet.Field.start_time: start_time,
                    AdSet.Field.end_time: end_time,
                    AdSet.Field.targeting: {
                        Targeting.Field.geo_locations: geo_locations,
                        Targeting.Field.age_min: age_min,
                        Targeting.Field.age_max: age_max,
                    },
                }

            else:
                params = {
                    AdSet.Field.status: "ACTIVE",
                    AdSet.Field.name: adset_name,
                    AdSet.Field.campaign_id: campaign_id,
                    AdSet.Field.daily_budget: daily_budget,
                    AdSet.Field.billing_event: AdSet.BillingEvent.impressions,
                    AdSet.Field.optimization_goal: adset_goal,
                    AdSet.Field.bid_strategy: "LOWEST_COST_WITHOUT_CAP",
                    AdSet.Field.start_time: start_time,
                    AdSet.Field.end_time: end_time,
                    AdSet.Field.targeting: {
                        Targeting.Field.geo_locations: geo_locations,
                        Targeting.Field.age_min: age_min,
                        Targeting.Field.age_max: age_max,
                        Targeting.Field.flexible_spec: flexible_spec,
                    },
                }

            if "VISUALIZZAZIONE MENU" in self.name and pixel_id is not None:
                params[AdSet.Field.promoted_object] = {
                    "custom_event_str": "MenuPage",
                    "custom_event_type": "OTHER",
                    "pixel_id": pixel_id
                }
            elif "DELIVERY" in self.name and pixel_id is not None:
                params[AdSet.Field.promoted_object] = {
                    "custom_event_str": "DeliveryPage",
                    "custom_event_type": "OTHER",
                    "pixel_id": pixel_id
                }
            elif "PRENOTAZIONI" in self.name and pixel_id is not None:
                params[AdSet.Field.promoted_object] = {
                    "custom_event_str": "BookingPage",
                    "custom_event_type": "OTHER",
                    "pixel_id": pixel_id
                }

            adset = AdAccount(account_id).create_ad_set(params=params)
            self._adsets.append(adset)
            return adset["id"]

        except FacebookError:
            return None
        except Exception:
            return None

    def get_insights_campaign(self):

        """ This function returns a dataframe with number of user, their age and their gender.
        The aim is to get the profile of the most common user who interacted with a campaign """

        campaign = self._facebook_campaign

        fields = ['impressions', 'reach', 'cpm', 'cpp']
        params = {
            "breakdowns": ["age", "gender"],
            "action_attribution_windows": ["1d_click", "7d_view"],
            "date_preset": "last_30d"
        }

        insights = campaign.get_insights(fields=fields, params=params)

        df_response = pd.DataFrame(insights)

        df_response['impressions'] = df_response['impressions'].astype(int)
        df_response['reach'] = df_response['reach'].astype(int)
        df_response['cpm'] = df_response['cpm'].astype(float)
        df_response['cpp'] = df_response['cpp'].astype(float)

        df_less = df_response.loc[df_response['impressions'] > 10]
        df_less.sort_values('cpm', inplace=True)

        return df_less

    def create_ad_creative_image(self, copy, image, call_to_action_type, link,
                                 name, status, page_id, instagram_id, pixel_id, page_token, access_token):
        """ This method create an ad creative within an adset """
        for adset in self._adsets:
            adset_id = adset["id"]
            FacebookAdsApi.init(access_token=page_token)
            page = Page(page_id)
            page_name = page.api_get(fields=["name"])["name"]

            link_data = AdCreativeLinkData()
            link_data[AdCreativeLinkData.Field.message] = copy
            link_data[AdCreativeLinkData.Field.link] = link
            link_data[AdCreativeLinkData.Field.picture] = image
            link_data[AdCreativeLinkData.Field.name] = page_name

            call_to_action = {
                'type': call_to_action_type,
                'value': {
                    'link': link
                },
            }

            link_data[AdCreativeLinkData.Field.call_to_action] = call_to_action

            object_story_spec = AdCreativeObjectStorySpec()
            object_story_spec[AdCreativeObjectStorySpec.Field.page_id] = page_id
            object_story_spec[AdCreativeObjectStorySpec.Field.link_data] = link_data

            params = {
                AdCreative.Field.name: "AdCreative image " + page_name + ', ' + self.name,
                AdCreative.Field.object_story_spec: object_story_spec
            }

            if instagram_id is not None:
                params[AdCreative.Field.instagram_actor_id] = instagram_id

            FacebookAdsApi.init(access_token=access_token)

            creative = AdAccount(self._account_id).create_ad_creative(params=params)

            params_ad = {
                FacebookAd.Field.name: "Ad image " + name,
                FacebookAd.Field.adset_id: adset_id,
                FacebookAd.Field.creative: {'creative_id': creative['id']},
                FacebookAd.Field.status: status
            }

            if pixel_id is not None:
                params_ad[FacebookAd.Field.tracking_specs] = \
                    [
                        {
                            "action.type": [
                                "offsite_conversion"
                            ],
                            "fb_pixel": [
                                pixel_id
                            ]
                        }
                    ]

            facebook_ad = AdAccount(self._account_id).create_ad(params=params_ad)
            copy = copy
            creative = image
            call_to_action = call_to_action_type

            ad = Ad(facebook_ad=facebook_ad, copy=copy, creative=creative, call_to_action=call_to_action)
            self._ads.append(ad)

    def create_ad_creative_carousel(self, copy, images_and_links, single_link,
                                    call_to_action_type, name, status, page_id):
        """ This method create a carousel with image and link and a call to action and a message.
        images_and_links is an array of dictionary like the following one:
        images_and_links = [
            {'image': image_hash,
             'link': link}, ...
             ]
            """
        for adset in self._adsets:
            adset_id = adset["id"]
            products = []

            page = Page(page_id)
            page_name = page.api_get(fields=["name"])["name"]

            for image_and_link in images_and_links:
                image = image_and_link['image']
                link = image_and_link['link']

                _product = AdCreativeLinkDataChildAttachment()
                _product[AdCreativeLinkDataChildAttachment.Field.link] = link
                _product[AdCreativeLinkDataChildAttachment.Field.name] = page_name
                _product[AdCreativeLinkDataChildAttachment.Field.picture] = image

                products.append(_product)

            call_to_action = {"type": call_to_action_type}

            link_data = AdCreativeLinkData()
            link_data[link_data.Field.child_attachments] = products
            link_data[link_data.Field.call_to_action] = call_to_action
            link_data[link_data.Field.message] = copy
            link_data[link_data.Field.link] = single_link

            object_story_spec = AdCreativeObjectStorySpec()
            object_story_spec[object_story_spec.Field.page_id] = page_id
            object_story_spec[object_story_spec.Field.link_data] = link_data

            params = {
                AdCreative.Field.name: "AdCreative carousel " + page_name + ', ' + self.name,
                AdCreative.Field.object_story_spec: object_story_spec
            }

            creative = AdAccount(self._account_id).create_ad_creative(params=params)

            params = {
                FacebookAd.Field.name: "Ad carousel " + name,
                FacebookAd.Field.adset_id: adset_id,
                FacebookAd.Field.creative: {'creative_id': creative['id']},
                FacebookAd.Field.status: status
            }

            facebook_ad = AdAccount(self._account_id).create_ad(params=params)
            copy = copy
            creative = images_and_links
            call_to_action = call_to_action_type

            ad = Ad(facebook_ad=facebook_ad, copy=copy, creative=creative, call_to_action=call_to_action)
            self._ads.append(ad)

    def create_ad_creative_slideshow(self, copy, slideshow_id, image,
                                     link, call_to_action_type, name, status, page_id):
        """ This method creates an ad with a slideshow """
        for adset in self._adsets:
            adset_id = adset["id"]

            page = Page(page_id)
            page_name = page.api_get(fields=["name"])["name"]

            call_to_action = {
                'type': call_to_action_type,
                'value': {
                    'link': link
                },
            }

            video_data = AdCreativeVideoData()
            video_data[AdCreativeVideoData.Field.title] = "Slideshow " + page_name + ", " + self.name
            video_data[AdCreativeVideoData.Field.image_url] = image
            video_data[AdCreativeVideoData.Field.video_id] = slideshow_id
            video_data[AdCreativeVideoData.Field.message] = copy
            video_data[AdCreativeVideoData.Field.call_to_action] = call_to_action

            object_story_spec = AdCreativeObjectStorySpec()
            object_story_spec[AdCreativeObjectStorySpec.Field.page_id] = page_id
            object_story_spec[AdCreativeObjectStorySpec.Field.video_data] = video_data

            params_creative = {
                AdCreative.Field.name: "AdCreative slideshow " + page_name + ', ' + self.name,
                AdCreative.Field.object_story_spec: object_story_spec
            }

            creative = AdAccount(self._account_id).create_ad_creative(params=params_creative)

            params = {
                FacebookAd.Field.name: "Ad slideshow " + name,
                FacebookAd.Field.adset_id: adset_id,
                FacebookAd.Field.creative: {'creative_id': creative['id']},
                FacebookAd.Field.status: status
            }

            facebook_ad = AdAccount(self._account_id).create_ad(params=params)
            copy = copy
            creative = slideshow_id
            call_to_action = call_to_action_type

            ad = Ad(facebook_ad=facebook_ad, copy=copy, creative=creative, call_to_action=call_to_action)
            self._ads.append(ad)

    def create_ad_creative_video(self, access_token, copy, video_url, image, link, call_to_action_type,
                                 name, status, page_id, instagram_id, pixel_id):
        video_id = post_video_on_facebook(video_url, self._account_id, access_token)
        for adset in self._adsets:
            adset_id = adset["id"]

            page = Page(page_id)
            page_name = page.api_get(fields=["name"])["name"]

            call_to_action = {
                'type': call_to_action_type,
                'value': {
                    'link': link
                },
            }

            video_data = AdCreativeVideoData()
            video_data[AdCreativeVideoData.Field.title] = "Video " + page_name + ", " + self.name
            video_data[AdCreativeVideoData.Field.image_url] = image
            video_data[AdCreativeVideoData.Field.video_id] = video_id
            video_data[AdCreativeVideoData.Field.message] = copy
            video_data[AdCreativeVideoData.Field.call_to_action] = call_to_action

            object_story_spec = AdCreativeObjectStorySpec()
            object_story_spec[AdCreativeObjectStorySpec.Field.page_id] = page_id
            object_story_spec[AdCreativeObjectStorySpec.Field.video_data] = video_data

            params_creative = {
                AdCreative.Field.name: "AdCreative video " + page_name + ', ' + self.name,
                AdCreative.Field.object_story_spec: object_story_spec
            }

            if instagram_id is not None:
                params_creative[AdCreative.Field.instagram_actor_id] = instagram_id

            creative = AdAccount(self._account_id).create_ad_creative(params=params_creative)

            params = {
                FacebookAd.Field.name: "Ad slideshow " + name,
                FacebookAd.Field.adset_id: adset_id,
                FacebookAd.Field.creative: {'creative_id': creative['id']},
                FacebookAd.Field.status: status
            }

            if pixel_id is not None:
                params[FacebookAd.Field.tracking_specs] = \
                    [
                        {
                            "action.type": [
                                "offsite_conversion"
                            ],
                            "fb_pixel": [
                                pixel_id
                            ]
                        }
                    ]

            facebook_ad = AdAccount(self._account_id).create_ad(params=params)
            copy = copy
            creative = video_id
            call_to_action = call_to_action_type

            ad = Ad(facebook_ad=facebook_ad, copy=copy, creative=creative, call_to_action=call_to_action)
            self._ads.append(ad)

    def get_best_ads(self, status="ACTIVE"):
        """ This method returns the best ad (or the first two if they have similar results) """

        adset = self._adsets[0]

        ads = list(adset.get_ads(fields=["status"]))

        ads = [ad for ad in ads if ad["status"] == status]

        fields = ['cost_per_conversion', 'ctr', 'impressions']

        params = {
            "date_preset": "last_30d"
        }

        dataframes = []

        for ad in ads:
            insights = ad.get_insights(fields=fields, params=params)[0].export_all_data()

            insights['impressions'] = [int(insights['impressions'])]
            insights['ctr'] = [float(insights['ctr'])]
            insights = cost_per_conversion_to_dict(insights)

            ad_item = insights
            ad_item['ad_id'] = [ad['id']]
            dataframes.append(pd.DataFrame(ad_item))

        df_ads = append_all_dataframes(dataframes)

        conversion_columns = [column_name for column_name in df_ads.columns if "conversion" in column_name]

        sort_columns = conversion_columns + ['ctr']

        df_ads_sorted = df_ads.sort_values(by=sort_columns, ignore_index=True)

        best_ads = []

        first_best_ad = FacebookAd(df_ads_sorted["ad_id"].iloc[0])

        best_ads.append(first_best_ad)

        # if the second-best ad has at least one metric better than the first we keep both of them

        compare_first_two_ads = df_ads_sorted[sort_columns].iloc[0] - df_ads_sorted[sort_columns].iloc[1]

        if (compare_first_two_ads < 0).sum() < len(sort_columns):
            second_best_ad = FacebookAd(df_ads_sorted["ad_id"].iloc[1])

            best_ads.append(second_best_ad)

        return best_ads


###############################################


def get_ads_dataframe(campaign_id, objective, step_of_funnel, date_preset='last_30d'):
    """
    This function is used to get a dataframe with metric
    and ads within a campaign
    """

    campaign = FacebookCampaign(campaign_id)
    params = {
        "level": "ad",
        "breakdowns": ["age", "gender"],
        "action_attribution_windows": ["1d_click", "7d_view"],
        "date_preset": date_preset
    }

    if objective == 'REACH' and step_of_funnel == 'TOFU':
        fields = ['cpm', 'ad_id']

        try:
            insights = list(campaign.get_insights(fields=fields, params=params))

            if len(insights) > 0:
                df_response = pd.DataFrame(insights)
                df_response['cpm'] = df_response['cpm'].astype(float)

                df_response.fillna(0, inplace=True)
                df_response.sort_values('cpm', inplace=True)

                df_less = df_response.loc[df_response['cpm'] != 0]

            else:
                df_less = pd.DataFrame()
                df_response = pd.DataFrame()

            return df_less, df_response

        except FacebookError:
            logging.exception("")
            return pd.DataFrame(), pd.DataFrame()

    elif objective == 'REACH' and step_of_funnel == 'BOFU':

        fields = ['impressions', 'actions', 'action_values', 'spend', 'ad_id']

        try:
            insights = list(campaign.get_insights(fields=fields, params=params))
            if len(insights) > 0:
                insights = actions_to_dict(insights)
                insights = action_values_to_dict(insights)
                df_response = pd.DataFrame(insights)

                df_response['cpm'] = df_response['cpm'].astype(float)
                df_response['impressions'] = df_response['impressions'].astype(int)
                df_response['spend'] = df_response['spend'].astype(float)

                df_response['cost_per_link_click'] = \
                    df_response['spend'] / df_response['link_click']

                df_response['cr_impression'] = \
                    df_response['offsite_conversion.fb_pixel_purchase'] / df_response['impressions']

                df_response['cr_link_click'] = \
                    df_response['offsite_conversion.fb_pixel_purchase'] / df_response['link_click']

                df_response['cpa'] = \
                    df_response['spend'] / df_response['offsite_conversion.fb_pixel_purchase']

                df_response['roas'] = \
                    df_response['offsite_conversion.fb_pixel_purchase_value'] / df_response['spend']

                df_response['average_revenue_per_clic'] = \
                    df_response['offsite_conversion.fb_pixel_purchase_value'] / df_response['link_click']

                df_response.fillna(0, inplace=True)
                df_response.sort_values('cpa', inplace=True)

                columns = ['ad_id', 'cpa', 'roas', 'cost_per_link_click',
                           'cr_impression', 'cr_link_click', 'average_revenue_per_clic']
                df_less = df_response[columns]
                df_less = df_less.loc[df_less['cpa'] != 0]
                df_less = df_less.loc[df_less['cpa'] != np.inf]

            else:
                df_less = pd.DataFrame()
                df_response = pd.DataFrame()

            return df_less, df_response

        except FacebookError:
            logging.exception("")
            return pd.DataFrame(), pd.DataFrame()

    elif objective == 'BRAND_AWARENESS':

        fields = ['cpm', 'ad_id']

        try:
            insights = list(campaign.get_insights(fields=fields, params=params))

            if len(insights) > 0:
                df_response = pd.DataFrame(insights)

                df_response['cpm'] = df_response['cpm'].astype(float)

                df_response.fillna(0, inplace=True)
                df_response.sort_values('cpm', inplace=True)

                df_less = df_response.loc[df_response['cpm'] != 0]

            else:
                df_less = pd.DataFrame()
                df_response = pd.DataFrame()

            return df_less, df_response

        except FacebookError:
            logging.exception("")
            return pd.DataFrame(), pd.DataFrame()

    elif objective == 'MESSAGES':

        fields = ['actions', 'spend', 'ad_id']

        try:

            insights = list(campaign.get_insights(fields=fields, params=params))

            if len(insights) > 0:

                df_response = pd.DataFrame(insights)

                df_response['cost_per_link_click'] = \
                    df_response['spend'] / df_response['link_click']

                df_response.fillna(0, inplace=True)
                df_response.sort_values('cost_per_link_click', inplace=True)

                columns = ['ad_id', 'cost_per_link_click']
                df_less = df_response[columns]
                df_less = df_less.loc[df_less['cost_per_link_click'] != 0]
                df_less = df_less.loc[df_less['cost_per_link_click'] != np.inf]

            else:
                df_less = pd.DataFrame()
                df_response = pd.DataFrame()

            return df_less, df_response

        except FacebookError:
            logging.exception("")
            return pd.DataFrame(), pd.DataFrame()

    elif objective == 'POST_ENGAGEMENT':

        fields = ['cpm', 'actions', 'impressions', 'spend', 'ad_id']

        try:
            insights = list(campaign.get_insights(fields=fields, params=params))

            if len(insights) > 0:
                insights = actions_to_dict(insights)

                df_response = pd.DataFrame(insights)

                df_response['cpm'] = df_response['cpm'].astype(float)
                df_response['impressions'] = df_response['impressions'].astype(int)
                df_response['spend'] = df_response['spend'].astype(float)

                df_response['cost_per_post_engagement'] = df_response['post_engagement'] / df_response['spend']
                df_response['engagement_rate'] = df_response['post_engagement'] / df_response['impressions'] * 100

                df_response.fillna(0, inplace=True)
                df_response.sort_values('cost_per_post_engagement', inplace=True)

                columns = ['ad_id', 'cost_per_post_engagement', 'engagement_rate', 'cpm']
                df_less = df_response[columns]
                df_less = df_less.loc[df_less['cost_per_post_engagement'] != 0]
                df_less = df_less.loc[df_less['cost_per_post_engagement'] != np.inf]

            else:
                df_less = pd.DataFrame()
                df_response = pd.DataFrame()

            return df_less, df_response

        except FacebookError:
            logging.exception("")
            return pd.DataFrame(), pd.DataFrame()

    elif objective == 'APP_INSTALLS':

        # there is to check if the name of offsite_... is correct

        fields = ['ctr', 'spend', 'actions', 'action_values', 'ad_id']

        try:

            insights = list(campaign.get_insights(fields=fields, params=params))

            if len(insights) > 0:

                insights = actions_to_dict(insights)
                insights = action_values_to_dict(insights)

                df_response = pd.DataFrame(insights)

                df_response['ctr'] = df_response['ctr'].astype(float)
                df_response['spend'] = df_response['spend'].astype(float)

                df_response['cost_per_link_click'] = \
                    df_response['spend'] / df_response['link_click']

                df_response['cr_impression'] = \
                    df_response['offsite_conversion.fb_pixel_app_install'] / df_response['impressions']

                df_response['cr_link_click'] = \
                    df_response['offsite_conversion.fb_pixel_app_install'] / df_response['link_click']

                df_response['cpa'] = \
                    df_response['spend'] / df_response['offsite_conversion.fb_pixel_app_install']

                df_response.fillna(0, inplace=True)
                df_response.sort_values('cpa', inplace=True)

                columns = ['ad_id', 'cpa', 'cr_link_click', 'cr_impression',
                           'cost_per_link_click', 'ctr']
                df_less = df_response[columns]
                df_less = df_less.loc[df_less['cpa'] != 0]
                df_less = df_less.loc[df_less['cpa'] != np.inf]

            else:
                df_less = pd.DataFrame()
                df_response = pd.DataFrame()

            return df_less, df_response

        except FacebookError:
            logging.exception("")
            return pd.DataFrame(), pd.DataFrame()

    elif objective == 'VIDEO_VIEWS':

        fields = ['cost_per_thruplay', 'cost_per_2_sec_continuous_video_view',
                  'cpm', 'video_p50_watched_actions', 'ad_id']

        try:

            insights = list(campaign.get_insights(fields=fields, params=params))

            if len(insights) > 0:

                df_response = pd.DataFrame(insights)

                df_response['cost_per_thruplay'] = df_response['cost_per_thruplay'].astype(float)

                df_response['cost_per_2_sec_continuous_video_view'] = \
                    df_response['cost_per_2_sec_continuous_video_view'].astype(float)

                df_response['cpm'] = df_response['cpm'].astype(float)

                df_response['video_p50_watched_actions'] = df_response['video_p50_watched_actions'].astype(float)

                df_response.fillna(0, inplace=True)
                df_response.sort_values('cost_per_thruplay', inplace=True)

                columns = ['ad_id', 'cost_per_thruplay',
                           'cost_per_2_sec_continuous_video_view', 'cpm']
                df_less = df_response[columns]
                df_less = df_less.loc[df_less['cost_per_thruplay'] != 0]
                df_less = df_less.loc[df_less['cost_per_thruplay'] != np.inf]

            else:
                df_less = pd.DataFrame()
                df_response = pd.DataFrame()

            return df_less, df_response

        except FacebookError:
            logging.exception("")
            return pd.DataFrame(), pd.DataFrame()

    elif objective == 'LEAD_GENERATION':

        fields = ['spend', 'actions', 'cost_per_action_type', 'ctr', 'ad_id']

        try:
            insights = list(campaign.get_insights(fields=fields, params=params))

            if len(insights) > 0:

                insights = cost_per_action_to_dict(insights)
                insights = actions_to_dict(insights)

                df_response = pd.DataFrame(insights)

                df_response['ctr'] = df_response['ctr'].astype(float)
                df_response['spend'] = df_response['spend'].astype(float)

                df_response['cost_per_link_click'] = \
                    df_response['spend'] / df_response['link_click']

                df_response.fillna(0, inplace=True)
                df_response.sort_values('cost_per_lead', inplace=True)

                columns = ['ad_id', 'cost_per_lead', 'cost_per_link_click', 'ctr']
                df_less = df_response[columns]
                df_less = df_less.loc[df_less['cost_per_lead'] != 0]
                df_less = df_less.loc[df_less['cost_per_lead'] != np.inf]

            else:
                df_less = pd.DataFrame()
                df_response = pd.DataFrame()

            return df_less, df_response

        except FacebookError:
            logging.exception("")
            return pd.DataFrame(), pd.DataFrame()

    elif objective in ['CONVERSIONS', 'PRODUCT_CATALOG_SALES'] and step_of_funnel == "TOFU":

        fields = ['ctr', 'impressions', 'actions', 'action_values', 'spend', 'ad_id']

        try:
            insights = list(campaign.get_insights(fields=fields, params=params))

            if len(insights) > 0:

                insights = actions_to_dict(insights)
                insights = action_values_to_dict(insights)

                df_response = pd.DataFrame(insights)

                df_response['ctr'] = df_response['ctr'].astype(float)
                df_response['impressions'] = df_response['impressions'].astype(int)
                df_response['spend'] = df_response['spend'].astype(float)

                df_response['cr_view_content/impressions'] = \
                    df_response['view_content'] / df_response['impressions']

                df_response['cr_view_content/link_click'] = \
                    df_response['view_content'] / df_response['link_click']

                df_response['cpa_view_content'] = \
                    df_response['spend'] / df_response['view_content']

                df_response['cpa_purchase'] = \
                    df_response['spend'] / df_response['offsite_conversion.fb_pixel_purchase']

                df_response['roas'] = \
                    df_response['offsite_conversion.fb_pixel_purchase_value'] / df_response['spend']

                df_response.fillna(0, inplace=True)
                df_response.sort_values('cpa_view_content', inplace=True)

                columns = ['ad_id', 'cpa_view_content', 'cr_view_content/link_click',
                           'cr_view_content/impressions', 'ctr', 'cpa_purchase', 'roas']
                df_less = df_response[columns]
                df_less = df_less.loc[df_less['cpa_view_content'] != 0]
                df_less = df_less.loc[df_less['cpa_view_content'] != np.inf]

            else:
                df_less = pd.DataFrame()
                df_response = pd.DataFrame()

            return df_less, df_response

        except FacebookError:
            logging.exception("")
            return pd.DataFrame(), pd.DataFrame()

    elif objective in ['CONVERSIONS', 'PRODUCT_CATALOG_SALES'] and step_of_funnel == "MOFU":

        fields = ['ctr', 'impressions', 'actions', 'action_values', 'spend', 'ad_id']

        try:

            insights = list(campaign.get_insights(fields=fields, params=params))

            if len(insights) > 0:

                insights = actions_to_dict(insights)
                insights = action_values_to_dict(insights)

                df_response = pd.DataFrame(insights)

                df_response['ctr'] = df_response['ctr'].astype(float)
                df_response['impressions'] = df_response['impressions'].astype(int)
                df_response['spend'] = df_response['spend'].astype(float)

                df_response['cost_per_link_click'] = \
                    df_response['spend'] / df_response['link_click']

                # conversion rate add to cart
                df_response['cr_add_to_cart/impressions'] = \
                    df_response['offsite_conversion.fb_pixel_add_to_cart'] / df_response['impressions']

                df_response['cr_add_to_cart/link_click'] = \
                    df_response['offsite_conversion.fb_pixel_add_to_cart'] / df_response['link_click']

                df_response['cr_add_to_cart_value/impressions'] = \
                    df_response['offsite_conversion.fb_pixel_add_to_cart_value'] / df_response['impressions']

                df_response['cr_add_to_cart_value/link_click'] = \
                    df_response['offsite_conversion.fb_pixel_add_to_cart_value'] / df_response['link_click']

                # conversion rate initiate checkout
                df_response['cr_initiate_checkout/impressions'] = \
                    df_response['offsite_conversion.fb_pixel_initiate_checkout'] / df_response['impressions']

                df_response['cr_initiate_checkout/link_click'] = \
                    df_response['offsite_conversion.fb_pixel_initiate_checkout'] / df_response['link_click']

                df_response['cr_initiate_checkout_value/impressions'] = \
                    df_response['offsite_conversion.fb_pixel_initiate_checkout_value'] / df_response['impressions']

                df_response['cr_initiate_checkout_value/link_click'] = \
                    df_response['offsite_conversion.fb_pixel_initiate_checkout_value'] / df_response['link_click']

                # cpa add to cart

                df_response['cpa_add_to_cart'] = \
                    df_response['spend'] / df_response['offsite_conversion.fb_pixel_add_to_cart']

                # cpa initiate checkout
                df_response['cpa_initiate_checkout'] = \
                    df_response['spend'] / df_response['offsite_conversion.fb_pixel_initiate_checkout']

                # cr purchase
                df_response['cr_purchase/impressions'] = \
                    df_response['offsite_conversion.fb_pixel_purchase'] / df_response['impressions']

                df_response['cr_purchase/link_click'] = \
                    df_response['offsite_conversion.fb_pixel_purchase'] / df_response['link_click']

                df_response['cr_purchase_value/impressions'] = \
                    df_response['offsite_conversion.fb_pixel_purchase_value'] / df_response['impressions']

                df_response['cr_purchase_value/link_click'] = \
                    df_response['offsite_conversion.fb_pixel_purchase_value'] / df_response['link_click']

                # cpa purchase and roas

                df_response['cpa_purchase'] = \
                    df_response['spend'] / df_response['offsite_conversion.fb_pixel_purchase']

                df_response['roas'] = \
                    df_response['offsite_conversion.fb_pixel_purchase_value'] / df_response['spend']

                df_response.fillna(0, inplace=True)
                df_response.sort_values('cpa_add_to_cart', inplace=True)
                columns = ['ad_id', 'cpa_add_to_cart', 'cpa_initiate_checkout', 'cr_add_to_cart/link_click',
                           'cr_initiate_checkout/link_click', 'cpa_purchase', 'cr_purchase/link_click',
                           'roas', 'cost_per_link_click', 'ctr']
                df_less = df_response[columns]
                df_less = df_less.loc[df_less['cpa_add_to_cart'] != 0]
                df_less = df_less.loc[df_less['cpa_add_to_cart'] != np.inf]

            else:
                df_less = pd.DataFrame()
                df_response = pd.DataFrame()

            return df_less, df_response

        except FacebookError:
            logging.exception("")
            return pd.DataFrame(), pd.DataFrame()

    elif objective in ['CONVERSIONS', 'PRODUCT_CATALOG_SALES'] and step_of_funnel == "BOFU":

        fields = ['ctr', 'impressions', 'actions', 'action_values', 'spend', 'ad_id']

        try:

            insights = list(campaign.get_insights(fields=fields, params=params))

            if len(insights) > 0:

                insights = actions_to_dict(insights)
                insights = action_values_to_dict(insights)

                df_response = pd.DataFrame(insights)

                df_response['ctr'] = df_response['ctr'].astype(float)
                df_response['spend'] = df_response['spend'].astype(float)

                df_response['cost_per_link_click'] = \
                    df_response['spend'] / df_response['link_click']

                # cr purchase
                df_response['cr_purchase/impressions'] = \
                    df_response['offsite_conversion.fb_pixel_purchase'] / df_response['impressions']

                df_response['cr_purchase/link_click'] = \
                    df_response['offsite_conversion.fb_pixel_purchase'] / df_response['link_click']

                df_response['cr_purchase_value/impressions'] = \
                    df_response['offsite_conversion.fb_pixel_purchase_value'] / df_response['impressions']

                df_response['cr_purchase_value/link_click'] = \
                    df_response['offsite_conversion.fb_pixel_purchase_value'] / df_response['link_click']

                # cpa purchase, roas and average revenue per clic
                df_response['cpa_purchase'] = \
                    df_response['spend'] / df_response['offsite_conversion.fb_pixel_purchase']

                df_response['roas'] = \
                    df_response['offsite_conversion.fb_pixel_purchase_value'] / df_response['spend']

                df_response['average_revenue_per_clic'] = \
                    df_response['offsite_conversion.fb_pixel_purchase_value'] / df_response['link_click']

                df_response.fillna(0, inplace=True)
                df_response.sort_values('roas', ascending=False, inplace=True)
                columns = ['ad_id', 'roas', 'cpa_purchase', 'cr_purchase/link_click',
                           'average_revenue_per_clic', 'cost_per_link_click', 'ctr']
                df_less = df_response[columns]
                df_less = df_less.loc[df_less['roas'] != 0]
                df_less = df_less.loc[df_less['roas'] != np.inf]

            else:
                df_less = pd.DataFrame()
                df_response = pd.DataFrame()

            return df_less, df_response

        except FacebookError:
            logging.exception("")
            return pd.DataFrame(), pd.DataFrame()

    elif objective == 'MESSAGES':

        fields = ['cpm', 'actions', 'ctr', 'spend', 'ad_id']

        try:

            insights = list(campaign.get_insights(fields=fields, params=params))

            if len(insights) > 0:

                insights = cost_per_action_to_dict(insights)

                df_response = pd.DataFrame(insights)

                df_response['cpm'] = df_response['cpm'].astype(float)
                df_response['ctr'] = df_response['ctr'].astype(float)
                df_response['spend'] = df_response['spend'].astype(float)

                df_response['cost_per_link_click'] = \
                    df_response['spend'] / df_response['link_click']

                df_response.fillna(0, inplace=True)
                df_response.sort_values('cpc_link', inplace=True)

                columns = ['ad_id', 'cost_per_link_click', 'cpm', 'ctr']
                df_less = df_response[columns]
                df_less = df_less.loc[df_less['cost_per_link_click'] != 0]
                df_less = df_less.loc[df_less['cost_per_link_click'] != np.inf]

            else:
                df_less = pd.DataFrame()
                df_response = pd.DataFrame()

            return df_less, df_response

        except FacebookError:
            logging.exception("")
            return pd.DataFrame(), pd.DataFrame()
    else:
        print("There is some error in the input")
        return pd.DataFrame()


def actions_to_dict(response):
    """
    This function takes as input a json response and
    returns the "unpacked" response. For example
    > input:  {"x":1, {"type":"actions","var": "y", "val":1}}
    > output: {"x":1,"y":1}
    """
    for i, dato in enumerate(response['data']):
        if 'actions' in dato.keys():
            elem = dato['actions']
            for item in elem:
                key = item['action_type']
                val = item['value']
                response['data'][i][key] = int(val)
    for i, dato in enumerate(response['data']):
        if 'actions' in dato.keys():
            del response['data'][i]['actions']
    return response


def cost_per_action_to_dict(response):
    """
    This function takes as input a json response and
    returns the "unpacked" response. For example
    > input:  {"x":1, {"type":"cost_per_action","var": "y", "val":1}}
    > output: {"x":1,"y":1}
    """
    for i, dato in enumerate(response['data']):
        if 'cost_per_action_type' in dato.keys():
            elem = dato['cost_per_action_type']
            for item in elem:
                key = 'cost_per_' + item['action_type']
                val = item['value']
                response['data'][i][key] = float(val)
    for i, item in enumerate(response['data']):
        if 'cost_per_action_type' in item.keys():
            del response['data'][i]['cost_per_action_type']
    return response


def action_values_to_dict(response):
    """
    This function takes as input a json response and
    returns the "unpacked" response. For example
    > input:  {"x":1, {"type":"action_values","var": "y", "val":1}}
    > output: {"x":1,"y":1}
    """
    for i, dato in enumerate(response['data']):
        if 'action_values' in dato.keys():
            elem = dato['action_values']
            for item in elem:
                key = item['action_type'] + '_value'
                val = item['value']
                response['data'][i][key] = float(val)
    for i, item in enumerate(response['data']):
        if 'action_values' in item.keys():
            del response['data'][i]['action_values']
    return response


def cost_per_conversion_to_dict(insights):
    """ This function takes as input a json response and
    returns the "unpacked" response. For example
    > input:  {"x":1, {"type":"action_values","var": "y", "val":1}}
    > output: {"x":1,"y":1} """
    elem = insights['cost_per_conversion']
    for item in elem:
        key = item['action_type']
        val = item['value']
        insights[key] = [float(val)]

    del insights['cost_per_conversion']
    return insights


def get_step_of_funnel(name):
    words = name.split()
    if "TOFU" in words:
        return "TOFU"
    elif "MOFU" in words:
        return "MOFU"
    elif "BOFU" in words:
        return "BOFU"
    else:
        return ""


def create_campaign(access_token, account_id, name, objective, daily_budget):
    FacebookAdsApi.init(access_token=access_token)
    params = {
        "name": name,
        "objective": objective,
        "status": os.environ.get("PYTHON_ENV") == "prod" and "ACTIVE" or "PAUSED",
        "special_ad_categories": []
    }
    campaign = AdAccount(account_id).create_campaign(params=params)

    new_campaign = Campaign(facebook_campaign=campaign,
                            access_token=access_token,
                            account_id=account_id,
                            name=name,
                            campaign_objective=objective,
                            daily_budget=daily_budget,
                            adsets=[])
    return new_campaign, campaign["id"]


def post_images_on_facebook(image_paths, account_id):
    image_hashes = []

    for image_path in image_paths:
        params = {
            AdImage.Field.filename: image_path
        }
        try:
            image = AdAccount(account_id).create_ad_image(params=params)
            image_hashes.append(image['hash'])
        except FacebookError:
            image_hashes.append(None)

    return image_hashes


def post_slideshow_on_facebook(images_urls, account_id, access_token):
    slideshow_spec = {
        "images_urls": images_urls,
        "duration_ms": 2500,
        "transition_ms": 250
    }
    url = f"https://graph-video.facebook.com/v14.0/{account_id}/advideos?" + \
          f"slideshow_spec={str(slideshow_spec)}&access_token={access_token}"

    response = requests.post(url)

    if response.status_code != 200:
        print(f"Error status code {response.status_code}.")
        if response.status_code == 400:
            message = (response.json())['error']['message']
            code = (response.json())['error']['code']
            print(f"Error: {message}\n Code: %d" % code)

        response_id = None

    else:
        response_id = response.json()['id']

    return response_id


def append_all_dataframes(dataframes):
    df_final = pd.DataFrame()

    for dataframe in dataframes:
        df_final = pd.concat([df_final, dataframe], ignore_index=True)

    return df_final


def get_optimization_goal_from_objective(objective):
    if objective == "APP_INSTALLS":
        return "APP_INSTALLS"
    elif objective == "BRAND_AWARENESS":
        return "AD_RECALL_LIFT"
    elif objective == "CONVERSIONS":
        return "OFFSITE_CONVERSIONS"
    elif objective == "EVENT_RESPONSES":
        return "EVENT_RESPONSES"
    elif objective == "LEAD_GENERATION":
        return "LEAD_GENERATION"
    elif objective == "LINK_CLICKS":
        return "LINK_CLICKS"
    elif objective == "MESSAGES":
        return "CONVERSATIONS"
    elif objective == "PAGE_LIKES":
        return "PAGE_LIKES"
    elif objective == "POST_ENGAGEMENT":
        return "POST_ENGAGEMENT"
    elif objective == "PRODUCT_CATALOG_SALES":
        return "OFFSITE_CONVERSIONS"
    elif objective == "REACH":
        return "REACH"
    elif objective == "VIDEO_VIEWS":
        return "THRUPLAY"


def get_custom_conversions(account_id):
    custom_conversions = AdAccount(account_id).get_custom_conversions(fields=["name"])
    if len(custom_conversions) == 0:
        return []
    else:
        data = [conv.export_all_data() for conv in custom_conversions]
        return data


def get_promoted_object(name, account_id, pixel_id):
    custom_conversions = get_custom_conversions(account_id)
    custom_id = ""

    exists = False
    for custom_conversion in custom_conversions:
        if name == custom_conversion["name"]:
            exists = True
            custom_id = custom_conversion["id"]

    if not exists:
        custom_id = create_custom_conversion(name, account_id, pixel_id)

    promoted_object = {
        "custom_conversion_id": custom_id
    }

    return promoted_object


def get_optimised_daily_budget(goal, df):
    spend_impressions, spend_reach, spend_actions = fit_data(df)
    if goal in ["CONVERSIONS", "VIDEO_VIEWS"]:
        tau = spend_actions[1]
        daily_budget = 0.7 * tau

    elif goal in ["BRAND_AWARENESS", "REACH", "POST_ENGAGEMENT"]:
        tau = spend_reach[1]
        daily_budget = 0.7 * tau

    else:
        tau = spend_impressions[1]
        daily_budget = 0.7 * tau

    return max(daily_budget, 300), spend_impressions


def create_custom_conversion(name, account_id, pixel_id):
    account = AdAccount(account_id)
    if "menu" in name.split("_"):
        params = {
            "name": name,
            "rule": '{"and":[{"url":{"i_contains": "menu"}}]}',
            "event_source_id": pixel_id
        }
        try:
            conversion = account.create_custom_conversion(params=params)
            return conversion["id"]
        except FacebookError:
            return None

    elif "prenota" in name.split("_"):
        params = {
            "name": name,
            "rule": '{"and":[{"url":{"i_contains": "prenota"}}]}',
            "event_source_id": pixel_id
        }
        try:
            conversion = account.create_custom_conversion(params=params)
            return conversion["id"]
        except FacebookError:
            return None

    else:
        return None


def get_campaign_info(campaign_id, access_token):
    FacebookAdsApi.init(access_token=access_token)
    adsets = list(FacebookCampaign(campaign_id).get_ad_sets(fields=["daily_budget", "end_time"]))
    if len(adsets) == 0:
        return None

    daily_budget = 0
    for adset in adsets:
        daily_budget += int(adset["daily_budget"])

    end_time = adsets[0]["end_time"]
    object_story_spec = adsets[0].get_ad_creatives(fields=["object_story_spec"])[0]["object_story_spec"]

    try:
        copy = object_story_spec["link_data"]["message"]
    except KeyError:
        copy = ""

    return copy, daily_budget, end_time


def modify_campaign_with_new_data(account_id, campaign_id, copy, budget, end_date, access_token):
    FacebookAdsApi.init(access_token=access_token)
    if budget or end_date:
        adset_list = list(FacebookCampaign(campaign_id).get_ad_sets())
        for adset in adset_list:
            params = {}
            if budget:
                single_budget = int(budget / len(adset_list))
                params["daily_budget"] = single_budget
            if end_date:
                params["end_time"] = end_date

            adset.api_update(params=params)

    if copy:
        ad_list = list(FacebookCampaign(campaign_id).get_ads())
        for ad in ad_list:
            ad_creative_list = list(ad.get_ad_creatives(fields=["object_story_spec"]))
            for ad_creative in ad_creative_list:
                link_data = ad_creative["object_story_spec"]["link_data"]
                link_data.update({"message": copy})

                object_story_spec = ad_creative["object_story_spec"]
                object_story_spec.update({"link_data": link_data})
                object_story_spec["link_data"].pop("picture", None)

                params = {
                    "name": "AdCreative",
                    "object_story_spec": object_story_spec
                }

                new_creative = AdAccount(account_id).create_ad_creative(params=params)
                ad.api_update(params={"creative": {"creative_id": new_creative["id"]}})
                ad_creative.api_delete()


def post_video_on_facebook(video_url, account_id, access_token):
    FacebookAdsApi.init(access_token=access_token)
    params = {
        "file_url": video_url,
        "title": "Video"
    }

    video = AdAccount(account_id).create_ad_video(params=params)
    return video["id"]
