import os
import requests
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("SERPER_API_KEY")

print("API Key Loaded:", bool(api_key))

response = requests.post(
    "https://google.serper.dev/search",
    headers={
        "X-API-KEY": api_key,
        "Content-Type": "application/json",
    },
    json={
        "q": "Cherokee Culvert Company Macon GA",
    },
)

print("Status Code:", response.status_code)
print(response.text)