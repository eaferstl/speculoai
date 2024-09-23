import hashlib
import logging
from flask import jsonify, request
from google.cloud import firestore
import functions_framework

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@functions_framework.http
def create_live_transfer(request):
    logger.info(f"Received request: Method={request.method}, Content-Type={request.content_type}")
    
    # Handle OPTIONS request for CORS
    if request.method == 'OPTIONS':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Max-Age': '3600'
        }
        return ('', 204, headers)

    if request.method != 'POST':
        logger.warning(f"Invalid request method: {request.method}")
        return jsonify({'error': 'Only POST requests are accepted'}), 405

    try:
        # Get the JSON data from the request
        data = request.get_json()
        logger.info(f"Received data: {data}")

        # Validate required fields
        required_fields = ['from', 'transfer_number', 'to']
        for field in required_fields:
            if field not in data:
                logger.error(f"Missing required field: {field}")
                return jsonify({'error': f'Missing required field: {field}'}), 400

        # Generate a unique hash for the request to identify duplicates
        unique_string = f"{data['from']}_{data['to']}_{data['transfer_number']}_{data.get('reason_say', '')}"
        request_hash = hashlib.md5(unique_string.encode()).hexdigest()

        # Initialize Firestore client
        db = firestore.Client()

        # Check if a document with this hash already exists
        docs = db.collection('LiveTransfers').where('request_hash', '==', request_hash).get()
        if docs:
            logger.info(f"Duplicate request detected with hash: {request_hash}")
            return jsonify({'message': 'Duplicate request detected. No new document created.'}), 200

        # Prepare the document data
        doc_data = {
            'from': data['from'],
            'transfer_number': data['transfer_number'],
            'to': data['to'],
            'reason_say': data.get('reason_say', ''),
            'from_name': data.get('from_name', ''),
            'organization_id': data.get('organization_id', ''),
            'created_at': firestore.SERVER_TIMESTAMP,
            'processed': False,  # New field
            'answered': False,    # New field
            'request_hash': request_hash  # Store the unique hash
        }

        # Add the document to the LiveTransfers collection
        doc_ref = db.collection('LiveTransfers').add(doc_data)
        logger.info(f"Document created successfully with ID: {doc_ref[1].id}")

        return jsonify({
            'message': 'Document created successfully',
            'document_id': doc_ref[1].id
        }), 201

    except ValueError as ve:
        logger.error(f"ValueError: {str(ve)}")
        return jsonify({'error': 'Invalid JSON in request body'}), 400
    except firestore.exceptions.FirebaseError as fe:
        logger.error(f"Firestore error: {str(fe)}")
        return jsonify({'error': 'Database operation failed'}), 500
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        return jsonify({'error': 'An unexpected error occurred'}), 500

if __name__ == "__main__":
    app.run(host='127.0.0.1', port=8080, debug=True)