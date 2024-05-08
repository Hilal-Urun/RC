import os
from marketing.shared import get_completion, extract_hashtags_return_text2


def generate_text(text, max_tokens=150, temprature=0.7):
    prompt=text+"\n Response should be in italian language. Use also emojies only when needed please AND create " \
                "hastags about the generated text end of the response. "
    response = get_completion(prompt=prompt,temperature=temprature)
    return response


class ad_copy_4personas:
    def __init__(self, goal, age):
        self.goal = goal
        self.age = age

    def complete_text(self):
        try:
            ad_text = generate_text(
                f"write an add text for {self.goal} at our restaurant for people age between {self.age}", 0.7)
        except:
            ad_text = generate_text(
                f"write an add text for {self.goal} at our restaurant for people age between {self.age} in short",
                 0.7)
        hashtags,ad_text_ = extract_hashtags_return_text2(ad_text)
        return {"text": ad_text_, "hashtags": hashtags}

