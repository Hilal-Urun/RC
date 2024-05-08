import os
import requests
from datetime import datetime, timedelta


def schedule_ad_copy_endpoint():
    current_time = datetime.now()
    next_month = current_time + timedelta(days=30)
    schedule_payload = {
        "request": {
            "url": f"{os.getenv('internal_url')}/schedule_ad_copy",
            "method": "POST",
            "headers": {
                "Content-Type": "application/json"
            }
        },
        "schedule": {
            "at": int(next_month.timestamp()),
            "recurrent": True,
            "recurrencyTime": "1 month"
        }
    }
    response = requests.get(os.getenv("scheduler_url"), json=schedule_payload)

    if response.status_code == 200:
        print(f"Scheduled /schedule_ad_copy endpoint is successfully.")
    else:
        print(f"Failed to schedule /schedule_ad_copy endpoint. Status code: {response.status_code}")


def schedule_social_media_copy_endpoint():
    current_time = datetime.now()
    next_month = current_time + timedelta(days=30)
    schedule_payload = {
        "request": {
            "url": f"{os.getenv('internal_url')}/schedule_social_media_copy",
            "method": "POST",
            "body": {"social media": "Creating social media copies"},
            "headers": {
                "Content-Type": "application/json"
            }
        },
        "schedule": {
            "at": int(next_month.timestamp()),
            "recurrent": True,
            "recurrencyTime": "1 month"
        }
    }
    response = requests.get(os.getenv("scheduler_url"), json=schedule_payload)

    if response.status_code == 200:
        print(f"Scheduled /schedule_social_media_copy endpoint is successfully.")
    else:
        print(f"Failed to schedule /schedule_social_media_copy endpoint. Status code: {response.status_code}")


def schedule_buyer_persona_endpoint():
    current_time = datetime.now()
    next_month = current_time + timedelta(days=30)
    schedule_payload = {
        "request": {
            "url": f"{os.getenv('internal_url')}/schedule_create_buyer_personas_description",
            "method": "POST",
            "body": {"buyer persona": "Creating buyer persona copies"},
            "headers": {
                "Content-Type": "application/json"
            }
        },
        "schedule": {
            "at": int(next_month.timestamp()),
            "recurrent": True,
            "recurrencyTime": "1 month"
        }
    }
    response = requests.get(os.getenv("scheduler_url"), json=schedule_payload)

    if response.status_code == 200:
        print(f"Scheduled /buyer_persona endpoint successfully.")
    else:
        print(f"Failed to schedule /buyer_persona endpoint for. Status code: {response.status_code}")


def schedule_visitatore_endpoint():
    current_time = datetime.now()
    next_month = current_time + timedelta(days=30)

    schedule_payload = {
        "request": {
            "url": f"{os.getenv('internal_url')}/schedule_visitatore_description",
            "method": "POST",
            "body": {"visitatore": "Creating visitatore copies"},
            "headers": {
                "Content-Type": "application/json"
            }
        },
        "schedule": {
            "at": int(next_month.timestamp()),
            "recurrent": True,
            "recurrencyTime": "1 month"
        }
    }
    response = requests.get(os.getenv("scheduler_url"), json=schedule_payload)

    if response.status_code == 200:
        print(f"Scheduled /visitatore endpoint successfully.")
    else:
        print(f"Failed to schedule /visitatore endpoint. Status code: {response.status_code}")
