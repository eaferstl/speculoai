# Call Builder Function

## Table of Contents
1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Key Components](#key-components)
4. [Setup and Installation](#setup-and-installation)
5. [Configuration](#configuration)
6. [Deployment](#deployment)
7. [Usage](#usage)
8. [Flow Types](#flow-types)
9. [Payload Generation](#payload-generation)
10. [Database Operations](#database-operations)
11. [API Integration](#api-integration)
12. [Error Handling and Logging](#error-handling-and-logging)
13. [Security Considerations](#security-considerations)
14. [Testing](#testing)
15. [Contributing](#contributing)
16. [License](#license)

## Overview

The Call Builder function is a sophisticated Cloud Function designed to generate and send call payloads to Bland AI for automated phone calls. It's an integral part of a larger customer interaction management system, supporting various workflow types and handling both standard calls and voicemails.

## Architecture

The function follows a modular architecture:

1. Request Processing (`main.py`)
2. Data Retrieval (`database_ops.py`)
3. Payload Crafting (`prompt_crafting.py`, `payload_factory.py`)
4. API Communication (`api_client.py`)
5. Configuration Management (`config.py`)
6. Utility Functions (`html_processing.py`, `time_utils.py`)

## Key Components

- `main.py`: Entry point for the Cloud Function. Handles HTTP requests, orchestrates the overall process.
- `prompt_crafting.py`: Core logic for creating call payloads based on flow type and other parameters.
- `payload_factory.py`: Generates specific payload structures for different call types (standard, pathway, voicemail).
- `database_ops.py`: Manages Firestore database operations, including querying and updating documents.
- `api_client.py`: Handles communication with the Bland AI API, including request formatting and error handling.
- `config.py`: Manages configuration settings, loading from both environment variables and Google Cloud Storage.
- `secret_manager.py`: Accesses secrets from Google Cloud Secret Manager, ensuring secure handling of sensitive data.
- `html_processing.py`: Processes HTML content in prompts, ensuring clean text output.
- `time_utils.py`: Provides time-related utilities, particularly for determining the appropriate greeting based on time of day.

## Setup and Installation

1. Ensure you have the Google Cloud SDK installed and configured.
2. Set up a Google Cloud project with the following services enabled:
   - Cloud Functions
   - Firestore
   - Secret Manager
   - Cloud Storage
   - Error Reporting
3. Clone the repository:
   ```
   git clone [repository-url]
   cd call-builder-function
   ```
4. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

## Configuration

1. Environment variables:
   - Create an `env.yaml` file with the following content:
     ```yaml
     ENVIRONMENT: production
     PROJECT_ID: [your-project-id]
     CONFIG_BUCKET: [your-config-bucket]
     BLAND_AI_URL: https://isa.bland.ai/v1/calls
     ```

2. Google Cloud Storage Configuration:
   - Create a bucket named as per `CONFIG_BUCKET` in your `env.yaml`.
   - Upload the following configuration files to this bucket:
     - `config_production.json`
     - `payload_defaults.json`
     - `pronunciation_guide.json`

3. Secret Manager:
   - Create a secret named `bland-api-key` in Secret Manager and store your Bland AI API key.

## Deployment

Deploy the function using the Google Cloud CLI:

```bash
gcloud functions deploy call_builder \
  --gen2 \
  --runtime=python312 \
  --region=us-central1 \
  --source=. \
  --trigger-http \
  --allow-unauthenticated \
  --env-vars-file env.yaml
```

## Usage

Send a POST request to the function's URL with a JSON payload:

```json
{
  "flow_id": "flow123",
  "contact_id": "contact456",
  "organization_id": "org789",
  "test": false
}
```

- `flow_id`: ID of the flow to execute
- `contact_id`: ID of the contact to call
- `organization_id`: ID of the organization
- `test` (optional): Set to `true` for test calls

## Flow Types

The function supports three main flow types:

1. **Convert**: Aimed at converting leads. First attempt is a voicemail if no previous calls.
2. **Engage**: For engaging with existing customers or warm leads.
3. **Revive**: For re-engaging with inactive customers or cold leads.

## Payload Generation

Payloads are generated based on the flow type and other parameters:

1. Standard Payload: Used for most calls.
2. Pathway Payload: Used when a specific conversation pathway is defined.
3. Voicemail Payload: Used for leaving voicemails, typically on the first attempt of a Convert flow.

## Database Operations

The function interacts with Firestore to:

1. Retrieve flow, organization, and contact information.
2. Fetch knowledge base data and rules.
3. Update contact flow status after call attempts.
4. Save call data for future reference.

## API Integration

The function communicates with the Bland AI API to initiate calls:

1. Formats the payload according to Bland AI specifications.
2. Sends POST requests to the Bland AI endpoint.
3. Handles API responses and errors.

## Error Handling and Logging

- Comprehensive error handling throughout the codebase.
- Errors are logged using Google Cloud Error Reporting.
- Debug logs are available in Cloud Functions logs.

## Security Considerations

1. API keys and secrets are stored in Google Cloud Secret Manager.
2. HTTPS is used for all external communications.
3. Proper IAM roles should be assigned to the Cloud Function's service account.

## Testing

1. Unit Tests: Write unit tests for individual components (TODO).
2. Integration Tests: Test the entire function flow with mock data (TODO).
3. Use the `test` flag in the request payload for dry runs.

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is proprietary and confidential. Unauthorized copying of this file, via any medium, is strictly prohibited.# ISA-AI
# ISA-AI
