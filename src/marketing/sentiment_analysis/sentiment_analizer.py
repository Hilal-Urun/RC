import os
import re
import logging
from typing import List
import pandas as pd
import requests
from transformers import pipeline
from datetime import datetime, timedelta
from marketing.shared import get_sc_tokenizer, get_sc_model


def preprocess(text):
    if text:
        text = text.lower()
        text = re.sub(r"[^\w\d\s]", "", text)
        text = re.sub(r" +", " ", text)
        text = [w.strip() for w in text.split()]
        text = " ".join(text)
        if not text:
            return ""
    else:
        return ""
    return text


def get_sentiment_list(location_var: str, days_preset: int) -> List:
    def _sentiment_analyser(sentence: str):
        # Load model and tokenizer
        tokenizer = get_sc_tokenizer()
        sc_model = get_sc_model()
        classifier = pipeline("sentiment-analysis", model=sc_model, tokenizer=tokenizer)

        results = classifier([sentence])

        return results[0]["label"]

    def calculate_sentiment(comment):
        if comment:
            comment = _sentiment_analyser(comment)
        else:
            pass
        return comment

    url = f"{os.getenv('gmb_api_aigot')}GetReviews?locationName={location_var}&nextPageToken="
    starting_date = (datetime.now() - timedelta(days=days_preset)).strftime("%Y-%m-%dT%H:%M:%S")

    nextPageToken = "null"

    data_final = pd.DataFrame()
    while True:
        try:
            req = requests.get(url + nextPageToken)
            data = req.json()
            nextPageToken = data["reviews"].get("nextPageToken")
            data = pd.DataFrame(data["reviews"]["reviews"])
            data["createTime"] = pd.to_datetime(data["createTime"])
            data["updateTime"] = pd.to_datetime(data["updateTime"])
            data["comment"] = data["comment"].apply(linearize_comment)
            data["english_comment"] = data["comment"].apply(only_english)
            data["preprocessed_comment"] = data["english_comment"].apply(preprocess)
            data["sentiment"] = data["preprocessed_comment"].apply(calculate_sentiment)

            if not (data["createTime"] > starting_date).all():
                data = data[data["createTime"] > starting_date]
                data_final = pd.concat([data_final, data], ignore_index=True)
                break
            else:
                data_final = pd.concat([data_final, data], ignore_index=True)

        except Exception:
            logging.exception("")
            break

    items_list = []
    negative_counts = 0
    positive_counts = 0
    neutral_counts = 0
    one_star_counts = 0
    two_star_counts = 0
    three_star_counts = 0
    four_star_counts = 0
    five_star_counts = 0

    print(data_final)

    for index, row in data_final.iterrows():
        item = {
            "id": index,
            "location": location_var,
            "starRating": row["starRating"],
            "comment": row["comment"],
            "preprocessed_comment": row["preprocessed_comment"],
            "createTime": row["createTime"],
            "updateTime": row["updateTime"],
            "sentiment": row["sentiment"]
        }

        if "pos" in item["sentiment"].lower():
            positive_counts += 1
        elif "neg" in item["sentiment"].lower():
            negative_counts += 1
        elif "meu" in item["sentiment"].lower():
            neutral_counts += 1

        if item["starRating"].lower() == "one":
            one_star_counts += 1
        elif item["starRating"].lower() == "two":
            two_star_counts += 1
        elif item["starRating"].lower() == "three":
            three_star_counts += 1
        elif item["starRating"].lower() == "four":
            four_star_counts += 1
        elif item["starRating"].lower() == "five":
            five_star_counts += 1
        else:
            pass

        items_list.append(item)

    counts_dict = {
        "comments_positive_counts": positive_counts,
        "comments_negative_counts": negative_counts,
        "comments_neutral_counts": neutral_counts,
        "one_star_counts": one_star_counts,
        "two_star_counts": two_star_counts,
        "three_star_counts": three_star_counts,
        "four_star_counts": four_star_counts,
        "five_star_counts": five_star_counts
    }

    return items_list, counts_dict


def only_english(comment):
    if comment is None:
        return comment
    else:
        if "(Translated by Google)" in comment:
            if "(Original)" in comment:
                return re.search(r"(?<=\(Translated by Google\))(.*)(?=\(Original\))", comment).group(0)
            else:
                return re.search(r"(?<=\(Translated by Google\))(.*)", comment).group(0)
        else:
            return comment


def linearize_comment(comment):
    if isinstance(comment, str):
        return " ".join(comment.splitlines())
    else:
        return None
