import base64
import json
from googleapiclient.discovery import build
from flask import jsonify

# Initialize the Gmail API service using the default service account
def get_gmail_service():
    return build('gmail', 'v1')

# Fetch the full email content using the message ID
def get_message(service, user_id, msg_id):
    message = service.users().messages().get(userId=user_id, id=msg_id, format='full').execute()
    return message

# Parse emails based on Pub/Sub event
def parse_emails(event, context):
    pubsub_message = base64.b64decode(event['data']).decode('utf-8')
    print(f'Received message: {pubsub_message}')

    # Extract the email address and message ID from the Pub/Sub message
    message_data = json.loads(pubsub_message)
    email_address = message_data.get('emailAddress')
    message_id = message_data.get('historyId')  # Assuming this is actually the message ID

    service = get_gmail_service()
    user_id = 'me'

    # Fetch the full email using the message ID
    full_message = get_message(service, user_id, message_id)
    if full_message:
        # Do something with the full email content, e.g., log it, store it in a database, etc.
        print(json.dumps(full_message, indent=2))
        return jsonify(full_message)
    else:
        return jsonify({'message': 'No message found'})

    return 'OK'
