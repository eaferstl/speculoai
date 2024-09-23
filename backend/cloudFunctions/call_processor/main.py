import os
import re
import json
import requests
from datetime import datetime
from openai import OpenAI
import firebase_admin
from firebase_admin import credentials, firestore
from flask import abort, jsonify
import functions_framework
from google.auth import default
from googleapiclient.discovery import build
from google.oauth2 import service_account
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import base64
from secret_manager import access_secret_version
import copy


# Initialize Firebase Admin SDK outside of your function
if not firebase_admin._apps:
    cred = credentials.ApplicationDefault()
    firebase_admin.initialize_app(cred)

# Firestore client
db = firestore.client()

# Get the project ID from environment variables
project_id = os.environ.get("PROJECT_ID")

openai_api_key = access_secret_version(project_id, "OPENAI_API_KEY")
if openai_api_key is None:
    print("Failed to retrieve OpenAI API key")
    # Handle the error appropriately (e.g., raise an exception or use a default value)
else:
    openai_client = OpenAI(api_key=openai_api_key)

# If modifying these scopes, make sure to update the OAuth consent screen as well.
SCOPES = ['https://www.googleapis.com/auth/gmail.send']

def setup_credentials():
    """Sets up the credentials from environment variables."""
    credentials_json = access_secret_version(project_id, "GOOGLE_APPLICATION_CREDENTIALS")
    if credentials_json:
        with open('/tmp/gmailkeys.json', 'w') as f:
            f.write(credentials_json)
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = '/tmp/gmailkeys.json'
    else:
        raise ValueError("GOOGLE_APPLICATION_CREDENTIALS_JSON environment variable not set")

def get_gmail_service():
    """Creates and returns an authorized Gmail API service instance."""
    try:
        creds = service_account.Credentials.from_service_account_file(
            '/tmp/gmailkeys.json', scopes=SCOPES)
        delegated_creds = creds.with_subject('bobby@heyisa.ai')  # Replace with your email
        return build('gmail', 'v1', credentials=delegated_creds)
    except Exception as e:
        print(f"An error occurred while creating Gmail service: {e}")
        raise

def create_message(sender, to, subject, html_message_text, plain_message_text):
    """Creates an email message with HTML and plain text versions."""
    message = MIMEMultipart('alternative')
    message['to'] = to
    message['from'] = sender
    message['subject'] = subject

    part1 = MIMEText(plain_message_text, 'plain')
    part2 = MIMEText(html_message_text, 'html')

    message.attach(part1)
    message.attach(part2)

    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
    return {'raw': raw_message}

def send_gmail_message(service, user_id, message):
    """Sends an email message."""
    try:
        message = service.users().messages().send(userId=user_id, body=message).execute()
        print(f'Message Id: {message["id"]}')
        return message
    except Exception as e:
        print(f'An error occurred: {e}')
        raise

def send_notification_email(contact_data, call_data, recipient_email):
    sender_email = 'HeyIsa Notifications <leads@heyisa.ai>'
    subject = 'New Answer Notification'
    
    # Construct HTML email body
    html_message_text = f"""
    <!DOCTYPE html>
    <html lang="en" xmlns="http://www.w3.org/1999/xhtml" xmlns:v="urn:schemas-microsoft-com:vml" xmlns:o="urn:schemas-microsoft-com:office:office">
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <meta http-equiv="X-UA-Compatible" content="IE=edge">
        <meta name="format-detection" content="telephone=no">
        <meta name="x-apple-disable-message-reformatting">
        <meta name="lead_information_version" content="1.0" />
        <meta name="lead_source" content="{contact_data.get('lead_source', 'N/A')}" />
        <meta name="lead_type" content="{contact_data.get('lead_type', 'N/A')}" />
        <meta name="lead_name" content="{contact_data.get('firstName', 'N/A')} {contact_data.get('lastName', 'N/A')}" />
        <meta name="lead_email" content="{contact_data.get('email', 'N/A')}" />
        <meta name="lead_phone" content="{contact_data.get('phoneNumber', 'N/A')}" />
        <meta name="lead_property_address" content="{contact_data.get('address', {}).get('street', 'N/A')}" />
        <meta name="lead_property_city" content="{contact_data.get('address', {}).get('city', 'N/A')}" />
        <meta name="lead_property_state" content="{contact_data.get('address', {}).get('state', 'N/A')}" />
        <meta name="lead_property_zip" content="{contact_data.get('address', {}).get('zip', 'N/A')}" />
        <meta name="lead_message" content="{call_data.get('call_analysis', {}).get('summary', 'N/A')}" />
        <meta name="lead_time_frame" content="{call_data.get('call_analysis', {}).get('answers', {}).get('Timeline', 'N/A')}" />
        <meta name="lead_financing" content="{call_data.get('call_analysis', {}).get('answers', {}).get('Financing', 'N/A')}" />
        <meta name="lead_call_id" content="{call_data.get('call_id', 'N/A')}" />
        <meta name="lead_call_length" content="{call_data.get('call_length', 'N/A')}" />
        <meta name="lead_call_status" content="{call_data.get('status', 'N/A')}" />
        <meta name="lead_call_recording_url" content="{call_data.get('recording_url', 'N/A')}" />
        <meta name="lead_call_transcript" content="{call_data.get('concatenated_transcript', 'N/A')}" />
        <meta name="lead_call_outcome" content="{call_data.get('call_analysis', {}).get('outcome', 'N/A')}" />
        <meta name="lead_call_summary" content="{call_data.get('call_analysis', {}).get('summary', 'N/A')}" />
        <title>New Lead Notification</title>
        <style type="text/css">
            @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;700&display=swap');
            body, table, td, a {{ -webkit-text-size-adjust: 100%; -ms-text-size-adjust: 100%; }}
            table, td {{ mso-table-lspace: 0pt; mso-table-rspace: 0pt; }}
            img {{ -ms-interpolation-mode: bicubic; }}
            img {{ border: 0; height: auto; line-height: 100%; outline: none; text-decoration: none; }}
            table {{ border-collapse: collapse !important; }}
            body {{ height: 100% !important; margin: 0 !important; padding: 0 !important; width: 100% !important; }}
            a[x-apple-data-detectors] {{ color: inherit !important; text-decoration: none !important; font-size: inherit !important; font-family: inherit !important; font-weight: inherit !important; line-height: inherit !important; }}
            @media screen and (max-width: 525px) {{
                .wrapper {{ width: 100% !important; max-width: 100% !important; }}
                .responsive-table {{ width: 100% !important; }}
                .padding {{ padding: 10px 5% 15px 5% !important; }}
                .section-padding {{ padding: 0 15px 50px 15px !important; }}
            }}
            .form-container {{ margin-bottom: 24px; padding: 20px; border: 1px dashed #ccc; }}
            .form-heading {{ color: #2a2a2a; font-family: "Roboto", "Helvetica", "Arial", sans-serif; font-weight: 700; text-align: left; line-height: 20px; font-size: 18px; margin: 0 0 8px; padding: 0; }}
            .form-answer {{ color: #2a2a2a; font-family: "Roboto", "Helvetica", "Arial", sans-serif; font-weight: 300; text-align: left; line-height: 20px; font-size: 16px; margin: 0; padding: 0; }}
            .divider {{ width: 100%; margin: 20px auto; border: none; border-top: 1px solid #eaeaea; }}
            .primary-color {{ color: #44D18B; }}
            .secondary-color {{ color: #2a2a2a; }}
            .button {{ background-color: #44D18B; border: none; color: white; padding: 15px 32px; text-align: center; text-decoration: none; display: inline-block; font-size: 16px; margin: 4px 2px; cursor: pointer; }}
        </style>
    </head>
    <body style="margin: 0 !important; padding: 0 !important; background-color: #f4f4f9;">
        <div style="display: none; font-size: 1px; color: #fefefe; line-height: 1px; font-family: 'Roboto', Helvetica, Arial, sans-serif; max-height: 0px; max-width: 0px; opacity: 0; overflow: hidden;">
            New lead notification: {contact_data.get('firstName', 'N/A')} {contact_data.get('lastName', 'N/A')} - {call_data.get('call_analysis', {}).get('summary', 'N/A')}
        </div>
        <table border="0" cellpadding="0" cellspacing="0" width="100%">
            <tr>
                <td bgcolor="#44D18B" align="center" style="padding: 15px;">
                    <table border="0" cellpadding="0" cellspacing="0" width="100%" style="max-width: 600px;">
                        <tr>
                            <td align="center" valign="top" style="padding: 40px 10px 40px 10px;">
                                <a href="https://heyisa.ai" target="_blank" style="display: inline-block;">
                                    <img alt="Logo" src="https://storage.googleapis.com/heyisa-media/heyIsa_long_white_logo.png" width="200" style="display: block; width: 200px; max-width: 200px; min-width: 200px; font-family: 'Roboto', Helvetica, Arial, sans-serif; color: #ffffff; font-size: 18px;" border="0">
                                </a>
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
            <tr>
                <td bgcolor="#f4f4f9" align="center" style="padding: 10px 15px 30px 15px;">
                    <table border="0" cellpadding="0" cellspacing="0" width="100%" style="max-width: 600px;">
                        <tr>
                            <td bgcolor="#ffffff" align="left" style="padding: 30px 30px 20px 30px; border-radius: 4px 4px 0px 0px; color: #2a2a2a; font-family: 'Roboto', Helvetica, Arial, sans-serif; font-size: 18px; font-weight: 400; line-height: 25px;">
                                <h1 style="font-size: 32px; font-weight: 700; margin: 0; color: #44D18B;">New Answered Call Notification</h1>
                            </td>
                        </tr>
                        <tr>
                            <td bgcolor="#ffffff" align="left" style="padding: 0px 30px 20px 30px; color: #2a2a2a; font-family: 'Roboto', Helvetica, Arial, sans-serif; font-size: 16px; font-weight: 400; line-height: 25px;">
                                <p style="margin: 0;">A new answered call has been processed. Please check HeyIsa for details.</p>
                            </td>
                        </tr>
                        <tr>
                            <td bgcolor="#ffffff" align="left" style="padding: 0px 30px 20px 30px; color: #2a2a2a; font-family: 'Roboto', Helvetica, Arial, sans-serif; font-size: 16px; font-weight: 400; line-height: 25px;">
                                <h2 style="font-size: 22px; font-weight: 700; margin: 0 0 10px 0; color: #44D18B;">Contact Details:</h2>
                                <p style="margin: 0 0 10px 0;"><strong>Name:</strong> {contact_data.get('firstName', 'N/A')} {contact_data.get('lastName', 'N/A')}</p>
                                <p style="margin: 0 0 10px 0;"><strong>Email:</strong> <a href="mailto:{contact_data.get('email', 'N/A')}" style="color: #44D18B;">{contact_data.get('email', 'N/A')}</a></p>
                                <p style="margin: 0 0 10px 0;"><strong>Phone:</strong> <a href="tel:{contact_data.get('phoneNumber', 'N/A')}" style="color: #44D18B;">{contact_data.get('phoneNumber', 'N/A')}</a></p>
                                <p style="margin: 0 0 10px 0;"><strong>Address:</strong> {contact_data.get('address', {}).get('street', 'N/A')}, {contact_data.get('address', {}).get('city', 'N/A')}, {contact_data.get('address', {}).get('state', 'N/A')}, {contact_data.get('address', {}).get('zip', 'N/A')}</p>
                            </td>
                        </tr>
                        <tr>
                            <td bgcolor="#ffffff" align="left" style="padding: 0px 30px 20px 30px; color: #2a2a2a; font-family: 'Roboto', Helvetica, Arial, sans-serif; font-size: 16px; font-weight: 400; line-height: 25px;">
                                <h2 style="font-size: 22px; font-weight: 700; margin: 0 0 10px 0; color: #44D18B;">Call Information:</h2>
                                <p style="margin: 0 0 10px 0;"><strong>Call ID:</strong> {call_data.get('call_id', 'N/A')}</p>
                                <p style="margin: 0 0 10px 0;"><strong>Call Length:</strong> {call_data.get('call_length', 'N/A')}</p>
                                <p style="margin: 0 0 10px 0;"><strong>Call Status:</strong> {call_data.get('status', 'N/A')}</p>
                                <p style="margin: 0 0 10px 0;"><strong>Call Outcome:</strong> {call_data.get('call_analysis', {}).get('outcome', 'N/A')}</p>
                                <p style="margin: 0 0 10px 0;"><strong>Time Frame:</strong> {call_data.get('call_analysis', {}).get('answers', {}).get('Timeline', 'N/A')}</p>
                                <p style="margin: 0 0 10px 0;"><strong>Financing:</strong> {call_data.get('call_analysis', {}).get('answers', {}).get('Financing', 'N/A')}</p>
                            </td>
                        </tr>
                        <tr>
                            <td bgcolor="#ffffff" align="left" style="padding: 0px 30px 20px 30px; color: #2a2a2a; font-family: 'Roboto', Helvetica, Arial, sans-serif; font-size: 16px; font-weight: 400; line-height: 25px;">
                                <h2 style="font-size: 22px; font-weight: 700; margin: 0 0 10px 0; color: #44D18B;">Call Summary:</h2>
                                <p style="margin: 0 0 10px 0;">{call_data.get('call_analysis', {}).get('summary', 'N/A')}</p>
                            </td>
                        </tr>
                        <tr>
                            <td bgcolor="#ffffff" align="left" style="padding: 0px 30px 40px 30px; border-radius: 0px 0px 4px 4px; color: #2a2a2a; font-family: 'Roboto', Helvetica, Arial, sans-serif; font-size: 16px; font-weight: 400; line-height: 25px;">
                                <p style="margin: 0;">For more details, please check the full call transcript and recording in HeyIsa.</p>
                                <a href="https://app.heyisa.ai" target="_blank" class="button" style="font-family: 'Roboto', Helvetica, Arial, sans-serif; font-size: 16px; font-weight: 400; color: #ffffff; text-decoration: none; display: inline-block; margin: 20px 0; padding: 15px 25px; border-radius: 4px; background-color: #44D18B;">View in HeyIsa</a>
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """

    # Construct plain text email body
    plain_message_text = f"""
    New Answered Call Notification

    A new answered call has been processed. Please check HeyIsa for details.

    Contact Details:
    Name: {contact_data.get('firstName', 'N/A')} {contact_data.get('lastName', 'N/A')}
    Email: {contact_data.get('email', 'N/A')}
    Phone: {contact_data.get('phoneNumber', 'N/A')}
    Address: {contact_data.get('address', {}).get('street', 'N/A')}, {contact_data.get('address', {}).get('city', 'N/A')}, {contact_data.get('address', {}).get('state', 'N/A')}, {contact_data.get('address', {}).get('zip', 'N/A')}

    Call Information:
    Call ID: {call_data.get('call_id', 'N/A')}
    Call Length: {call_data.get('call_length', 'N/A')}
    Call Status: {call_data.get('status', 'N/A')}
    Call Outcome: {call_data.get('call_analysis', {}).get('outcome', 'N/A')}
    Time Frame: {call_data.get('call_analysis', {}).get('answers', {}).get('Timeline', 'N/A')}
    Financing: {call_data.get('call_analysis', {}).get('answers', {}).get('Financing', 'N/A')}

    Call Summary:
    {call_data.get('call_analysis', {}).get('summary', 'N/A')}

    For more details, please check the full call transcript and recording in HeyIsa.

    View in HeyIsa: https://app.heyisa.ai
    """
    
    # Use the Gmail API service to send the email
    setup_credentials()
    service = get_gmail_service()
    message = create_message(sender_email, recipient_email, subject, html_message_text, plain_message_text)
    send_gmail_message(service, 'me', message)

def normalize_phone_number(phone_number):
    return re.sub(r'\D', '', phone_number)

def serialize_firestore_data(doc):
    if doc.exists:
        def serialize_value(value):
            if isinstance(value, datetime):
                return value.isoformat()
            elif isinstance(value, list):
                return [serialize_value(item) for item in value]
            elif isinstance(value, dict):
                return {k: serialize_value(v) for k, v in value.items()}
            else:
                return value
        
        data = doc.to_dict()
        return {k: serialize_value(v) for k, v in data.items()}
    else:
        return None

def normalize_call_status(status):
    normalized_status = re.sub(r'[^a-z0-9 ]', '', status.lower())
    normalized_status = normalized_status.replace(" ", "")
    return normalized_status

def grab_call_info(call_id):
    try:
        doc_ref = db.collection('Calls').document(call_id)
        doc = doc_ref.get()

        if doc.exists:
            print("Successfully fetched call information.")
            return doc.to_dict()
        else:
            print("Call information not found.")
            return None
    except Exception as e:
        print(f"Error fetching call information: {e}")
        return None

def grab_insights_instructions(flow_id):
    try:
        flow_doc = db.collection('Flows').document(flow_id).get()
        if flow_doc.exists:
            prompt_params = flow_doc.get('prompt_parameters')
            insights_id = prompt_params.get('insights_id')
            insights_doc = db.collection('Insights').document(insights_id).get()
            if insights_doc.exists:
                return insights_doc.to_dict()
            else:
                print("Insights not found.")
        else:
            print("Flow document not found.")
            return None
    except Exception as e:
        print(f"Error fetching insights: {e}")
        return None

def find_contact_by_phone_and_org(phone_number, organization_id):
    try:
        contacts_ref = db.collection('Contacts')
        query = contacts_ref.where('phoneNumber', '==', normalize_phone_number(phone_number)).where('organization_id', '==', organization_id).limit(1)
        results = query.get()
        if results:
            return results[0].reference
        else:
            return None
    except Exception as e:
        print(f"Error finding contact: {e}")
        return None

@functions_framework.http
def call_processor(request):
    request_data = request.get_json(silent=True)
    if not request_data:
        return abort(400, "Bad Request: No JSON payload provided.")

    call_id = request_data.get("call_id", "")
    
    # Extract all necessary data from request_data
    call_length = request_data.get("call_length", 0)
    to_number = request_data.get("to", "")
    from_number = request_data.get("from", "")
    language = request_data.get("request_data", {}).get("language", "")
    completed = request_data.get("completed", False)
    created_at = request_data.get("created_at", "")
    inbound = request_data.get("inbound", False)
    queue_status = request_data.get("queue_status", "")
    endpoint_url = request_data.get("endpoint_url", "")
    max_duration = request_data.get("max_duration", 0)
    error_message = request_data.get("error_message", "")
    answered_by = request_data.get("answered_by", "")
    recording_url = request_data.get("recording_url", "")
    concatenated_transcript = request_data.get("concatenated_transcript", "")
    status = request_data.get("status", "")
    corrected_duration = request_data.get("corrected_duration", "")
    end_at = request_data.get("end_at", "")
    call_cost = request_data.get("price", 0)
    summary = request_data.get("summary", "")
    
    metadata = request_data.get("metadata", {})
    organization_id = metadata.get("organization_id", "")


    # Handle inbound calls differently
    if inbound:
        is_test = False
        return process_inbound_call(from_number, organization_id, call_id, call_length, to_number, language, completed, created_at, inbound, queue_status, endpoint_url, max_duration, error_message, recording_url, concatenated_transcript, status, corrected_duration, end_at, call_cost, summary, is_test)

    # For outbound calls, proceed with existing logic
    call_data = grab_call_info(call_id)
    if call_data is None:
        return jsonify({"success": False, "message": "Failed to fetch call information."})
    
    is_test = call_data.get('original_request', {}).get('test', False)
    
    call_status_result_unclean = call_status(openai_client, concatenated_transcript, is_test)
    call_status_result = normalize_call_status(call_status_result_unclean)

    if "answered" in call_status_result:
        return process_answered_call(call_id, call_length, to_number, from_number, language, completed, created_at, inbound, queue_status, endpoint_url, max_duration, error_message, recording_url, concatenated_transcript, status, corrected_duration, end_at, call_cost, organization_id, is_test)
    elif "voicemail" in call_status_result:
        return process_voicemail_call(call_id, call_length, to_number, from_number, language, completed, created_at, inbound, queue_status, endpoint_url, max_duration, error_message, recording_url, concatenated_transcript, status, corrected_duration, end_at, call_cost, is_test)
    else: 
        return process_no_answer_call(call_id, call_length, to_number, from_number, language, completed, created_at, inbound, queue_status, endpoint_url, max_duration, error_message, recording_url, concatenated_transcript, status, corrected_duration, end_at, call_cost, is_test)

def process_inbound_call(from_number, organization_id, call_id, call_length, to_number, language, completed, created_at, inbound, queue_status, endpoint_url, max_duration, error_message, recording_url, concatenated_transcript, status, corrected_duration, end_at, call_cost, summary, is_test):
    contact_ref = find_contact_by_phone_and_org(from_number, organization_id)
    if contact_ref is None:
        contact_data = {
            'phoneNumber': normalize_phone_number(from_number),
            'organization_id': organization_id,
            'activeFlows': [],
            'finishedFlows': [],
            'lastCallAnswered': created_at,
            'callTimestamp': created_at,
            'recentOutcome': "inbound",
            'created_at': datetime.utcnow()
        }
        contact_ref = db.collection('Contacts').add(contact_data)[1]
        contact_id = contact_ref.id
    else:
        contact_id = contact_ref.id

    doc_ref = db.collection('Calls').document(call_id)
    try:
        doc_ref.set({
            "call_id": call_id,
            "callTimestamp": datetime.utcnow(),
            "call_length": call_length,
            "to_number": to_number,
            "from_number": from_number,
            "language": language,
            "completed": completed,
            "created_at": created_at,
            "inbound": inbound,
            "queue_status": queue_status,
            "endpoint_url": endpoint_url,
            "max_duration": max_duration,
            "error_message": error_message,
            "answered_by": 'human',
            "recording_url": recording_url,
            "concatenated_transcript": concatenated_transcript,
            "status": status,
            "corrected_duration": corrected_duration,
            "end_at": end_at,
            "call_cost": call_cost,
            "call_analysis": {
                "outcome": "inbound",
                "summary": summary
            },
            "original_request": {
                "contact_id": contact_id,
                "organization_id": organization_id
            },
            "processed_at": firestore.SERVER_TIMESTAMP,
            "is_test": is_test
        })
        
        # Remove the reference to request_data and use the function parameters
        update_contact_in_contacts(from_number, organization_id, None, "inbound", call_id, created_at, is_test)

        return jsonify({"success": True, "message": "Inbound call data processed and stored successfully."})
    except Exception as e:
        return jsonify({"success": False, "message": "Failed to store inbound call data."})

def process_answered_call(call_id, call_length, to_number, from_number, language, completed, created_at, inbound, queue_status, endpoint_url, max_duration, error_message, recording_url, concatenated_transcript, status, corrected_duration, end_at, call_cost, organization_id, is_test):
    call_made_info = grab_call_info(call_id)
    if call_made_info is None:
        return jsonify({"success": False, "message": "Failed to fetch call information."})
    
    original_request = call_made_info.get('original_request', {})
    insights_instructions = grab_insights_instructions(original_request['flow_id'])
    if insights_instructions is None:
        return jsonify({"success": False, "message": "Failed to fetch system prompt."})

    insights_response = call_insights(openai_client, insights_instructions, concatenated_transcript, is_test)

    try:
        insights_data = json.loads(insights_response.get("insights", "{}"))

    except json.JSONDecodeError as e:
        return jsonify({"success": False, "message": "Failed to parse analysis response."})

    try:
        doc_ref = db.collection('Calls').document(call_id)
        doc_ref.update({
            "call_length": call_length,
            "to_number": to_number,
            "from_number": from_number,
            "language": language,
            "completed": completed,
            "created_at": created_at,
            "inbound": inbound,
            "queue_status": queue_status,
            "endpoint_url": endpoint_url,
            "max_duration": max_duration,
            "error_message": error_message,
            "answered_by": 'human',
            "recording_url": recording_url,
            "concatenated_transcript": concatenated_transcript,
            "status": status,
            "corrected_duration": corrected_duration,
            "end_at": end_at,
            "call_cost": call_cost,
            "call_analysis": insights_data,
            "processed_at": firestore.SERVER_TIMESTAMP,
            "is_test": is_test
        })
        
        contact_id = original_request.get('contact_id')
        update_contact_in_contacts(to_number, organization_id, original_request.get('flow_id', ''), insights_data.get('outcome'), call_id, created_at, is_test)

        return jsonify({"success": True, "message": "Call data processed and stored successfully."})
    except Exception as e:
        return jsonify({"success": False, "message": "Failed to store call analysis."})

def process_voicemail_call(call_id, call_length, to_number, from_number, language, completed, created_at, inbound, queue_status, endpoint_url, max_duration, error_message, recording_url, concatenated_transcript, status, corrected_duration, end_at, call_cost, is_test):
    doc_ref = db.collection('Calls').document(call_id)
    doc_ref.update({
        "call_length": call_length,
        "to_number": to_number,
        "from_number": from_number,
        "language": language,
        "completed": completed,
        "created_at": created_at,
        "inbound": inbound,
        "queue_status": queue_status,
        "endpoint_url": endpoint_url,
        "max_duration": max_duration,
        "error_message": error_message,
        "answered_by": 'voicemail',
        "recording_url": recording_url,
        "concatenated_transcript": concatenated_transcript,
        "status": status,
        "corrected_duration": corrected_duration,
        "end_at": end_at,
        "call_cost": call_cost,
        "processed_at": firestore.SERVER_TIMESTAMP,
        "is_test": is_test
    })
    return jsonify({"success": True, "message": "Voicemail. Call data stored successfully."})

def process_no_answer_call(call_id, call_length, to_number, from_number, language, completed, created_at, inbound, queue_status, endpoint_url, max_duration, error_message, recording_url, concatenated_transcript, status, corrected_duration, end_at, call_cost, is_test):
    doc_ref = db.collection('Calls').document(call_id)
    doc_ref.update({
        "call_length": call_length,
        "to_number": to_number,
        "from_number": from_number,
        "language": language,
        "completed": completed,
        "created_at": created_at,
        "inbound": inbound,
        "queue_status": queue_status,
        "endpoint_url": endpoint_url,
        "max_duration": max_duration,
        "error_message": error_message,
        "answered_by": 'no answer',
        "recording_url": recording_url,
        "concatenated_transcript": concatenated_transcript,
        "status": status,
        "corrected_duration": corrected_duration,
        "end_at": end_at,
        "call_cost": call_cost,
        "processed_at": firestore.SERVER_TIMESTAMP,
        "is_test": is_test
    })
    return jsonify({"success": True, "message": "No answer. Call data stored successfully."})

def update_contact_in_contacts(phone_number, organization_id, flow_id, outcome, call_id, created_at, is_test):
    print(f"Entering update_contact_in_contacts. Phone: {phone_number}, Org ID: {organization_id}, Flow ID: {flow_id}, Outcome: {outcome}")
    try:
        contact_ref = find_contact_by_phone_and_org(phone_number, organization_id)
        
        if contact_ref is None:
            print(f"No existing contact found for phone {phone_number} and org {organization_id}. Creating new contact.")
            contact_data = {
                'phoneNumber': normalize_phone_number(phone_number),
                'organization_id': organization_id,
                'activeFlows': [],
                'finishedFlows': [],
                'lastCallAnswered': created_at,
                'callTimestamp': created_at,
                'recentOutcome': outcome,
                'created_at': datetime.utcnow()
            }
            contact_ref = db.collection('Contacts').add(contact_data)[1]
            print(f"New contact added with ID: {contact_ref.id}")
        else:
            print(f"Existing contact found with ID: {contact_ref.id}")

        contact_doc = contact_ref.get()
        print(f"Contact doc exists: {contact_doc.exists}")

        if contact_doc.exists:
            print(f"Processing existing contact document {contact_ref.id}")
            contact_data = contact_doc.to_dict()
            active_flows = contact_data.get('activeFlows', [])
            finished_flows = contact_data.get('finishedFlows', [])
            print(f"Current active flows: {json.dumps(active_flows, indent=2)}")
            print(f"Current finished flows: {json.dumps(finished_flows, indent=2)}")

            flow_to_update = next((flow for flow in active_flows if flow['flow_id'] == flow_id), None)
            print(f"Flow to update: {json.dumps(flow_to_update, indent=2)}")

            if flow_to_update:
                print(f"Flow {flow_id} found in active flows. Updating status.")
                flow_to_update['status'] = 'success'
                flow_to_update['outcome'] = outcome
                flow_to_update['call_id'] = call_id
                finished_flows.append(flow_to_update)
                active_flows = [flow for flow in active_flows if flow['flow_id'] != flow_id]
                print(f"Updated active flows: {json.dumps(active_flows, indent=2)}")
                print(f"Updated finished flows: {json.dumps(finished_flows, indent=2)}")
            else:
                print(f"Flow {flow_id} not found in active flows. Checking finished flows.")
                recent_finished_flow = None
                try:
                    recent_finished_flow = max(
                        (flow for flow in finished_flows if flow['flow_id'] == flow_id),
                        key=lambda x: x.get('createdAt', datetime.min)
                    )
                except ValueError:
                    print("No finished flows with the given flow_id found.")
                
                if recent_finished_flow:
                    print(f"Updating recent finished flow {flow_id}.")
                    recent_finished_flow['status'] = 'success'
                    recent_finished_flow['outcome'] = outcome
                    recent_finished_flow['call_id'] = call_id
                else:
                    print(f"No flow found with ID {flow_id}. This is unexpected.")
                    print("Debugging information:")
                    print(f"Flow ID we're looking for: {flow_id}")
                    print("All flow IDs in active flows:")
                    for flow in active_flows:
                        print(f"- {flow.get('flow_id')}")
                    print("All flow IDs in finished flows:")
                    for flow in finished_flows:
                        print(f"- {flow.get('flow_id')}")

            print(f"Updating contact document {contact_ref.id} with new data.")
            update_data = {
                'activeFlows': active_flows,
                'finishedFlows': finished_flows,
                'callTimestamp': created_at,
                'lastCallAnswered': created_at,
                'recentOutcome': outcome
            }
            contact_ref.update(update_data)
            print(f"Contact {contact_ref.id} updated successfully with data: {json.dumps(update_data, indent=2)}")

            # Verify the update
            updated_contact = contact_ref.get().to_dict()
            print("Contact document after update:")
            print(f"Active flows: {json.dumps(updated_contact.get('activeFlows', []), indent=2)}")
            print(f"Finished flows: {json.dumps(updated_contact.get('finishedFlows', []), indent=2)}")

            org_id = contact_data.get('organization_id')
            print(f"Organization ID from contact document: {org_id}")
            if org_id:
                org_doc = db.collection('Organizations').document(org_id).get()
                if org_doc.exists:
                    org_data = org_doc.to_dict()
                    print(f"Organization data retrieved: {org_data}")
                    
                    sync_link = org_data.get('sync_link')
                    notification_email = org_data.get('notification_email')
                    print(f"Sync link: {sync_link}, Notification email: {notification_email}")
                    if sync_link or notification_email:
                        print("Sending data to sync and/or notification email.")
                        send_data_to_sync(contact_ref, db.collection('Calls').document(call_id), sync_link, notification_email, is_test)
                    else:
                        print("Sync link and notification email not found in the organization document.")
                else:
                    print(f"Organization document for ID {org_id} does not exist.")
            else:
                print("Organization ID not found in the contact document.")
        else:
            print(f"Contact document {contact_ref.id} does not exist, which is unexpected at this point.")

        print("Contact update process completed successfully.")
        return True

    except Exception as e:
        print(f"Error in update_contact_in_contacts: {str(e)}")
        return False

def send_data_to_sync(contact_doc_ref, call_doc_ref, sync_link, notification_email, is_test):
    try:
        contact_doc_snapshot = contact_doc_ref.get()
        call_doc_snapshot = call_doc_ref.get()

        contact_data = serialize_firestore_data(contact_doc_snapshot)
        call_data = serialize_firestore_data(call_doc_snapshot)

        if contact_data and call_data:
            call_data.pop('call_cost', None)

            payload = {
                'contact': contact_data,
                'call': call_data,
                'flow_status': 'answered'
            }

            if sync_link:
                try:
                    response = requests.post(sync_link, json=payload)
                    response.raise_for_status()
                except requests.exceptions.RequestException as req_err:
                    print(f"Failed to send data to sync link: {req_err}")

            # Send notification email
            if notification_email:
                send_notification_email(contact_data, call_data, notification_email)

    except Exception as e:
        print(f"An error occurred in send_data_to_sync: {e}")

def call_status(client, transcript, is_test):
    system_prompt = ("""
    "Analyze the phone call transcript and determine the call status as 'answered', 'voicemail', or 'no answer'.
    - The participants in the call are labeled as 'user' and 'assistant'. Dialogue from the user is indicated with 'user:', and dialogue from the assistant begins with 'assistant:'.
    - Consider the call as 'answered' if the responses under 'user:' are indicative of live interaction, showing that an actual person is responding and engaging in conversation.
    - Consider the call as 'voicemail' if the 'user:' responses sound like a standard voicemail greeting or message, indicating that the assistant is speaking to a voicemail system.
    - Consider the call as 'no answer' if there is no 'user:' dialogue, suggesting the phone was not picked up.
    Only return one of these three options based on the analysis: 'answered', 'voicemail', or 'no answer'. Do not include any other output."
    """)
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": transcript}
            ],
            temperature=0.0
        )
        
        call_status = response.choices[0].message.content.strip()
        
        if call_status not in ['answered', 'voicemail']:
            call_status = 'no answer'
        
        return call_status
    except Exception as e:
        print(f"Error during call status determination: {e}")
        return "error"

def call_insights(client, system_prompt, transcript, is_test):
    json_example = {
        "outcome": "Example Outcome",
        "answers": {
            "Example Question Title": "Example Answer"
        },
        "summary": "Example brief summary of the call."
    }
    
    json_example_str = json.dumps(json_example, indent=2)
    
    conversation_context = system_prompt.get("script_context", "")
    questions_to_answer = system_prompt.get("questions_to_answer", {})
    outcomes_to_determine = system_prompt.get("outcomes", {})

    crafted_system_prompt = f"Your job is to analyze phone conversation transcripts. The contact's dialogue always begins with 'user:' the Assistant's dialogue always begins with 'assistant:' \n\n"
    crafted_system_prompt += "Instructions:\n"
    crafted_system_prompt += "Based on the transcript, determine the best fit outcome and answer the questions provided. "
    crafted_system_prompt += "Summarize the call, following the JSON structure shown in the example below.\n\n"
    crafted_system_prompt += f"Example JSON structure:\n{json_example_str}\n\n"
    
    crafted_system_prompt += "Outcomes to consider:\n"
    for outcome, description in outcomes_to_determine.items():
        crafted_system_prompt += f"- {outcome}: {description}\n"
    
    crafted_system_prompt += "\nQuestions to answer:\n"
    for title, question in questions_to_answer.items():
        crafted_system_prompt += f"- {title}: {question}\n"
    
    crafted_system_prompt += "\nPlease structure the response as a JSON object including the best fit outcome, "
    crafted_system_prompt += "answers to the questions, and a summary of the conversation. "
    crafted_system_prompt += "Omit any questions that cannot be answered based on the transcript. "
    crafted_system_prompt += "The response should strictly follow the example's structure and include nothing beyond it."
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": crafted_system_prompt},
                {"role": "user", "content": transcript}
            ],
            temperature=0.3,
        )
        
        analysis_response = response.choices[0].message.content.strip()
        
        return {"insights": analysis_response}
    except Exception as e:
        print(f"Error during call analysis: {e}")
        return {"error": str(e)}
