import functions_framework
import json
import requests
from flask import abort, jsonify
import datetime
import os
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
    timezone = pytz.timezone(timezone_str)
    now = datetime.datetime.now(timezone)
    part_of_day = "morning" if now.hour < 12 else "afternoon"
    day_of_week = now.strftime('%A')
    return day_of_week, part_of_day

def query_document_by_id(collection, doc_id):
    try:
        doc_ref = db.collection(collection).document(doc_id)
        doc = doc_ref.get()
        if doc.exists:
            return doc.to_dict()
        else:
            print(f"No document found with ID: {doc_id}")
            return None
    except Exception as e:
        print(f"Error fetching document by ID: {str(e)}")
        return None

def update_contact_flow(contact_id, flow_id):
    try:
        contact_ref = db.collection('Contacts').document(contact_id)
        contact_doc = contact_ref.get()
        if contact_doc.exists:
            contact_ref.update({
                'lastCallAttempt': datetime.datetime.utcnow().isoformat()
            })
            print(f"Contact {contact_id} updated successfully.")
        else:
            print(f"Contact document {contact_id} does not exist.")
    except Exception as e:
        print(f"Failed to update contact document: {str(e)}")

def format_knowledge_base(knowledge_base):
    print("Formatting knowledge base...")
    formatted_qa = "Knowledge Base Q&A:\n"
    for entry in knowledge_base:
        question = entry.get('question', 'No question provided')
        answer = entry.get('answer', 'No answer provided')
        formatted_qa += f"Q: {question}\nA: {answer}\n\n"
    print("Knowledge base formatted successfully.")
    return formatted_qa

def process_html(html_content):
    print(f"Processing HTML content: {html_content}")
    soup = BeautifulSoup(html_content, 'html.parser')
    plain_text = soup.get_text(separator='\n')
    print("HTML content processed successfully.")
    return plain_text

def craft_prompt(knowledge_base, rules_and_guidelines, prompt_ref, organization_info, contact_info, call_settings):
    print("Crafting prompt...")

    contact_address = contact_info.get('address', {})
    print(f"Extracted contact address: {contact_address}")

    contact_formatted = {
        'contact_first_name': contact_info.get('firstName', ''),
        'contact_last_name': contact_info.get('lastName', ''),
        'contact_phone': contact_info.get('phoneNumber', ''),
        'contact_email': contact_info.get('email', ''),
        'contact_street': contact_address.get('street', ''),
        'contact_city': contact_address.get('city', '')
    }

    assistant_formatted = {
        'assistant_name': organization_info.get('assistant_name', ''),
        'assistant_name_pronunciation': organization_info.get('assistant_name_pronunciation', '')
    }

    timezone_str = organization_info.get('timezone', '')
    day_of_week, part_of_day = get_day_time(timezone_str)

    org_formatted = {
        'org_name': organization_info.get('org_name', '')
    }

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

    kb_formatted = format_knowledge_base(knowledge_base.get('knowledge_base', ''))
    knowledge_base_text = knowledge_base.get('knowledge_base_text', '')

    prompt_logic = process_html(prompt_ref.get('prompt_logic', ''))
    default_prompt_start = process_html(prompt_ref.get('default_prompt_start', ''))
    prompt_body = process_html(prompt_ref.get('prompt', ''))
    default_prompt_end = process_html(prompt_ref.get('default_prompt_end', ''))

    rules_text = rules_and_guidelines.get('rules_and_guidelines', '')
    print(f"Rules and guidelines text: {rules_text}")

    all_prompt_components = [
        rules_text, prompt_logic, default_prompt_start, prompt_body, default_prompt_end, org_info_text,
        contact_info_text, assistant_info_text, kb_formatted
    ]
    print("All prompt components assembled.")

    prompt_string = '\n'.join(filter(None, all_prompt_components))

    default_voice_settings = {}

    try:
        voice_settings = call_settings.get('voice_settings', {})
    except AttributeError:
        print("Voice settings not found or not a dictionary. Using default voice settings.")
        voice_settings = {}
    for key, default_value in default_voice_settings.items():
        voice_settings.setdefault(key, default_value)

    print(f'Voice settings: {voice_settings}')

    try:
        phone_numbers = organization_info.get('phoneNumbers', {})
        outbound = phone_numbers.get('outbound', None)
    except Exception as e:
        outbound = None

    transfer_phone_number = call_settings.get('transfer_phone_number', None)
    if transfer_phone_number is not None and len(str(transfer_phone_number)) < 10:
        transfer_phone_number = None

    pathway_transfer = transfer_phone_number

    first_sentence = (
        f"Hey there, happy {day_of_week} {part_of_day}, is this {contact_info.get('firstName')}?"
        if contact_info.get('firstName')
        else f"Hey there, happy {day_of_week}, how are you doing this {part_of_day}?"
    )

    payload = {
        'phone_number': contact_formatted.get('contact_phone', None),
        'task': prompt_string,
        'model': call_settings.get('model', 'enhanced'),
        'transfer_phone_number': transfer_phone_number,
        'answered_by_enabled': call_settings.get('answered_by_enabled', False),
        'encrypted_key': call_settings.get('encrypted_key', None),
        'from': outbound,
        'pronunciation_guide': [
            {
                "word": organization_info.get('assistant_name', ''),
                "pronunciation": organization_info.get('assistant_name_pronunciation', ''),
                "case_sensitive": "false",
                "spaced": "true"
            },
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
        'temperature': call_settings.get('temperature', 0.5),
        'voice': call_settings.get('voice', 'e1289219-0ea2-4f22-a994-c542c2a48a0f'),
        'webhook': 'https://us-central1-heyisaai.cloudfunctions.net/callProcessor-test',
        'wait_for_greeting': call_settings.get('wait_for_greeting', True),
        'first_sentence': first_sentence,
        'record': True,
        'language': call_settings.get('language', None),
        'max_duration': call_settings.get('max_duration', 25),
        'interruption_threshold': call_settings.get('interruption_threshold', 200),
        'voice_settings': voice_settings,
        'request_data': {
            'assistant_info': assistant_formatted,
            'contact_info': contact_formatted,
            'organization_info': org_formatted,
            'knowledge_base_info': knowledge_base_text,
        }
    }
    return payload

def craft_pathway(knowledge_base, rules_and_guidelines, prompt_ref, organization_info, contact_info, call_settings, flow_doc):
    print("Crafting pathway payload...")

    contact_address = contact_info.get('address', {})
    print(f"Extracted contact address: {contact_address}")

    contact_formatted = {
        'contact_first_name': contact_info.get('firstName', ''),
        'contact_last_name': contact_info.get('lastName', ''),
        'contact_phone': contact_info.get('phoneNumber', ''),
        'contact_email': contact_info.get('email', ''),
        'contact_street': contact_address.get('street', ''),
        'contact_city': contact_address.get('city', '')
    }

    assistant_formatted = {
        'assistant_name': organization_info.get('assistant_name', ''),
        'assistant_name_pronunciation': organization_info.get('assistant_name_pronunciation', '')
    }

    timezone_str = organization_info.get('timezone', '')
    day_of_week, part_of_day = get_day_time(timezone_str)

    org_formatted = {
        'org_name': organization_info.get('org_name', '')
    }

    knowledge_base_text = knowledge_base.get('knowledge_base_text', '')

    rules_text = rules_and_guidelines.get('rules_and_guidelines', '')
    print(f"Rules and guidelines text: {rules_text}")

    default_voice_settings = {}

    try:
        voice_settings = call_settings.get('voice_settings', {})
    except AttributeError:
        print("Voice settings not found or not a dictionary. Using default voice settings.")
        voice_settings = {}
    for key, default_value in default_voice_settings.items():
        voice_settings.setdefault(key, default_value)

    print(f'Voice settings: {voice_settings}')

    try:
        phone_numbers = organization_info.get('phoneNumbers', {})
        outbound = phone_numbers.get('outbound', None)
    except Exception as e:
        outbound = None

    transfer_phone_number = call_settings.get('transfer_phone_number', None)
    if transfer_phone_number is not None and len(str(transfer_phone_number)) < 10:
        transfer_phone_number = None

    pathway_transfer = transfer_phone_number

    first_sentence = (
        f"Hey there, happy {day_of_week} {part_of_day}, is this {contact_info.get('firstName')}?"
        if contact_info.get('firstName')
        else f"Hey there, happy {day_of_week}, how are you doing this {part_of_day}?"
    )

    context = prompt_ref.get('context', "default_context")
    value_link = flow_doc.get('value_link', "default_value_link")

    payload = {
        'phone_number': contact_formatted.get('contact_phone', None),
        'pathway_id': prompt_ref.get('pathway_id', None),
        'model': call_settings.get('model', 'enhanced'),
        'answered_by_enabled': call_settings.get('answered_by_enabled', False),
        'encrypted_key': call_settings.get('encrypted_key', None),
        'from': outbound,
        'pronunciation_guide': [
            {
                "word": organization_info.get('assistant_name', ''),
                "pronunciation": organization_info.get('assistant_name_pronunciation', ''),
                "case_sensitive": "false",
                "spaced": "true"
            },
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
        'temperature': call_settings.get('temperature', 0.5),
        'voice': call_settings.get('voice', 'e1289219-0ea2-4f22-a994-c542c2a48a0f'),
        'webhook': 'https://us-central1-heyisaai.cloudfunctions.net/callProcessor-test',
        'wait_for_greeting': call_settings.get('wait_for_greeting', True),
        'record': True,
        'language': call_settings.get('language', None),
        'max_duration': call_settings.get('max_duration', 25),
        'interruption_threshold': call_settings.get('interruption_threshold', 200),
        'voice_settings': voice_settings,
        'request_data': {
            'start_sentence': first_sentence,
            'assistant_info': assistant_formatted,
            'contact_info': contact_formatted,
            'organization_info': org_formatted,
            'knowledge_base_info': knowledge_base_text,
            'pathway_transfer': pathway_transfer,
            'context': context,
            'value_link': value_link
        }
    }
    
    return payload

@functions_framework.http
def trigger_phone_call(request):
    request_json = request.get_json(silent=True)
    print(f'Received request: {request_json}')

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
        
        general_knowledge_id = prompt_parameters.get('general_knowledgebase_id')
        general_knowledge = query_document_by_id('KnowledgeBases', general_knowledge_id) if general_knowledge_id else None

        specific_knowledge_id = prompt_parameters.get('specific_knowledgebase_id')
        specific_knowledge = query_document_by_id('KnowledgeBases', specific_knowledge_id) if specific_knowledge_id else None

        knowledge_base = {}
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
            call_settings['encrypted_key'] = organization_info.get('twilio', {}).get('encrypted_key', {})
            print(f'Call settings: {call_settings}')
        except AttributeError:
            print("Call settings not found or not a dictionary. Using an empty dictionary instead.")
            call_settings = {}

        print(f'Call settings: {call_settings}')

        pathway_id = prompt_ref.get('pathway_id', None)

        if pathway_id:
            crafted_payload = craft_pathway(
                knowledge_base=knowledge_base,
                rules_and_guidelines=rules_and_guidelines,
                prompt_ref=prompt_ref,
                organization_info=organization_info,
                contact_info=contact_info,
                call_settings=call_settings,
                flow_doc=flow_doc
            )
        else:
            crafted_payload = craft_prompt(
                knowledge_base=knowledge_base,
                rules_and_guidelines=rules_and_guidelines,
                prompt_ref=prompt_ref,
                organization_info=organization_info,
                contact_info=contact_info,
                call_settings=call_settings,
                flow_doc=flow_doc
            )

        print(f'Crafted payload: {crafted_payload}')

        url = "https://isa.bland.ai/v1/calls"
        headers = {
            "authorization": f"{os.environ.get('BLAND_API_KEY')}",
            "Content-Type": "application/json",
            "encrypted_key": call_settings.get('encrypted_key', None)
        }
        print(f'Making POST request to {url} with headers {headers} and payload {crafted_payload}')
        response = requests.post(url, json=crafted_payload, headers=headers)
        print(f'Received response: {response.status_code} {response.text}')

        if response.status_code == 200:
            response_data = response.json()
            call_id = response_data.get("call_id", "")
            db.collection('Calls').document(call_id).set({
                "original_request": request_json,
                "response": response.text,
                "call_id": call_id,
                "callTimestamp": datetime.datetime.utcnow()
            })
            update_contact_flow(request_json['contact_id'], request_json['flow_id'])

            return jsonify({"success": True, "data": response.text})
        else:
            error_message = f"Call API error: {response.text}"
            print(error_message)
            return abort(response.status_code, description=error_message)

    except Exception as e:
        error_message = f"Server error: {str(e)}"
        print(error_message)
        return abort(500, description=error_message)
