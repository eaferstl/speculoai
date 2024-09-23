# HeyIsa Call Processing Application

## Introduction

The HeyIsa Call Processing Application is a sophisticated system designed to handle both incoming and outgoing calls, process call data, perform AI-powered analysis, and send notifications. This application integrates seamlessly with Firebase, OpenAI's GPT models, and the Gmail API to provide a comprehensive solution for call management and analysis in a single, consolidated Python script.

## Features

- Process both inbound and outbound call data
- Determine call status (answered, voicemail, no answer) using AI
- Perform in-depth call analysis using OpenAI's GPT models
- Store call data and analysis results in Firebase Firestore
- Send detailed email notifications for processed calls
- Synchronize data with external systems via webhook
- Handle various call scenarios including human-answered calls, voicemails, and no-answers

## Technologies Used

- Python 3.7+
- Firebase Admin SDK
- OpenAI API (GPT-4 models)
- Google Cloud Functions
- Gmail API
- Flask (for HTTP request handling)

## Setup

### Prerequisites

- Google Cloud account with Firebase project set up
- OpenAI API account and API key
- Gmail API credentials
- Python 3.7 or higher installed

### Environment Variables

The following environment variables need to be set:

- `OPENAI_API`: Your OpenAI API key
- `GOOGLE_APPLICATION_CREDENTIALS_JSON`: JSON content of your Google Cloud service account key (for Firebase and Gmail API)

### Installation

1. Clone the repository:
   ```
   git clone https://github.com/your-org/heyisa-call-processor.git
   cd heyisa-call-processor
   ```

2. Install dependencies:
   ```
   pip install firebase-admin openai flask google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client
   ```

3. Set up your environment variables as described in the Prerequisites section.

## Usage

The application is designed to be deployed as a Google Cloud Function. The main entry point is the `process_call_data` function.

To run the application locally for development:

1. Install the Google Cloud Functions Framework:
   ```
   pip install functions-framework
   ```

2. Run the application:
   ```
   functions-framework --target=process_call_data
   ```

3. The function will be available at `http://localhost:8080`

## API Documentation

### Endpoint: `/process_call_data`

**Method:** POST

**Request Body:**

```json
{
  "call_id": "string",
  "call_length": "number",
  "to": "string",
  "from": "string",
  "language": "string",
  "completed": "boolean",
  "created_at": "string",
  "inbound": "boolean",
  "queue_status": "string",
  "endpoint_url": "string",
  "max_duration": "number",
  "error_message": "string",
  "answered_by": "string",
  "recording_url": "string",
  "concatenated_transcript": "string",
  "status": "string",
  "corrected_duration": "string",
  "end_at": "string",
  "price": "number",
  "summary": "string",
  "metadata": {
    "organization_id": "string"
  }
}
```

**Response:**

```json
{
  "success": "boolean",
  "message": "string"
}
```

## Key Components

1. **Call Status Determination**: Uses OpenAI's GPT-4-mini model to analyze call transcripts and determine if the call was answered, went to voicemail, or wasn't answered.

2. **Call Insights Analysis**: Utilizes OpenAI's GPT-4 model to generate detailed insights from the call transcript, including outcome, answers to predefined questions, and a summary.

3. **Database Operations**: Manages Firestore operations for storing and retrieving call data, contact information, and organization details.

4. **Email Notifications**: Sends detailed HTML and plain text email notifications using the Gmail API when a call is processed.

5. **Data Synchronization**: Implements a mechanism to synchronize processed call data with external systems via a webhook.

## Firebase Firestore Collections

The application uses the following collections in Firestore:

- `Calls`: Stores detailed call data and analysis results
- `Contacts`: Manages contact information
- `Organizations`: Stores organization-specific data including sync links and notification emails
- `Flows`: Contains flow information for call processing
- `Insights`: Stores insights instructions for call analysis

## Error Handling and Logging

The application uses print statements for logging. In a production environment, consider replacing these with a more robust logging solution.

## Security Considerations

- Ensure all API keys and credentials are securely stored and never committed to version control.
- Implement proper authentication and authorization for the Cloud Function.
- Regularly review and update the permissions for the Firebase and Gmail API service accounts.

## Scalability

The application is designed to handle individual call processing. For high-volume scenarios, consider implementing queuing mechanisms and optimizing database operations.

## Contributing

Contributions to the HeyIsa Call Processing Application are welcome. Please follow these steps:

1. Fork the repository
2. Create a new branch for your feature
3. Commit your changes
4. Push to the branch
5. Create a new Pull Request

## License

[Specify your license here]

## Support

For support, please contact [your support email or channel].

## Disclaimer

This application processes sensitive call data. Ensure compliance with all relevant data protection and privacy regulations in your jurisdiction.

gcloud functions deploy call_processor \
  --gen2 \
  --runtime=python312 \
  --region=us-central1 \
  --source=. \
  --trigger-http \
  --allow-unauthenticated \
  --env-vars-file env.yaml