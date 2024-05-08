import logging
import os
import deepl
from fastapi import FastAPI, Response, Request
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from marketing.add_copy.ad_copy_persona import generate_text
from langdetect import detect
translator = deepl.Translator(os.getenv('DEEPL_AUTH_KEY'))
app = FastAPI()

@app.post("/review_response", status_code=200)
async def generate_review_response(review_json: Request, response: Response):
    review = await review_json.json()
    # Instantiate the sentiment analyzer
    if detect(review["review"]) != 'en':
        tr_review = translator.translate_text(review["review"], target_lang="TR").text
        review = translator.translate_text(tr_review, target_lang="IT").text
    else:
        review = review["review"]
    analyzer = SentimentIntensityAnalyzer()
    sentiment_result = analyzer.polarity_scores(review)
    # Check if the sentiment is positive
    if sentiment_result["compound"] > 0:
        sentiment = "positive"
    # Check if the sentiment is negative
    elif sentiment_result["compound"] < 0:
        sentiment = "negative"
    # If the sentiment is neutral
    else:
        sentiment = "neutral"
    try:
        prompt = "write a response to our customer's comment for our restaurant that will satisfy user." \
                 f"customer comment : {review}." \
                 f"customer comment sentiment is {sentiment}."
        prompt2 = "write a response to our customer's comment for our restaurant that will satisfy user and " \
                  "visit us again." \
                  f"customer comment : {review}." \
                  f"customer comment sentiment is {sentiment}."

        prompt3 = "write a response to our customer's comment for our restaurant that will satisfy user and offer " \
                  "discount if customer visit us again." \
                  f"customer comment : {review}." \
                  f"customer comment sentiment is {sentiment}."

        generated_response = generate_text(prompt, 400, 0.8)
        generated_response2 = generate_text(prompt2, 400, 0.7)
        generated_response3 = generate_text(prompt3, 400, 0.9)
        final_res={1:generated_response,2:generated_response2,3:generated_response3}
        response.status_code = 200
        return {"status": response.status_code, "response": final_res}
    except Exception as e:
        logging.exception(e)
        response.status_code = 500
        return {"status": response.status_code, "error_message": e.__class__.__name__}


def trial(review):
    # Instantiate the sentiment analyzer
    if detect(review) != 'en':
        tr_review = translator.translate_text(review, target_lang="TR").text
        review = translator.translate_text(tr_review, target_lang="IT").text
    analyzer = SentimentIntensityAnalyzer()
    sentiment_result = analyzer.polarity_scores(review)
    # Check if the sentiment is positive
    if sentiment_result["compound"] > 0:
        sentiment = "positive"
    # Check if the sentiment is negative
    elif sentiment_result["compound"] < 0:
        sentiment = "negative"
    # If the sentiment is neutral
    else:
        sentiment = "neutral"
    prompt = "write a response to our customer's comment for our restaurant that will satisfy user." \
             f"customer comment : {review}." \
             f"customer comment sentiment is {sentiment}."
    prompt2 = "write a response to our customer's comment for our restaurant that will satisfy user and " \
              "visit us again." \
              f"customer comment : {review}." \
              f"customer comment sentiment is {sentiment}."

    prompt3 = "write a response to our customer's comment for our restaurant that will satisfy user and offer " \
              "discount if customer visit us again." \
              f"customer comment : {review}." \
              f"customer comment sentiment is {sentiment}."

    generated_response = generate_text(prompt, 400, 0.8)
    generated_response2 = generate_text(prompt2, 400, 0.7)
    generated_response3 = generate_text(prompt3, 400, 0.9)
    return generated_response, generated_response2, generated_response3
