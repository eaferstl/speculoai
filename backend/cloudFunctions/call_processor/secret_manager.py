from google.cloud import secretmanager
from google.api_core import exceptions
import logging
from typing import Optional, Dict
from functools import lru_cache

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Initialize the Secret Manager client
client = secretmanager.SecretManagerServiceClient()

@lru_cache(maxsize=None)
def access_secret_version(project_id: str, secret_id: str, version_id: str = "latest") -> Optional[str]:
    """
    Access the secret version from Google Cloud Secret Manager.
    
    Args:
        project_id (str): The Google Cloud project ID.
        secret_id (str): The ID of the secret to access.
        version_id (str): The version of the secret to access. Defaults to "latest".
    
    Returns:
        Optional[str]: The secret payload as a string, or None if an error occurred.
    """
    if not project_id:
        logging.error("Project ID is not set")
        return None
    
    name = f"projects/{project_id}/secrets/{secret_id}/versions/{version_id}"
    
    try:
        response = client.access_secret_version(request={"name": name})
        return response.payload.data.decode("UTF-8")
    except exceptions.NotFound:
        logging.error(f"Secret {secret_id} not found")
    except exceptions.PermissionDenied:
        logging.error(f"Permission denied for secret {secret_id}")
    except Exception as e:
        logging.error(f"Error accessing secret {secret_id}: {str(e)}")
    
    return None

def get_all_secrets(project_id: str, secret_ids: list) -> Dict[str, str]:
    """
    Retrieve multiple secrets at once.
    
    Args:
        project_id (str): The Google Cloud project ID.
        secret_ids (list): A list of secret IDs to retrieve.
    
    Returns:
        Dict[str, str]: A dictionary of secret_id: secret_value pairs.
    """
    secrets = {}
    for secret_id in secret_ids:
        secret_value = access_secret_version(project_id, secret_id)
        if secret_value is not None:
            secrets[secret_id] = secret_value
        else:
            logging.warning(f"Failed to retrieve secret: {secret_id}")
    return secrets