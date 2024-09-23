from google.cloud import firestore
import datetime

db = firestore.Client()

def query_document_by_id(collection, doc_id):
    try:
        doc_ref = db.collection(collection).document(doc_id)
        doc = doc_ref.get()
        if doc.exists:
            data = doc.to_dict()
            data['id'] = doc.id  # Add the document ID to the data
            return data
        return None
    except Exception as e:
        print(f"Error fetching document by ID: {str(e)}")
        return None

def get_organization_config(org_id):
    org_ref = db.collection('Organizations').document(org_id)
    org_doc = org_ref.get()
    if org_doc.exists:
        org_data = org_doc.to_dict()
        return org_data.get('config', {})
    return {}

def update_organization_config(org_id, new_config):
    org_ref = db.collection('Organizations').document(org_id)
    org_ref.set({'config': new_config}, merge=True)

def get_call_count(contact_id, flow_id):
    contact_ref = db.collection('Contacts').document(contact_id)
    contact_doc = contact_ref.get()
    if contact_doc.exists:
        contact_data = contact_doc.to_dict()
        active_flows = contact_data.get('activeFlows', [])
        if not isinstance(active_flows, list):
            print(f"Warning: activeFlows for contact {contact_id} is not a list. Returning 0.")
            return 0
        for flow in active_flows:
            if isinstance(flow, dict) and flow.get('flow_id') == flow_id:
                return flow.get('callCounter', 0)
    return 0

def update_contact_flow(contact_id, flow_id, max_attempts):
    try:
        contact_ref = db.collection('Contacts').document(contact_id)
        contact_doc = contact_ref.get()
        if contact_doc.exists:
            contact_data = contact_doc.to_dict()
            active_flows = contact_data.get('activeFlows', [])
            finished_flows = contact_data.get('finishedFlows', [])
            
            flow_updated = False
            for flow in active_flows:
                if isinstance(flow, dict) and flow.get('flow_id') == flow_id:
                    flow['callCounter'] = flow.get('callCounter', 0) + 1
                    if flow['callCounter'] >= max_attempts:
                        flow['status'] = 'unresponsive'
                        finished_flows.append(flow)
                        active_flows.remove(flow)
                    flow_updated = True
                    break
            
            if not flow_updated:
                # If the flow wasn't found in activeFlows, add it
                new_flow = {
                    'flow_id': flow_id,
                    'callCounter': 1,
                    'status': 'active'
                }
                active_flows.append(new_flow)
            
            contact_ref.update({
                'activeFlows': active_flows,
                'finishedFlows': finished_flows,
                'lastCallAttempt': datetime.datetime.utcnow().isoformat()
            })
            print(f"Contact {contact_id} updated successfully.")
        else:
            print(f"Contact document {contact_id} does not exist.")
    except Exception as e:
        print(f"Failed to update contact document: {str(e)}")

def save_call_data(call_id, request_json, response_text):
    db.collection('Calls').document(call_id).set({
        "original_request": request_json,
        "response": response_text,
        "call_id": call_id,
        "callTimestamp": datetime.datetime.utcnow()
    })