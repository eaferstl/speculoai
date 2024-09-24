import functions_framework
from flask import jsonify
import json
import os
import re
import google.generativeai as genai
from google.cloud import firestore
import datetime
from google.auth import default
from google.auth.transport.requests import Request
import requests

# Initialize Firestore
db = firestore.Client()

# Get the project ID from the environment variable
project_id = os.environ.get('PROJECT_ID')
if not project_id:
    raise ValueError("PROJECT_ID environment variable is not set")

# Authenticate for Gemini API
scopes = ['https://www.googleapis.com/auth/cloud-platform', 'https://www.googleapis.com/auth/generative-language']
credentials, _ = default(scopes=scopes)
credentials.refresh(Request())

# Configure genai with credentials
genai.configure(credentials=credentials)

@functions_framework.http
def process_lead_email(request):
    print(f"Function started. Using project ID: {project_id}")
    # Parse the payload
    payload = request.get_json()
    print(f"Received payload: {payload}")

    # Extract the email body and client email
    email_body = payload.get('email_body', '')
    client_email = payload.get('client_email', '')
    print(f"Extracted client_email: {client_email}")

    # Process the email to extract lead information
    try:
        lead_info = extract_lead_info(email_body)
        print(f"Extracted lead_info: {lead_info}")
    except Exception as e:
        print(f"Error in extract_lead_info: {str(e)}")
        return jsonify({"error": f"Failed to extract lead info: {str(e)}"}), 500

    # Store the lead information in the database
    try:
        result = store_lead_info(client_email, lead_info)
        print(f"Result from store_lead_info: {result}")
    except Exception as e:
        print(f"Error in store_lead_info: {str(e)}")
        return jsonify({"error": f"Failed to store lead info: {str(e)}"}), 500

    # Return the result as JSON
    return jsonify(result)

def extract_lead_info(email_body):
    print("Starting extract_lead_info")
    # Initialize the Gemini model
    model = genai.GenerativeModel('gemini-1.5-pro')

    # Prepare the prompt
    prompt = f"""
    Extract real estate lead information from the following email body. 
    The email contains details about a potential real estate lead. 
    Extract the following information, if present:
    - First Name
    - Last Name
    - Phone Number (format as a string with just digits)
    - Email Address
    - Any relevant tags or categories (e.g., "buyer", "seller", "investor")
    - Zip Code
    - City
    - State
    - Street Address

    If any field is not found, leave it empty. Be as accurate as possible in extracting the information.
    Return the information as a JSON object with the following structure:

    {{
      "firstName": "",
      "lastName": "",
      "phoneNumber": "",
      "tags": [],
      "email": "",
      "address": {{
        "zip": "",
        "city": "",
        "state": "",
        "street": ""
      }}
    }}

    Email body:
    {email_body}
    """

    print("Sending prompt to Gemini")
    # Generate a response with safety settings
    try:
        safety_settings = {
            'HARM_CATEGORY_DANGEROUS_CONTENT': 'BLOCK_NONE',
            'HARM_CATEGORY_HATE_SPEECH': 'BLOCK_NONE',
            'HARM_CATEGORY_HARASSMENT': 'BLOCK_NONE',
            'HARM_CATEGORY_SEXUALLY_EXPLICIT': 'BLOCK_NONE'
        }

        response = model.generate_content(
            prompt,
            safety_settings=safety_settings,
            generation_config=genai.GenerationConfig(
                temperature=0.2,
                top_p=0.8,
                top_k=40,
            )
        )
        print(f"Received response from Gemini: {response.text}")
    except Exception as e:
        print(f"Error generating content from Gemini: {str(e)}")
        raise
    # Parse the response
    try:
        # Clean up the response text
        clean_response = clean_json_response(response.text)
        print(f"Cleaned response: {clean_response}")
        
        lead_info = json.loads(clean_response)
        
        # Ensure phone number is just digits
        if lead_info.get('phoneNumber'):
            lead_info['phoneNumber'] = ''.join(filter(str.isdigit, lead_info['phoneNumber']))
        
        # Ensure tags is a list
        if isinstance(lead_info.get('tags'), str):
            lead_info['tags'] = [tag.strip() for tag in lead_info['tags'].split(',') if tag.strip()]
        elif not isinstance(lead_info.get('tags'), list):
            lead_info['tags'] = []

        print(f"Final lead_info: {lead_info}")
        return lead_info
    except Exception as e:
        print(f"Error parsing Gemini response: {str(e)}")
        print(f"Response text: {response.text}")
        print(f"Cleaned response: {clean_response}")
        raise

def clean_json_response(response_text):
    print("Starting clean_json_response")
    print(f"Original response text: {response_text}")
    # Find JSON content between triple backticks
    json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response_text)
    if json_match:
        json_content = json_match.group(1)
    else:
        # If no JSON block is found, try to find content between curly braces
        json_match = re.search(r'\{[\s\S]*\}', response_text)
        if json_match:
            json_content = json_match.group(0)
        else:
            print("No JSON content found in the response")
            raise ValueError("No JSON content found in the response")

    # Remove any lines that start with a timestamp
    lines = json_content.split('\n')
    clean_lines = [line for line in lines if not re.match(r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}', line.strip())]
    
    # Join the remaining lines
    clean_text = '\n'.join(clean_lines)
    
    # Instead of removing all non-JSON characters, let's parse the JSON and then re-serialize it
    try:
        json_obj = json.loads(clean_text)
        clean_text = json.dumps(json_obj, ensure_ascii=False)
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {str(e)}")
        raise
    
    print(f"Cleaned JSON: {clean_text}")
    return clean_text.strip()

def store_lead_info(client_email, lead_info):
    print("Starting store_lead_info")
    flow_ref = db.collection('Flows').where('lead_email', '==', client_email).limit(1).get()
    
    if not flow_ref:
        return {"error": "No matching flow found for the given client email"}

    flow_doc = flow_ref[0]
    organization_id = flow_doc.get('organization_id')
    lead_source = flow_doc.get('lead_source')
    flow_id = flow_doc.id

    # Sanitize phone number
    sanitized_phone_number = re.sub("[^0-9]", "", lead_info['phoneNumber'])
    if len(sanitized_phone_number) == 10:
        sanitized_phone_number = '1' + sanitized_phone_number
    elif len(sanitized_phone_number) < 11:
        return {"error": "Phone number is too short"}

    # Check if the lead already exists
    contacts_ref = db.collection('Contacts')
    existing_contact = contacts_ref.where('organization_id', '==', organization_id).where('phoneNumber', '==', sanitized_phone_number).limit(1).get()

    current_time = datetime.datetime.now().isoformat()

    if existing_contact:
        # Update existing contact
        contact_doc = existing_contact[0]
        contact_id = contact_doc.id
        contact_data = contact_doc.to_dict()
        print (contact_data)
        # Check if there's already an active flow
        if 'activeFlows' in contact_data and contact_data['activeFlows'] and len(contact_data['activeFlows']) > 0:
            return {"error": "Contact already has an active flow"}

        # Update the contact with new information and add active flow
        update_data = {
            **lead_info,
            'updatedAt': current_time,
            'activeFlows': [{
                'flow_id': flow_id,
                'flow_name': flow_doc.get('name'),
                'status': 'pending',
                'createdAt': current_time,
                'callCounter': 0,
                'type': 'Convert'
            }]
        }
        contacts_ref.document(contact_id).update(update_data)
    else:
        # Add new contact
        new_contact_data = {
            **lead_info,
            'organization_id': organization_id,
            'lead_source': lead_source,
            'phoneNumber': sanitized_phone_number,
            'phoneStatus': 'active',
            'createdAt': current_time,
            'updatedAt': current_time,
            'activeFlows': [{
                'flow_id': flow_id,
                'flow_name': flow_doc.get('name'),
                'status': 'pending',
                'createdAt': current_time,
                'callCounter': 0,
                'type': 'Convert'
            }]
        }
        new_contact = contacts_ref.add(new_contact_data)
        contact_id = new_contact[1].id

    # Add to flow_contacts subcollection
    flow_contacts_ref = db.collection('Flows').document(flow_id).collection('flow_contacts')
    flow_contacts_ref.document(contact_id).set(lead_info)

    return {
        "success": True,
        "message": "Lead information stored successfully",
        "contact_id": contact_id,
        "flow_id": flow_id
    }

