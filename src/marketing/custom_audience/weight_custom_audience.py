import time

import pandas as pd
import os
import logging

from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.customaudience import CustomAudience
from facebook_business.exceptions import FacebookError

from marketing import db, FACEBOOK_GOALS, API_VERSION

current_directory = os.path.dirname(os.path.realpath(__file__))
df_quality_score = pd.read_csv(f"{current_directory}/custom_audience_quality_score.csv",
                               delimiter=";", index_col="name")


def weight_custom_audience(custom_audience, access_token):
    retention_days = custom_audience['retention_days']
    if retention_days == 10:
        custom_audience['freshness_weight'] = 3
    elif retention_days == 30:
        custom_audience['freshness_weight'] = 2
    elif retention_days == 60:
        custom_audience['freshness_weight'] = 1

    FacebookAdsApi.init(access_token=access_token, api_version=API_VERSION)
    ca_data = CustomAudience(custom_audience["id"]).api_get(fields=["delivery_status",
                                                                    "approximate_count_lower_bound"])
    if ca_data["delivery_status"]["code"] != 200:
        custom_audience['number_weight'] = 0
    else:
        if 500 > ca_data["approximate_count_lower_bound"] >= 250:
            custom_audience['number_weight'] = 1
        elif 2000 > ca_data["approximate_count_lower_bound"] >= 500:
            custom_audience['number_weight'] = 2
        elif ca_data["approximate_count_lower_bound"] >= 2000:
            custom_audience['number_weight'] = 3
        else:
            custom_audience['number_weight'] = 0
    for goal in FACEBOOK_GOALS:
        custom_audience[goal] = df_quality_score.loc[custom_audience['name'], goal]

    return custom_audience


def add_weight_to_all_custom_audiences(account_id, access_token, last_processed_index=0):
    custom_audiences = db.audiences.find_one({"account_id": account_id})['custom_audiences']
    df_custom = pd.DataFrame(custom_audiences)
    error_weight = False
    _last_processed_index = last_processed_index
    for i, custom_audience in df_custom.iterrows():
        if i < last_processed_index:
            continue
        try:
            custom_audience_weight = weight_custom_audience(custom_audience, access_token)
            df_custom.iloc[i] = custom_audience_weight
            _last_processed_index += 1
        except FacebookError:
            logging.exception("")
            error_weight = True
            break
        time.sleep(30)

    db.audiences.update_one(
        {
            "account_id": account_id
        },
        {
            "$set": {
                "custom_audiences": df_custom.to_dict('records'),
                "error_weight": error_weight,
                "last_update": int(time.time())
            }
        }
    )
    return _last_processed_index, error_weight


def update_weight_custom_audience(account_id, access_token):
    if db.audiences.find_one({"account_id": account_id})["last_update"] > time.time() - 86400:
        return

    # now we deal only with audiences updated more than a day ago

    error = True
    last_index = 0
    while error:
        last_index, error = add_weight_to_all_custom_audiences(account_id, access_token, last_index)
        time.sleep(300)





