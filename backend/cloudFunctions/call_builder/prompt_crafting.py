# prompt_crafting.py

# prompt_crafting.py

from payload_factory import PayloadFactory
from database_ops import get_organization_config, get_call_count
from secret_manager import access_secret_version
from html_processing import process_html
from time_utils import get_day_time
from config import config

class PayloadCrafter:
    def __init__(self, knowledge_base, rules_and_guidelines, prompt_ref, organization_info, contact_info, call_settings, flow_doc, is_test=False):
        self.knowledge_base = knowledge_base
        self.rules_and_guidelines = rules_and_guidelines
        self.prompt_ref = prompt_ref
        self.organization_info = organization_info
        self.contact_info = contact_info
        self.call_settings = call_settings
        self.flow_doc = flow_doc
        self.is_test = is_test
        
        self.flow_type = flow_doc.get('flow_type', '')
        self.contact_id = contact_info.get('id')
        self.flow_id = flow_doc.get('id')
        
        org_id = organization_info.id if hasattr(organization_info, 'id') else organization_info.get('id')
        self.org_config = get_organization_config(org_id)
        self.bland_api_key = access_secret_version(config.get('project_id'), 'bland-api-key')
        self.payload_factory = PayloadFactory()

    def craft_payload(self):
        flow_handler = self.get_flow_handler()
        return flow_handler()

    def get_flow_handler(self):
        handlers = {
            'Convert': self.handle_convert_flow,
            'Engage': self.handle_engage_flow,
            'Revive': self.handle_revive_flow
        }
        return handlers.get(self.flow_type, self.handle_default_flow)

    def handle_convert_flow(self):
        call_count = get_call_count(self.contact_id, self.flow_id)
        if call_count == 0 and not self.is_test:
            return self.payload_factory.create_payload('convert_voicemail', org_config=self.org_config, **self.get_payload_kwargs())
        return self.craft_standard_payload()

    def handle_engage_flow(self):
        return self.payload_factory.create_payload('voicemail', org_config=self.org_config, **self.get_payload_kwargs())

    def handle_revive_flow(self):
        return self.craft_standard_payload()

    def handle_default_flow(self):
        return self.craft_standard_payload()

    

    def craft_standard_payload(self):
        print(f"Script:{self.prompt_ref}")#debug
        if self.prompt_ref.get('pathway_id'):
            return self.payload_factory.create_payload('pathway', org_config=self.org_config, **self.get_payload_kwargs())
        return self.payload_factory.create_payload('standard', org_config=self.org_config, **self.get_payload_kwargs())

    def get_payload_kwargs(self):
        return {
            'phone_number': self.contact_info.get('phoneNumber'),
            'knowledge_base': self.knowledge_base,
            'rules_and_guidelines': self.rules_and_guidelines,
            'prompt_ref': self.prompt_ref,
            'organization_info': self.organization_info,
            'contact_info': self.contact_info,
            'call_settings': self.call_settings,
            'is_test': self.is_test,
            'bland_api_key': self.bland_api_key,
        }

def craft_prompt(knowledge_base, rules_and_guidelines, prompt_ref, organization_info, contact_info, call_settings, flow_doc, is_test=False):
    crafter = PayloadCrafter(
        knowledge_base, rules_and_guidelines, prompt_ref, organization_info, 
        contact_info, call_settings, flow_doc, is_test
    )
    return crafter.craft_payload()