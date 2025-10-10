#!/usr/bin/env python3
"""Quick test script for Perplexity API"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv('PERPLEXITY_API_KEY')
print(f"API Key loaded: {API_KEY[:10]}..." if API_KEY else "No API key found")

url = "https://api.perplexity.ai/chat/completions"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

payload = {
    "model": "sonar",
    "messages": [
        {"role": "user", "content": "What is aluminum?"}
    ]
}

print(f"\nSending request to: {url}")
print(f"Model: {payload['model']}")

try:
    response = requests.post(url, headers=headers, json=payload, timeout=30)

    print(f"\nStatus code: {response.status_code}")

    if response.status_code != 200:
        print(f"Error response: {response.text}")
    else:
        result = response.json()
        print(f"Success! Response: {result}")

except Exception as e:
    print(f"Exception: {e}")
