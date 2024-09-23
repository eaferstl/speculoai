# main.py

import functions_framework
from flask import abort, jsonify
from prompt_crafting import craft_prompt
from database_ops import query_document_by_id, update_contact_flow, save_call_data
from google.cloud import error_reporting
from config import config
from api_client import send_bland_ai_request

import logging

# Initialize error reporting client
error_client = error_reporting.Client()


logging.basicConfig(level=logging.INFO)

@functions_framework.http
def call_builder(request):
    try:
        request_json = request.get_json(silent=True)
        print(f"Received request: {request_json}")

        flow_doc, organization_info, contact_info = get_required_documents(request_json)
        logging.info(f"Retrieved organization_info: {organization_info}")


        crafted_payload = craft_prompt(
            knowledge_base=get_knowledge_base(flow_doc),
            rules_and_guidelines=get_rules_and_guidelines(flow_doc),
            prompt_ref=get_prompt_ref(flow_doc),
            organization_info=organization_info,
            contact_info=contact_info,
            call_settings=get_call_settings(organization_info, flow_doc),
            flow_doc=flow_doc,
            is_test=request_json.get('test', False)
        )

        response = send_bland_ai_request(crafted_payload)

        if response is None:
            logging.error("send_bland_ai_request returned None")
            return jsonify({"error": "Failed to get response from Bland AI"}), 500

        if response.status_code == 200:
            return handle_successful_response(response, request_json, flow_doc)
        else:
            return handle_error_response(response)

    except Exception as e:
        logging.exception("An error occurred while processing the request")
        return jsonify({"error": str(e)}), 500

def validate_request(request_json):
    return request_json and all(key in request_json for key in ['flow_id', 'contact_id', 'organization_id'])

def get_call_settings(organization_info, flow_doc):
    call_settings = organization_info.get('call_settings', {}).copy()
    flow_specific_call_settings = flow_doc.get('call_settings', {})
    call_settings.update(flow_specific_call_settings)
    call_settings['encrypted_key'] = organization_info.get('twilio', {}).get('encrypted_key')
    
    # Use config for default values
    call_settings.setdefault('max_duration', config.get('default_max_duration', 300))
    call_settings.setdefault('interruption_threshold', config.get('default_interruption_threshold', 0.5))
    
    return call_settings

def get_required_documents(request_json):
    flow_doc = query_document_by_id('Flows', request_json['flow_id'])
    organization_info = query_document_by_id('Organizations', request_json['organization_id'])
    contact_info = query_document_by_id('Contacts', request_json['contact_id'])
    
    if not all([flow_doc, organization_info, contact_info]):
        raise ValueError("One or more required documents not found")
    
    return flow_doc, organization_info, contact_info

def get_knowledge_base(flow_doc):
    prompt_parameters = flow_doc.get('prompt_parameters', {})
    general_knowledge_id = prompt_parameters.get('general_knowledgebase_id')
    specific_knowledge_id = prompt_parameters.get('specific_knowledgebase_id')
    
    knowledge_base = {}
    if general_knowledge_id:
        general_knowledge = query_document_by_id('KnowledgeBases', general_knowledge_id)
        if general_knowledge:
            knowledge_base.update(general_knowledge)
    
    if specific_knowledge_id:
        specific_knowledge = query_document_by_id('KnowledgeBases', specific_knowledge_id)
        if specific_knowledge:
            knowledge_base.update(specific_knowledge)
    
    return knowledge_base

def get_rules_and_guidelines(flow_doc):
    prompt_parameters = flow_doc.get('prompt_parameters', {})
    rules_id = prompt_parameters.get('rules_id')
    return query_document_by_id('Rules', rules_id) if rules_id else {}

def get_prompt_ref(flow_doc):
    prompt_parameters = flow_doc.get('prompt_parameters', {})
    script_id = prompt_parameters.get('script_id')
    return query_document_by_id('Scripts', script_id) if script_id else {}

def get_call_settings(organization_info, flow_doc):
    call_settings = organization_info.get('call_settings', {}).copy()
    flow_specific_call_settings = flow_doc.get('call_settings', {})
    call_settings.update(flow_specific_call_settings)
    call_settings['encrypted_key'] = organization_info.get('twilio', {}).get('encrypted_key')
    return call_settings


def handle_successful_response(response, request_json, flow_doc):
    response_data = response.json()
    call_id = response_data.get("call_id", "")
    save_call_data(call_id, request_json, response.text)
    
    if not request_json.get('test', False):
        max_attempts = flow_doc.get('maxAttempts', 0)
        update_contact_flow(request_json['contact_id'], request_json['flow_id'], max_attempts)
    
    return jsonify({"success": True, "data": response.text})

def handle_error_response(response):
    error_message = f"Call API error: {response.text}"
    logging.error(error_message)
    return jsonify({"error": error_message}), response.status_code