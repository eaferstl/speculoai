from google.cloud import storage
import json
from config import config
from time_utils import get_day_time
from html_processing import process_html
from database_ops import get_organization_config
import logging
import random
import datetime
import re

class PayloadFactory:
    def __init__(self):
        self.storage_client = storage.Client()
        self.bucket_name = config.get('config_bucket')
        self.load_configs()

    def load_configs(self):
        try:
            bucket = self.storage_client.bucket(self.bucket_name)
            
            pronunciation_blob = bucket.blob('pronunciation_guide.json')
            pronunciation_data = json.loads(pronunciation_blob.download_as_string())
            if isinstance(pronunciation_data, list):
                self.pronunciation_guide = pronunciation_data
            else:
                self.pronunciation_guide = pronunciation_data.get('custom_pronunciations', [])
            
            defaults_blob = bucket.blob('payload_defaults.json')
            self.payload_defaults = json.loads(defaults_blob.download_as_string())
        except Exception as e:
            logging.error(f"Error loading configs: {str(e)}")
            self.pronunciation_guide = []
            self.payload_defaults = {}

    def create_payload(self, payload_type, **kwargs):
        if payload_type == 'standard':
            return self.create_standard_payload(**kwargs)
        elif payload_type == 'pathway':
            return self.create_pathway_payload(**kwargs)
        elif payload_type == 'voicemail':
            return self.create_voicemail_payload(**kwargs)
        elif payload_type == 'convert_voicemail':
            return self.create_convert_payload(**kwargs)
        else:
            raise ValueError(f"Unknown payload type: {payload_type}")

    def create_standard_payload(self, **kwargs):
        contact_info = kwargs.get('contact_info', {})
        organization_info = kwargs.get('organization_info', {})
        call_settings = kwargs.get('call_settings', {})
        prompt_string = self.create_prompt_string(**kwargs)
        is_test = kwargs.get('is_test', False)  # Get the is_test parameter

        
        org_config = get_organization_config(organization_info.get('id'))
        
        payload = {
            'phone_number': contact_info.get('phoneNumber'),
            'task': prompt_string,
            'model': call_settings.get('model', self.payload_defaults.get('default_model', 'enhanced')),
            'transfer_phone_number': self.validate_phone_number(call_settings.get('transfer_phone_number')),
            'answered_by_enabled': call_settings.get('answered_by_enabled', True),
            'encrypted_key': call_settings.get('encrypted_key',None),
            'from': organization_info.get('phoneNumbers', {}).get('outbound') or None,
            'pronunciation_guide': self.pronunciation_guide,
            'temperature': call_settings.get('temperature', self.payload_defaults.get('default_temperature', 0.5)),
            'voice': call_settings.get('voice', self.payload_defaults.get('default_voice', 'e1289219-0ea2-4f22-a994-c542c2a48a0f')),
            'webhook': config.get('TEST_WEBHOOK_URL', "https://us-central1-heyisaai.cloudfunctions.net/callProcessor-test") if is_test else config.get('WEBHOOK_URL', "https://us-central1-heyisaai.cloudfunctions.net/callProcessor"),
            'wait_for_greeting': call_settings.get('wait_for_greeting', True),
            'first_sentence': self.create_first_sentence(contact_info, organization_info),
            'record': call_settings.get('record', True),
            'language': call_settings.get('language'),
            'max_duration': call_settings.get('max_duration', config.get('default_max_duration', 300)),
            'interruption_threshold': call_settings.get('interruption_threshold', config.get('default_interruption_threshold', 0.5)),
            'voice_settings': call_settings.get('voice_settings', {}),
            'request_data': self.create_request_data(**kwargs),
            'metadata': {
                'organization_id': organization_info.get('id')
            },
        }

        logging.info(f"Created standard payload: {payload}")
        return payload

    def validate_phone_number(self, phone_number):
        if phone_number is None:
            return None
        
        # Remove all non-digit characters
        digits_only = re.sub(r'\D', '', str(phone_number))
        
        # Check if the number has at least 10 digits
        if len(digits_only) >= 10:
            return digits_only
        else:
            logging.warning(f"Invalid transfer phone number: {phone_number}. Setting to None.")
            return None

    def create_pathway_payload(self, **kwargs):
        payload = self.create_standard_payload(**kwargs)
        payload['pathway_id'] = kwargs.get('prompt_ref', {}).get('pathway_id')
        if 'task' in payload:
            del payload['task']  # Remove 'task' as it's not used in pathway payloads

        print(f"Created pathway payload: {payload}")
        return payload

    def create_voicemail_payload(self, **kwargs):
        base_payload = self.create_standard_payload(**kwargs)
        base_payload['voicemail_message'] = self.create_voicemail_message(**kwargs)
        base_payload['voicemail_action'] = 'leave_message'
        base_payload['max_duration'] = 60
        base_payload['pathway_id'] = kwargs.get('prompt_ref', {}).get('pathway_id')
        base_payload['wait_for_greeting'] = True
        if 'task' in base_payload:
            del base_payload['task']  # Remove 'task' as it's not used in voicemail payloads

        logging.info(f"Created voicemail payload: {base_payload}")
        return base_payload
    
    def create_convert_payload(self, **kwargs):
        base_payload = self.create_standard_payload(**kwargs)
        base_payload['retry'] = {
            "wait": 10,
            "voicemail_action": "leave_message",
            "voicemail_message": self.create_voicemail_message(**kwargs)
        }
        base_payload['max_duration'] = 60
        base_payload['pathway_id'] = kwargs.get('prompt_ref', {}).get('pathway_id')
        base_payload['wait_for_greeting'] = True
        if 'task' in base_payload:
            del base_payload['task']  # Remove 'task' as it's not used in voicemail payloads

        logging.info(f"Created convert first call voicemail payload: {base_payload}")
        return base_payload

    def create_prompt_string(self, **kwargs):
        rules_and_guidelines = kwargs.get('rules_and_guidelines', {})
        knowledge_base = kwargs.get('knowledge_base', {})
        prompt_ref = kwargs.get('prompt_ref', {})
        
        rules = rules_and_guidelines.get('rules', [])
        guidelines = rules_and_guidelines.get('guidelines', [])
        combined_rules_and_guidelines = ' '.join(rules + guidelines)
        
        knowledge = ' '.join([f"{key}: {value}" for key, value in knowledge_base.items()])
        
        prompt_logic = process_html(prompt_ref.get('prompt_logic', ''))
        default_prompt_start = process_html(prompt_ref.get('default_prompt_start', ''))
        prompt_body = process_html(prompt_ref.get('prompt', ''))
        default_prompt_end = process_html(prompt_ref.get('default_prompt_end', ''))
        
        prompt_components = [
            combined_rules_and_guidelines, prompt_logic, default_prompt_start, 
            prompt_body, default_prompt_end, knowledge
        ]
        return '\n'.join(filter(None, prompt_components))

    def create_request_data(self, **kwargs):
        contact_info = kwargs.get('contact_info', {})
        organization_info = kwargs.get('organization_info', {})
        call_settings = kwargs.get('call_settings', {})
        flow_doc = kwargs.get('flow_doc', {})
        knowledge_base = kwargs.get('knowledge_base', {})
        prompt_ref = kwargs.get('prompt_ref', {})
        
        contact_address = contact_info.get('address', {})
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
        
        org_formatted = {
            'org_name': organization_info.get('org_name', ''),
            'org_key': organization_info.get('twilio', {}).get('encrypted_key') or None
        }
        
        knowledge_base_text = knowledge_base.get('knowledge_base_text', '')
        
        request_data = {
            'start_sentence': self.create_first_sentence(contact_info, organization_info),
            'assistant_info': assistant_formatted,
            'contact_info': contact_formatted,
            'organization_info': org_formatted,
            'knowledge_base_info': knowledge_base_text,
            'pathway_transfer': call_settings.get('transfer_phone_number'),
            'context': prompt_ref.get('context', "default_context"),
            'value_link': flow_doc.get('value_link', "default_value_link")
        }

        logging.info(f"Created request_data: {request_data}")
        return request_data

    def create_first_sentence(self, contact_info, organization_info):
        timezone_str = organization_info.get('timezone', 'UTC')
        day_of_week, part_of_day = get_day_time(timezone_str)
        
        if contact_info.get('firstName'):
            return f"Hey there, happy {day_of_week} {part_of_day}, is this {contact_info['firstName']}?"
        else:
            return f"Hey there, happy {day_of_week}, how are you doing this {part_of_day}?"

    def create_voicemail_message(self, **kwargs):
        prompt_ref = kwargs.get('prompt_ref', {})
        contact_info = kwargs.get('contact_info', {})
        organization_info = kwargs.get('organization_info', {})
        
        # Get day and time information
        timezone_str = organization_info.get('timezone', 'UTC')
        day_of_week, part_of_day = get_day_time(timezone_str)
        
        # Construct the first sentence
        first_name = contact_info.get('firstName', '')
        assistant_name = organization_info.get('assistant_name', '')
        company_name = organization_info.get('org_name', '')
        
        first_sentence = f"Hey there{' ' + first_name if first_name else ''}, This is {assistant_name} with {company_name}. "
        first_sentence += f"I hope you are having a great {day_of_week.lower()} {part_of_day}. "
        
        # Get the voicemail message from prompt_ref
        voicemail_message = prompt_ref.get('voicemail', '')
        
        # If voicemail_message is empty, use a default message
        if not voicemail_message:
            default_messages = [
                "I was hoping to catch you for a quick chat. Please give us a call when you get a chance.",
                "I wanted to touch base with you. When you have a moment, please give us a call back.",
                "I have some information I'd like to discuss with you. Feel free to call us back at your convenience.",
                "We have an update we'd like to share with you. Please give us a call when you're available.",
                "I tried reaching out and missed you. When you have a chance, we'd appreciate a call back."
            ]
            voicemail_message = random.choice(default_messages)
        
        # Construct the ending
        ending = self.create_voicemail_ending(first_name, day_of_week)
        
        # Combine the first sentence, voicemail message, and ending
        full_message = first_sentence + voicemail_message + " " + ending
        
        return full_message

    def create_voicemail_ending(self, first_name, day_of_week):
        current_day = datetime.datetime.now().strftime('%A')
        
        if current_day in ['Friday', 'Saturday', 'Sunday']:
            time_phrase = "weekend"
        else:
            time_phrase = "week"
        
        endings = [
            f"Thanks, {first_name}. Have an amazing rest of your {time_phrase}!",
            f"Take care, {first_name}, and enjoy the rest of your {time_phrase}.",
            f"Thanks for your time, {first_name}. Hope you have a fantastic {time_phrase}!",
            f"Appreciate your time, {first_name}. Wishing you a great {time_phrase} ahead!",
            f"Thanks again, {first_name}. Have a wonderful rest of your {time_phrase}!"
        ]
        
        return random.choice(endings)