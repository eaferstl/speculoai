import functions_framework
import requests
import json
from google.cloud import firestore
from datetime import datetime
from urllib.parse import unquote

# Retool API configuration
RETOOL_API_URL = 'https://speculo.retool.com/api/v2/user_invites'
RETOOL_API_TOKEN = 'retool_01j42wk1bqz8za9wp09pa5c90c'

def create_retool_user(email, first_name, last_name, active=True, metadata=None):
    print(f"Attempting to create Retool user: {email}")
    if metadata is None:
        metadata = {}

    headers = {
        'Authorization': f'Bearer {RETOOL_API_TOKEN}',
        'Content-Type': 'application/json'
    }
    print(f"Headers for Retool API request: {headers}")

    data = {
        'email': email,
        'defaultGroupIds': [],
        'metadata': metadata
    }
    print(f"Data for Retool API request: {json.dumps(data, indent=2)}")

    try:
        print(f"Sending POST request to Retool API: {RETOOL_API_URL}")
        response = requests.post(RETOOL_API_URL, headers=headers, json=data)
        print(f"Retool API response status code: {response.status_code}")
        print(f"Retool API response content: {response.text}")
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Error in Retool API request: {str(e)}")
        raise

@functions_framework.http
def new_subscription(request):
    print("new_subscription function called")
    print(f"Request method: {request.method}")

    if request.method != 'POST':
        print("Request method is not POST, returning 405")
        return 'Only POST requests are accepted', 405

    print("Decoding form data")
    data = {key: unquote(value) for key, value in request.form.items()}
    print(f"Decoded form data: {json.dumps(data, indent=2)}")

    email = data.get('Email')
    first_name = data.get('First Name')
    last_name = data.get('Last Name')
    active = True
    metadata = {
        'Current CRM System': data.get('Current CRM System'),
        'Database Size': data.get('Database Size'),
        'Hubspot Object ID': data.get('Hubspot Object ID'),
        'Subscription Level': data.get('Subscription Level'),
        'Subscription Price': data.get('Subscription Price'),
        'Team Name': data.get('Team Name'),
        'Title of Client': data.get('Title of Client'),
        'Website URL': data.get('Website URL')
    }
    print(f"Extracted user details: email={email}, first_name={first_name}, last_name={last_name}")
    print(f"Metadata: {json.dumps(metadata, indent=2)}")

    try:
        print("Initializing Firestore client")
        db = firestore.Client()

        print("Preparing document for Firestore")
        doc_data = {
            'accepted_terms': True,
            'active': True,
            'active_subscription': True,
            'completed_setup': True,
            'createdAt': data.get('Account Created'),
            'email': email,
            'notification_email': email,
            'org_name': data.get('Team Name'),
            'org_phone': data.get('Phone Number'),
            'primary_contact': {
                'email': email,
                'name': f"{first_name} {last_name}",
                'phone': data.get('Phone Number')
            },
            'subscription': {
                'name': data.get('Subscription Level'),
                'monthly_price': float(data.get('Subscription Price', '0').replace('$', '').replace(',', '')),
            },
            'timezone': data.get('Time Zone', '').replace('_slash_', '/'),
            'users': [email]
        }
        print(f"Firestore document data: {json.dumps(doc_data, indent=2)}")

        print("Adding document to Firestore")
        doc_ref = db.collection('Organizations').document()
        doc_ref.set(doc_data)
        print(f"Document added to Firestore with ID: {doc_ref.id}")

        # Now that Firestore document is created, create user in Retool
        print("Attempting to create user in Retool")
        user = create_retool_user(email, first_name, last_name, active, metadata)
        print(f"User created in Retool: {json.dumps(user, indent=2)}")

        response_data = {
            'success': True,
            'message': 'User added to Firestore and created successfully in Retool',
            'firestore_doc_id': doc_ref.id,
            'retool_user': user
        }
        print(f"Preparing successful response: {json.dumps(response_data, indent=2)}")
        return json.dumps(response_data), 200, {'Content-Type': 'application/json'}

    except firestore.exceptions.FirestoreError as e:
        error_message = f"Error adding document to Firestore: {str(e)}"
        print(error_message)
        return json.dumps({
            'success': False,
            'message': error_message
        }), 500, {'Content-Type': 'application/json'}

    except requests.RequestException as e:
        error_message = f"Error creating user in Retool: {str(e)}"
        print(error_message)
        return json.dumps({
            'success': False,
            'message': error_message
        }), 500, {'Content-Type': 'application/json'}

    except Exception as e:
        error_message = f"Unexpected error: {str(e)}"
        print(error_message)
        return json.dumps({
            'success': False,
            'message': error_message
        }), 500, {'Content-Type': 'application/json'}