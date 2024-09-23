#Live Production Model

import functions_framework
import json
import requests
from flask import abort, jsonify
import datetime
import os
import re
import time
import random
from bs4 import BeautifulSoup
import pytz

    
import firebase_admin
from firebase_admin import firestore

# Initialize Firebase Admin SDK once globally
if not firebase_admin._apps:
    firebase_admin.initialize_app()

# Firestore client
db = firestore.client()

def get_day_time(timezone_str):
    # Create a timezone object from the given string
    timezone = pytz.timezone(timezone_str)
    
    # Get the current time in the specified timezone
    now = datetime.datetime.now(timezone)
    
    # Determine whether it's morning or afternoon
    if now.hour < 12:
        part_of_day = "morning"
    else:
        part_of_day = "afternoon"
    
    # Get the day of the week (Monday, Tuesday, etc.)
    day_of_week = now.strftime('%A')
    
    return day_of_week, part_of_day

def query_document_by_id(collection, doc_id):
    """Query a single document by its ID and return its data."""
    try:
        doc_ref = db.collection(collection).document(doc_id)
        doc = doc_ref.get()
        if doc.exists:
            doc_data = doc.to_dict()
            return doc_data  # Return the document data including the ID
        else:
            print(f"No document found with ID: {doc_id}")
            return None
    except Exception as e:
        print(f"Error fetching document by ID: {str(e)}")
        return None


def update_contact_flow(contact_id, flow_id, max_attempts):
    """Update the callCounter and move flow between active and finished based on attempts."""
    try:
        contact_ref = db.collection('Contacts').document(contact_id)
        contact_doc = contact_ref.get()
        if contact_doc.exists:
            contact_data = contact_doc.to_dict()
            active_flows = contact_data.get('activeFlows', [])
            finished_flows = contact_data.get('finishedFlows', [])
            
            for flow in active_flows:
                if flow['flow_id'] == flow_id:
                    flow['callCounter'] = flow.get('callCounter', 0) + 1
                    if flow['callCounter'] >= max_attempts:
                        flow['status'] = 'unresponsive'
                        finished_flows.append(flow)
                        active_flows.remove(flow)
                    break
            
            contact_ref.update({
                'activeFlows': active_flows,
                'finishedFlows': finished_flows,
                'lastCallAttempt': datetime.datetime.utcnow().isoformat()
            })
            print(f"Contact {contact_id} updated successfully.")
        else:
            print(f"Contact document {contact_id} does not exist.")
    except Exception as e:
        print(f"Failed to update contact document: {str(e)}")

def format_knowledge_base(knowledge_base):
    """
    Formats the knowledge base entries into a clear, readable Q&A format.
    Assumes knowledge_base is a list of dictionaries with 'question' and 'answer' fields.
    """
    print("Formatting knowledge base...")
    formatted_qa = "Knowledge Base Q&A:\n"
    for entry in knowledge_base:
        question = entry.get('question', 'No question provided')
        answer = entry.get('answer', 'No answer provided')
        formatted_qa += f"Q: {question}\nA: {answer}\n\n"
    print("Knowledge base formatted successfully.")
    return formatted_qa

def process_html(html_content):
    """
    Converts HTML content to plain text. 
    Assumes html_content is a string containing HTML.
    """
    print(f"Processing HTML content: {html_content}")
    soup = BeautifulSoup(html_content, 'html.parser')
    plain_text = soup.get_text(separator='\n')
    print("HTML content processed successfully.")
    return plain_text

def craft_prompt(knowledge_base, rules_and_guidelines, prompt_ref, organization_info, contact_info, call_settings):
    """
    Crafts a dynamic payload for an API call based on input parameters.
    """
    print("Crafting prompt...")

    # Extracting contact info
    print("Extracting and formatting contact information...")
    contact_address = contact_info.get('address',{})
    print(f"Extracted contact address: {contact_address}")

    contact_formatted = {
        'contact_first_name': contact_info.get('firstName', ''),
        'contact_last_name': contact_info.get('lastName', ''),
        'contact_phone': contact_info.get('phoneNumber', ''),
        'contact_email': contact_info.get('email', ''),
        'contact_street': contact_address.get('street',''),
        'contact_city': contact_address.get('city','')
    }

    # Formats the assistant's name and pronunciation based on the organization_info dictionary.
    assistant_formatted = {
        'assistant_name': organization_info.get('assistant_name', ''),
        'assistant_name_pronunciation': organization_info.get('assistant_name_pronunciation', '')
    }

    # Extracts and formats the organization's name from the organization_info dictionary.
    org_formatted = {
        'org_name': organization_info.get('org_name', '')
    }

    # Formatting extracted information
    contact_info_text = f"Contact Name: {contact_info.get('firstName', '')} {contact_info.get('lastName', '')}\n" \
                        f"Phone: {contact_info.get('phoneNumber', '')}\n" \
                        f"Email: {contact_info.get('email', '')}\n" \
                        f"Street: {contact_address.get('street', '')}\n" \
                        f"City: {contact_address.get('city', '')}"
    print("Contact information formatted.")

    assistant_info_text = f"Assistant Name: {organization_info.get('assistant_name', '')}\n" \
                          f"Pronunciation: {organization_info.get('assistant_name_pronunciation', '')}"
    print("Assistant information formatted.")

    org_info_text = f"Organization Name: {organization_info.get('org_name', '')}"
    print("Organization information formatted.")

    # Formatting the knowledge base
    kb_formatted = format_knowledge_base(knowledge_base.get('knowledge_base',''))
    knowledge_base_text = knowledge_base.get('knowledge_base_text','') ###THIS IS NEW

    # Processing prompt components
    prompt_logic = process_html(prompt_ref.get('prompt_logic', ''))
    default_prompt_start = process_html(prompt_ref.get('default_prompt_start', ''))
    prompt_body = process_html(prompt_ref.get('prompt', ''))
    default_prompt_end = process_html(prompt_ref.get('default_prompt_end', ''))
    pathway = prompt_ref.get('pathway_id', None) ####THIS IS NEW


    # Assembling all components
    rules_text = rules_and_guidelines.get('rules_and_guidelines', '') 
    print(f"Rules and guidelines text: {rules_text}")

    all_prompt_components = [
        rules_text, prompt_logic, default_prompt_start, prompt_body, default_prompt_end, org_info_text, 
        contact_info_text, assistant_info_text, kb_formatted
    ]
    print("All prompt components assembled.")

    # Joining components
    prompt_string = '\n'.join(filter(None, all_prompt_components))
    print(f"Final prompt string:\n{prompt_string}")
    
    # Placeholder for default voice settings, potentially to be filled with actual values.
    default_voice_settings = {}

    # Attempts to retrieve 'voice_settings' from call_settings. If not found or not a dictionary, defaults are used.
    try:
        voice_settings = call_settings.get('voice_settings', {})
    except AttributeError:
        print("Voice settings not found or not a dictionary. Using default voice settings.")
        voice_settings = {}
    # Updates the voice settings with default values for any keys not already set.
    for key, default_value in default_voice_settings.items():
        voice_settings.setdefault(key, default_value)
    
    # Print the current voice settings for debugging or information purposes.
    print(f'Voice settings: {voice_settings}')

    # Attempts to retrieve the 'outbound' phone number from organization_info. In case of any exception, defaults to None.
    try:
        phone_numbers = organization_info.get('phoneNumbers', {})
        outbound = phone_numbers.get('outbound', None)
    except Exception as e:
        outbound = None

    transfer_phone_number = call_settings.get('transfer_phone_number', None)
    if transfer_phone_number is not None and len(str(transfer_phone_number)) < 10:
        transfer_phone_number = None

    pathway_transfer = transfer_phone_number

    timezone_str = organization_info.get('timezone', 'US/Central')
    day_of_week, part_of_day = get_day_time(timezone_str)

    first_sentence = (
        f"Hey {contact_info.get('firstName')}, happy {day_of_week} {part_of_day}."
        if contact_info.get('firstName')
        else f"Hey there, happy {day_of_week} {part_of_day}."
    )

    # Constructs the final payload incorporating all formatted data and settings.
    payload = {
        'phone_number': contact_formatted.get('contact_phone', None),  # Contact's phone number
        'pathway_id': pathway, ####THIS IS NEW
        'task': prompt_string,  # The crafted prompt string
        'model': call_settings.get('model', 'enhanced'),  # The model setting, defaulting to 'base'
        'transfer_phone_number': transfer_phone_number,  # Optional transfer phone number
        'answered_by_enabled': call_settings.get('answered_by_enabled', False),  # Whether the 'answered by' feature is enabled
        'encrypted_key': call_settings.get('encrypted_key', None),####THIS IS NEW
        'from': outbound,  # The outbound phone number
        'pronunciation_guide': [  
            {
                "word": "Isa",
                "pronunciation": "ee-suh",
                "case_sensitive": "false",
                "spaced": "true"
            },
            {
                "word": "Ave",
                "pronunciation": "Avenue",
                "case_sensitive": "false",
                "spaced": "true"
            },
            {
                "word": "St",
                "pronunciation": "Street",
                "case_sensitive": "false",
                "spaced": "true"
            },
            {
                "word": "Ln",
                "pronunciation": "Lane",
                "case_sensitive": "false",
                "spaced": "true"
            },
            {
                "word": "Rd",
                "pronunciation": "Road",
                "case_sensitive": "false",
                "spaced": "true"
            },
            {
                "word": "Cv",
                "pronunciation": "Cove",
                "case_sensitive": "false",
                "spaced": "true"
            },
            {
                "word": "Blvd",
                "pronunciation": "Boulevard",
                "case_sensitive": "false",
                "spaced": "true"
            },
            {
                "word": "Hwy",
                "pronunciation": "Highway",
                "case_sensitive": "false",
                "spaced": "true"
            },
            {
                "word": "Dr",
                "pronunciation": "Drive",
                "case_sensitive": "false",
                "spaced": "true"
            }
        ],
        'temperature': call_settings.get('temperature', 0.5),  # The temperature setting for the call
        'voice': call_settings.get('voice','e1289219-0ea2-4f22-a994-c542c2a48a0f'),#Org Specific. Can us ID
        'webhook': 'https://us-central1-heyisaai.cloudfunctions.net/callProcessor',
        'wait_for_greeting': call_settings.get('wait_for_greeting', True),#Org Specific
        #'first_sentence': first_sentence,  # Script Specific, default to "Hey There!" if no first name
        'record': call_settings.get('record', False),
        'language': call_settings.get('language', None),#Script Specific
        'max_duration': call_settings.get('max_duration', 25),
        #'amd': call_settings.get('amd', False),
        #'dynamic_data': call_settings.get('dynamic_data', [{"response_data": [{}]}]),#Script Specific
        'interruption_threshold': call_settings.get('interruption_threshold', 150),#Org Specific
        'voice_settings': voice_settings, #Org Specific
        'request_data': {
            'start_sentence': first_sentence,
            'assistant_info': assistant_formatted,
            'contact_info': contact_formatted,
            'organization_info': org_formatted,
            'knowledge_base_info': kb_formatted, #change in future to knowledge_base_text
            'pathway_transfer': pathway_transfer
        }
    }
    return payload

@functions_framework.http
def trigger_phone_call(request):
    request_json = request.get_json(silent=True)
    #print(f'Received request: {request_json}')

    # Ensure all required parameters are present
    if not request_json or not all(key in request_json for key in ['flow_id', 'contact_id', 'organization_id']):
        error_message = "Missing required parameters"
        print(error_message)
        return abort(400, description=error_message)

    try:
        flow_doc = query_document_by_id('Flows', request_json['flow_id'])
        flow_specific_call_settings = flow_doc.get('call_settings', {})
        transfer_number_from_flow_settings = flow_specific_call_settings.get('transfer_phone_number', None)
        organization_info = query_document_by_id('Organizations', request_json['organization_id'])
        contact_info = query_document_by_id('Contacts', request_json['contact_id'])
        prompt_parameters = flow_doc.get('prompt_parameters', {})
        # Attempt to fetch general knowledge; if not found or blank, set to None
        general_knowledge_id = prompt_parameters.get('general_knowledgebase_id')
        if general_knowledge_id:
            general_knowledge = query_document_by_id('KnowledgeBases', general_knowledge_id)
        else:
            general_knowledge = None

        # Attempt to fetch specific knowledge; if not found or blank, set to None
        specific_knowledge_id = prompt_parameters.get('specific_knowledgebase_id')
        if specific_knowledge_id:
            specific_knowledge = query_document_by_id('KnowledgeBases', specific_knowledge_id)
        else:
            specific_knowledge = None

        # Initialize knowledge_base as an empty dictionary
        knowledge_base = {}

        # Only merge non-None knowledge bases into knowledge_base
        if general_knowledge:
            knowledge_base.update(general_knowledge)
        if specific_knowledge:
            knowledge_base.update(specific_knowledge)

        prompt_ref = query_document_by_id('Scripts', prompt_parameters.get('script_id'))
        rules_and_guidelines = query_document_by_id('Rules', prompt_parameters.get('rules_id'))

        if not flow_doc:
            error_message = "Flow document not found by flow_id"
            print(error_message)
            return abort(404, description=error_message)
        if not organization_info:
            error_message = "Account document not found by organization_id"
            print(error_message)
            return abort(404, description=error_message)
        if not contact_info:
            error_message = "Contact document not found by contact_id"
            print(error_message)
            return abort(404, description=error_message)

        try:
            call_settings = organization_info.get('call_settings', {})
            call_settings['transfer_phone_number'] = transfer_number_from_flow_settings
            call_settings['encrypted_key'] = organization_info.get('twilio', {}).get('encrypted_key', {}) ####THIS IS NEW
            print(f'Call settings: {call_settings}')
        except AttributeError:
            print("Call settings not found or not a dictionary. Using an empty dictionary instead.")
            call_settings = {}

        crafted_payload = craft_prompt(
            knowledge_base=knowledge_base,
            rules_and_guidelines=rules_and_guidelines,
            prompt_ref=prompt_ref,
            organization_info=organization_info,
            contact_info=contact_info,
            call_settings=call_settings
        )
        #print(f'Crafted payload: {crafted_payload}')

        url = "https://isa.bland.ai/v1/calls"
        headers = {
            "authorization": f"{os.environ.get('BLAND_API_KEY')}",
            "Content-Type": "application/json",
            "encrypted_key": call_settings.get('encrypted_key', None)
        }
        #print(f'Making POST request to {url} with headers {headers} and payload {crafted_payload}')
        response = requests.post(url, json=crafted_payload, headers=headers)
        #print(f'Received response: {response.status_code} {response.text}')

        if response.status_code == 200:
            response_data = response.json()
            call_id = response_data.get("call_id", "")
            db.collection('Calls').document(call_id).set({
                "original_request": request_json,
                "response": response.text,
                "call_id": call_id,
                "callTimestamp": datetime.datetime.utcnow()
            })
            # After making the call successfully, update the contact flow
            max_attempts = flow_doc.get('maxAttempts', 0)
            update_contact_flow(request_json['contact_id'], request_json['flow_id'], max_attempts)

            return jsonify({"success": True, "data": response.text})
        else:
            error_message = f"Call API error: {response.text}"
            print(error_message)
            
            if "Rate limit exceeded" in response.text:
                # Generate a random wait time between 0 and 10 minutes
                wait_time = random.randint(0, 600)
                print(f"Rate limit exceeded. Retrying in {wait_time} seconds...")
                
                # Wait for the random duration
                time.sleep(wait_time)
                
                # Retry the API call recursively
                return trigger_phone_call(request)
            else:
                return abort(response.status_code, description=error_message)
        
    except Exception as e:
        error_message = f"Server error: {str(e)}"
        print(error_message)
        return abort(500, description=error_message)