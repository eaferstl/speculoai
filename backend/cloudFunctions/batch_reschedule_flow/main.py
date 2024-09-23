import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud import tasks_v2
from google.protobuf import timestamp_pb2, field_mask_pb2
import datetime
import pytz
import random
import json
import functions_framework

# Initialize the Firebase Admin SDK if not already initialized
if not firebase_admin._apps:
    try:
        firebase_admin.get_app()
    except ValueError:
        cred = credentials.ApplicationDefault()
        firebase_admin.initialize_app(cred)

# Firestore client
db = firestore.client()

def query_document(doc_id, collection):
    """Query a single document by document ID."""
    print(f"Querying document ID: {doc_id} in collection: {collection}")
    doc_ref = db.collection(collection).document(doc_id)
    try:
        doc = doc_ref.get()
        if doc.exists:
            print(f"Document found: {doc_id}")
            return doc.to_dict()
        else:
            print(f"No document found with ID: {doc_id} in {collection}")
            return None
    except Exception as e:
        print(f"Error querying document {doc_id} in {collection}: {str(e)}")
        return None

def schedule_cloud_task(task_type, scheduled_for, payload):
    """Schedule or reschedule a Cloud Task to trigger a workflow at a random time within the specified hour."""
    print(f"Scheduling/Rescheduling Cloud Task for type: {task_type}, scheduled for: {scheduled_for} with payload: {payload}")
    project_id = 'heyisaai'
    location = 'us-central1'
    queue_name = 'scheduled-flows'
    service_account_email = "54875993561-compute@developer.gserviceaccount.com"
    url_map = {
        'Engage': "https://us-central1-heyisaai.cloudfunctions.net/scheduled_engage",
        'Revive': "https://us-central1-heyisaai.cloudfunctions.net/scheduled_revive"
    }
    
    # Calculate the schedule time with random offset
    tz = pytz.timezone(payload['timezone'])
    scheduled_datetime = datetime.datetime.fromisoformat(scheduled_for).astimezone(tz)
    
    # Check if the scheduled time is in the past
    now = datetime.datetime.now(tz)
    if scheduled_datetime < now:
        raise ValueError("Cannot schedule a task in the past")
    
    # Check if the scheduled time is more than 30 days in the future
    max_future_time = now + datetime.timedelta(days=30)
    if scheduled_datetime > max_future_time:
        print(f"Warning: Scheduled time {scheduled_datetime} is more than 30 days in the future. Capping at {max_future_time}")
        scheduled_datetime = max_future_time
    
    # Generate a random offset within the hour (0 to 59 minutes, 0 to 59 seconds)
    random_offset = datetime.timedelta(minutes=random.randint(0, 59), seconds=random.randint(0, 59))
    randomized_datetime = scheduled_datetime.replace(minute=0, second=0, microsecond=0) + random_offset
    
    schedule_time = timestamp_pb2.Timestamp()
    schedule_time.FromDatetime(randomized_datetime.astimezone(pytz.UTC))

    # Prepare Cloud Tasks client
    client = tasks_v2.CloudTasksClient()
    parent = client.queue_path(project_id, location, queue_name)
    
    # Construct the task
    task = {
        "schedule_time": schedule_time,
        "http_request": {
            "http_method": tasks_v2.HttpMethod.POST,
            "url": url_map[task_type],
            "oidc_token": {
                "service_account_email": service_account_email
            },
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(payload).encode()
        }
    }

    # Check if a task already exists for this flow and contact
    existing_task_id = payload.get('cloud_task_id')
    if existing_task_id:
        try:
            # Try to delete the existing task
            task_name = client.task_path(project_id, location, queue_name, existing_task_id)
            client.delete_task(name=task_name)
            print(f"Existing task {existing_task_id} deleted successfully")
        except Exception as e:
            print(f"Error deleting existing task {existing_task_id}: {str(e)}")
            # Continue with creating a new task even if deletion fails

    # Create a new task
    try:
        response = client.create_task(parent=parent, task=task)
        print(f"New task created: {response.name} for {task_type} with scheduled time {randomized_datetime}")
        task_id = response.name.split('/')[-1]
    except Exception as e:
        print(f"Error creating new task: {str(e)}")
        raise

    return task_id, randomized_datetime.isoformat()

def batch_reschedule_flow(flow_id, new_scheduled_time, batch_size=500):
    # Get flow information
    flow_info = query_document(flow_id, 'Flows')
    if not flow_info:
        error_message = f"Flow information not found for flow_id: {flow_id}"
        print(error_message)
        return error_message

    task_type = flow_info.get('flow_type')
    prompt_parameters = flow_info.get('prompt_parameters', {})

    # Check if the new scheduled time is in the past
    now = datetime.datetime.now(pytz.UTC)
    new_scheduled_datetime = datetime.datetime.fromisoformat(new_scheduled_time).astimezone(pytz.UTC)
    if new_scheduled_datetime < now:
        error_message = "Cannot reschedule a flow to a time in the past"
        print(error_message)
        return error_message

    # Get all contacts for this flow
    flow_contacts = db.collection('Flows').document(flow_id).collection('flow_contacts').stream()
    
    rescheduled_count = 0
    errors = []

    for flow_contact in flow_contacts:
        contact_id = flow_contact.id
        contact_ref = db.collection('Contacts').document(contact_id)
        contact_data = contact_ref.get().to_dict()

        if not contact_data:
            errors.append(f"Contact data not found for contact_id: {contact_id}")
            continue

        organization_id = contact_data.get('organization_id')
        organization_info = query_document(organization_id, 'Organizations')

        if not organization_info:
            errors.append(f"Organization info not found for organization_id: {organization_id}")
            continue

        # Prepare payload for Cloud Task
        payload = {
            'contact_id': contact_id,
            'flow_id': flow_id,
            'script_id': prompt_parameters.get('script_id', ''),
            'insights_id': prompt_parameters.get('insights_id', ''),
            'rules_id': prompt_parameters.get('rules_id', ''),
            'general_knowledgebase_id': prompt_parameters.get('general_knowledgebase_id', ''),
            'specific_knowledgebase_id': prompt_parameters.get('specific_knowledgebase_id', ''),
            'organization_id': organization_id,
            'timezone': organization_info.get('timezone', 'UTC')
        }

        # Add existing cloud_task_id to payload if it exists
        existing_flow = next((flow for flow in contact_data.get('activeFlows', []) if flow['flow_id'] == flow_id), None)
        if existing_flow and 'cloud_task_id' in existing_flow:
            payload['cloud_task_id'] = existing_flow['cloud_task_id']

        # Schedule new Cloud Task or update existing one
        try:
            task_id, actual_scheduled_time = schedule_cloud_task(task_type, new_scheduled_time, payload)
        except ValueError as e:
            errors.append(f"Error scheduling Cloud Task for contact {contact_id}: {str(e)}")
            continue
        except Exception as e:
            errors.append(f"Unexpected error scheduling Cloud Task for contact {contact_id}: {str(e)}")
            continue

        # Update activeFlow in contact document
        active_flows = contact_data.get('activeFlows', [])
        flow_updated = False

        for flow in active_flows:
            if flow['flow_id'] == flow_id:
                flow['nextStepTime'] = new_scheduled_time
                flow['actualScheduledTime'] = actual_scheduled_time
                flow['status'] = 'scheduled'
                flow['cloud_task_id'] = task_id
                flow_updated = True
                break

        if not flow_updated:
            # If the flow wasn't in activeFlows, add it
            active_flows.append({
                'flow_id': flow_id,
                'nextStepTime': new_scheduled_time,
                'actualScheduledTime': actual_scheduled_time,
                'status': 'scheduled',
                'cloud_task_id': task_id,
                'type': task_type
            })

        # Update the contact document
        contact_ref.update({'activeFlows': active_flows})

        rescheduled_count += 1

        # Print progress for every batch
        if rescheduled_count % batch_size == 0:
            print(f"Processed {rescheduled_count} contacts")
        # After processing all contacts, update the flow document

    flow_ref = db.collection('Flows').document(flow_id)
    flow_ref.update({
        'scheduled_for': new_scheduled_time,
        'status': 'scheduled',
        'updated_at': datetime.datetime.now(pytz.UTC).isoformat()
    })

    result_message = f"Rescheduled {rescheduled_count} contacts for flow {flow_id}"
    if errors:
        result_message += f". Encountered {len(errors)} errors."

    print(result_message)
    if errors:
        print("Errors encountered:", errors)

    return result_message

@functions_framework.http
def reschedule_flow(request):
    """Cloud Function entry point for rescheduling a flow."""
    if request.method != 'POST':
        return json.dumps({'error': 'Send a POST request'}), 405, {'Content-Type': 'application/json'}
    
    try:
        request_json = request.get_json(silent=True)
        flow_id = request_json.get('flow_id')
        new_scheduled_time = request_json.get('new_scheduled_time')
        
        if not flow_id or not new_scheduled_time:
            return json.dumps({'error': 'flow_id and new_scheduled_time are required'}), 400, {'Content-Type': 'application/json'}
        
        result = batch_reschedule_flow(flow_id, new_scheduled_time)
        return json.dumps({'result': result}), 200, {'Content-Type': 'application/json'}
    except Exception as e:
        return json.dumps({'error': str(e)}), 500, {'Content-Type': 'application/json'}