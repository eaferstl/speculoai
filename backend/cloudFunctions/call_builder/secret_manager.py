from google.cloud import secretmanager
import logging

def access_secret_version(project_id, secret_id, version_id="latest"):
    if not project_id:
        logging.error("Project ID is not set")
        return None
    
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{project_id}/secrets/{secret_id}/versions/{version_id}"
    
    try:
        response = client.access_secret_version(request={"name": name})
        return response.payload.data.decode("UTF-8")
    except Exception as e:
        logging.error(f"Error accessing secret {secret_id}: {str(e)}")
        return None