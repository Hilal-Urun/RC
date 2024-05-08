import os
import re
import openai
from sentence_transformers import SentenceTransformer
from transformers import AutoTokenizer, AutoModelForSequenceClassification

openai.api_key = os.getenv('OPENAI_API_KEY')
st_model = None
sc_tokenizer = None
sc_model = None

def get_st_model() -> SentenceTransformer:
    global st_model
    if st_model is not None:
        return st_model

    st_model = SentenceTransformer("sentence-transformers/all-mpnet-base-v2", device="cpu")
    st_model.eval()
    st_model.share_memory()
    return st_model


def get_sc_tokenizer(model="cardiffnlp/twitter-xlm-roberta-base-sentiment") -> AutoTokenizer:
    global sc_tokenizer
    if sc_tokenizer is not None:
        return sc_tokenizer

    sc_tokenizer = AutoTokenizer.from_pretrained(model)
    return sc_tokenizer


def get_sc_model(model="cardiffnlp/twitter-xlm-roberta-base-sentiment"):
    global sc_model
    if sc_model is not None:
        return sc_model

    sc_model = AutoModelForSequenceClassification.from_pretrained(model)
    sc_model.eval()
    sc_model.share_memory()
    return sc_model


def extract_hashtags_return_text2(text):
    hashtags = re.findall(r'#\w+', text)
    cleaned_text = re.sub(r'#\w+', '', text)
    return hashtags, cleaned_text.strip()


def get_completion(prompt, temperature):
    messages = [{"role": "user", "content": prompt}]
    response = openai.ChatCompletion.create(model="gpt-4-1106-preview", messages=messages,
                                            temperature=float(temperature))
    return response.choices[0].message["content"]


def n_get_completion(prompt, temperature=0.7, n=1):
    messages = [{"role": "user", "content": prompt}]
    response = openai.ChatCompletion.create(model="gpt-4-1106-preview", messages=messages,
                                            temperature=float(temperature), n=n)
    return response.choices
