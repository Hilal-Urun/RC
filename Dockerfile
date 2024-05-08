FROM python:3.10-slim AS setup

ENV PYTHONUNBUFFERED 1
ENV TRANSFORMERS_CACHE "/app/.cache/huggingface"
ENV MPLCONFIGDIR "/app/.cache/matplotlib"
RUN groupadd -r app && useradd --no-log-init -d /app -r -g app app
ARG PYTHON_ENV
ENV PYTHON_ENV $PYTHON_ENV


RUN apt-get update
RUN mkdir -p .cache
RUN chown -R app:app .cache


RUN apt-get install --no-install-recommends -y gcc g++ pkg-config libxmlsec1 libxmlsec1-dev git
RUN pip install --no-cache-dir --upgrade pip wheel setuptools torch~=1.12.1 sentence_transformers~=2.2.2 transformers~=4.22.0 protobuf~=3.20.0

RUN python -c 'import torch; from sentence_transformers import SentenceTransformer; from transformers import AutoTokenizer, AutoModelForSequenceClassification; \
    model = SentenceTransformer("sentence-transformers/all-mpnet-base-v2", device="cpu"); \
    model=AutoTokenizer.from_pretrained("cardiffnlp/twitter-xlm-roberta-base-sentiment")'


FROM setup AS requirements

COPY ../RC/requirements.txt .

RUN pip install git+https://github.com/awais786/python3-saml.git@upgrading-pin-lxml
RUN pip install --no-cache-dir --upgrade -r requirements.txt


FROM requirements AS app

WORKDIR src/app

COPY ../RC/src ./

EXPOSE 8000
RUN python -c 'import nltk; nltk.download("punkt", download_dir="/app/src/marketing/nltk_data")'

RUN mkdir -p /app/src/marketing/nltk_data

RUN chown -R app:app .
ENTRYPOINT ["gunicorn", "--conf", "gunicorn_conf.py","--worker-class=uvicorn.workers.UvicornWorker", "app:app"]
