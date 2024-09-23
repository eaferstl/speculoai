import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud import tasks_v2
from google.api_core import exceptions
import datetime
import pytz
import json

# Initialize the Firebase Admin SDK if not already initialized
if not firebase_admin._apps:
    try:
        firebase_admin.get_app()
    except ValueError:
        cred = credentials.ApplicationDefault()
        firebase_admin.initialize_app(cred)

def batch_cancel_flow(flow_id, batch_size=500):
    db = firestore.client()
    tasks_client = tasks_v2.CloudTasksClient()
    
    # Get all contacts for this flow
    flow_contacts = db.collection('Flows').document(flow_id).collection('flow_contacts').stream()
    
    contact_count = 0
    tasks_to_delete = []
    
    for flow_contact in flow_contacts:
        contact_id = flow_contact.id
        contact_ref = db.collection('Contacts').document(contact_id)
        flow_contact_ref = db.collection('Flows').document(flow_id).collection('flow_contacts').document(contact_id)
        
        # Transaction to ensure atomic updates
        @firestore.transactional
        def update_contact_in_transaction(transaction):
            contact_snapshot = contact_ref.get(transaction=transaction)
            flow_contact_snapshot = flow_contact_ref.get(transaction=transaction)
            
            if contact_snapshot.exists:
                contact_data = contact_snapshot.to_dict()
                active_flows = contact_data.get('activeFlows', [])
                
                # Remove the flow from activeFlows
                updated_active_flows = [flow for flow in active_flows if flow['flow_id'] != flow_id]
                transaction.update(contact_ref, {'activeFlows': updated_active_flows})
                
                # Get the Cloud Task ID if it exists
                canceled_flow = next((flow for flow in active_flows if flow['flow_id'] == flow_id), None)
                if canceled_flow and 'cloud_task_id' in canceled_flow:
                    tasks_to_delete.append(canceled_flow['cloud_task_id'])
            
            if flow_contact_snapshot.exists:
                # Remove the isScheduled flag from the flow_contacts subcollection
                transaction.update(flow_contact_ref, {'isScheduled': firestore.DELETE_FIELD})
        
        # Run the transaction
        transaction = db.transaction()
        update_contact_in_transaction(transaction)
        
        contact_count += 1
        
        # Process task deletions in batches
        if contact_count % batch_size == 0:
            delete_cloud_tasks(tasks_to_delete)
            tasks_to_delete = []

    # Process any remaining task deletions
    if tasks_to_delete:
        delete_cloud_tasks(tasks_to_delete)
    
    # Update the flow status to 'canceled' in the Flows collection
    db.collection('Flows').document(flow_id).update({'status': 'draft'})
    
    return f"Canceled flow {flow_id} for {contact_count} contacts"

def delete_cloud_tasks(task_ids):
    tasks_client = tasks_v2.CloudTasksClient()
    for task_id in task_ids:
        task_name = tasks_client.task_path('heyisaai', 'us-central1', 'scheduled-flows', task_id)
        try:
            tasks_client.delete_task(name=task_name)
            print(f"Deleted task {task_id}")
        except exceptions.NotFound:
            print(f"Task {task_id} not found. It may have already been executed or deleted.")
        except Exception as e:
            print(f"Error deleting task {task_id}: {str(e)}")

def cancel_flow(request):
    """Cloud Function entry point for canceling a flow."""
    if request.method != 'POST':
        return json.dumps({'error': 'Send a POST request'}), 405, {'Content-Type': 'application/json'}
    
    try:
        request_json = request.get_json(silent=True)
        flow_id = request_json.get('flow_id')
        
        if not flow_id:
            return json.dumps({'error': 'flow_id is required'}), 400, {'Content-Type': 'application/json'}
        
        result = batch_cancel_flow(flow_id)
        return json.dumps({'result': result}), 200, {'Content-Type': 'application/json'}
    except Exception as e:
        return json.dumps({'error': str(e)}), 500, {'Content-Type': 'application/json'}