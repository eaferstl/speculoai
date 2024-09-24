from flask import jsonify, request
from google.cloud import firestore

def google_function(request):
    # Parse the request JSON data
    request_data = request.get_json()
    print("Request JSON data:", request_data)

    # Extract the phone number and remove the '+' if present
    phone_number = request_data.get('phone_number', '').replace('+', '')
    print("Clean phone number received:", phone_number)

    # Retrieve data for the specified phone number from Firestore
    team_member_data, doc_id = get_data_from_firestore(phone_number)
    print("Team member data fetched:", team_member_data)

    # Structure the data according to the provided template
    response_data = format_response_data(team_member_data, doc_id)
    print("Structured response data:", response_data)

    # Convert the structured data into JSON and return it
    return jsonify(response_data)

def get_data_from_firestore(phone_number):
    db = firestore.Client()
    # Reference to the TeamMembers collection
    team_members_ref = db.collection('TeamMembers')

    # Search for the document with the specified clean phone number
    docs = team_members_ref.where('phone', '==', phone_number).stream()

    # Assuming that phone numbers are unique and there will only be one match
    for doc in docs:
        doc_data = doc.to_dict()
        doc_id = doc.id
        print("Document found:", doc_data)  # Debug: Print the document data
        return doc_data, doc_id

    print("No document found for phone number:", phone_number)  # Debug: Print a message if no document is found
    return None, None

def format_response_data(team_member_data, doc_id):
    if not team_member_data:
        print("No team member data to format")  # Debug: Print a message if no data to format
        return None  # or return an error message

    # Add the document ID as 'team_member_id'
    team_member_data['team_member_id'] = doc_id
    return team_member_data

# Assuming the rest of the functions remain unchanged
