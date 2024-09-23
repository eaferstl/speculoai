# utils.py
from database_ops import query_document_by_id

def validate_request(request_json):
    return request_json and all(key in request_json for key in ['flow_id', 'contact_id', 'organization_id'])

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

def prepare_call_settings(organization_info, flow_doc):
    call_settings = organization_info.get('call_settings', {})
    flow_specific_call_settings = flow_doc.get('call_settings', {})
    call_settings['transfer_phone_number'] = flow_specific_call_settings.get('transfer_phone_number')
    call_settings['encrypted_key'] = organization_info.get('twilio', {}).get('encrypted_key', {})
    return call_settings