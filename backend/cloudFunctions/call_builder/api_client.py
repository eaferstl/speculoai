import requests
import logging
from config import config
from secret_manager import access_secret_version

def send_bland_ai_request(payload):
    url = config.get('bland_ai_url', "https://isa.bland.ai/v1/calls")
    project_id = config.get('project_id')#NOT WORKING
    print (payload) #Debugging Payload
    api_key = access_secret_version('heyisaai', 'bland-api-key') #hard coded the project ID
    
    if not api_key:
        logging.error("Failed to retrieve Bland AI API key from Secret Manager")
        return None

    headers = {
        "authorization": f"{api_key}",
        "Content-Type": "application/json",
        "encrypted_key": payload.get('encrypted_key')
    }

    print(f"Sending request to Bland AI. URL: {url}")
    print(f"Request headers: {headers}")
    print(f"Request payload: {payload}")

    try:
        response = requests.post(url, json=payload, headers=headers)
        logging.info(f"Received response from Bland AI. Status code: {response.status_code}")
        logging.debug(f"Response content: {response.text}")
        return response
    except requests.RequestException as e:
        logging.error(f"Error sending request to Bland AI: {str(e)}")
        return None