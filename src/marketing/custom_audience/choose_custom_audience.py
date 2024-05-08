import pandas as pd
import os

from marketing import db

current_directory = os.path.dirname(os.path.realpath(__file__))
df = pd.read_csv(f"{current_directory}/custom_audience_quality_score.csv", delimiter=";")


def get_best_audiences(account_id, goal, how_many=5):
    custom_audiences = db.audiences.find_one({"account_id": account_id}).get("custom_audiences")
    if custom_audiences is None:
        return None, False

    weight_list = list(map(lambda ca: total_weight(ca, goal), custom_audiences))
    custom_audience_weight_list = []
    for ca, w in zip(custom_audiences, weight_list):
        custom_audience_weight_list.append({"data": ca, "weight": w})
    custom_audience_weight_list.sort(key=lambda ca: ca["weight"], reverse=True)

    if custom_audience_weight_list[0]["weight"] >= 12:
        good_ca = True
    else:
        good_ca = False

    best_ca = [ca["data"] for ca in custom_audience_weight_list][:how_many]

    return {"custom_audiences": [{"id": ca["id"]} for ca in best_ca]}, good_ca


def get_all_custom_audiences(account_id):
    audiences = db.audiences.find_one({"account_id": account_id})
    if audiences is None:
        return None
    custom_audiences = audiences.get("custom_audiences", [])
    id_list = [ca["id"] for ca in custom_audiences]
    if len(id_list) == 0:
        return None
    else:
        return {"custom_audiences": [{"id": _id} for _id in id_list]}


def total_weight(custom_audience: dict, goal: str) -> float:
    # handling the case of conversions goal, excluding <10 days custom audience
    if goal == "CONVERSIONS":
        freshness_weight = custom_audience["freshness_weight"]
        if freshness_weight == 2:
            return 0

    return custom_audience["number_weight"] * custom_audience["freshness_weight"] * custom_audience.get(goal, 1)
