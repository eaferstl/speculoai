from openai import OpenAI
import firebase_admin
from firebase_admin import credentials, firestore
from flask import abort, jsonify
import os
import functions_framework
import re
import json

# Initialize Firebase Admin SDK outside of your function
if not firebase_admin._apps:
    cred = credentials.ApplicationDefault()
    firebase_admin.initialize_app(cred)

# Firestore client
db = firestore.client()

# Initialize the OpenAI client with your API key
openai_client = OpenAI(api_key=os.getenv("OPENAI_API"))

def grab_coaching_insights(organization_id):
    """
    Retrieves insights documents of type 'coaching' for the specified organization from the 'Insights' collection.

    Parameters:
    - organization_id: The ID of the organization to retrieve insights for.

    Returns:
    A list of insights documents of type 'coaching' if found, an empty list otherwise.
    """
    try:
        # Fetch all insights for the given organization
        insights_query = db.collection('Insights').where('organization_id', '==', organization_id).stream()
        
        coaching_insights = []
        for insight_doc in insights_query:
            insight_data = insight_doc.to_dict()
            # Check if the insight type is 'coaching'
            if insight_data.get('type') == 'coaching':
                coaching_insights.append(insight_data)
                print("Found coaching insight:", insight_data)
        
        if coaching_insights:
            print("Successfully fetched coaching insights.")
            return coaching_insights
        else:
            print("No coaching insights found for the given organization.")
            return []
    except Exception as e:
        print(f"Error fetching coaching insights: {e}")
        return []


def call_insights(client, system_prompt, transcript):
    """
    Performs detailed analysis of a call transcript using OpenAI, expecting a JSON-structured output with specific requirements.
    """

    # Prepare the JSON example with placeholders for outcomes and questions
    json_example = {
        "answers": {
            "Example Question Title": "Example Answer"
        },
        "summary": "Example summary of anything else we should know about the call. Plus all the details given by the agent in a structured form"
    }
    
    # Convert the example JSON structure to a string for inclusion in the prompt
    json_example_str = json.dumps(json_example, indent=2)
    
    # Extract parts from the system prompt
    conversation_context = system_prompt.get("script_context", "")
    questions_to_answer = system_prompt.get("questions_to_answer", {})
    
    # Constructing the crafted_system_prompt
    crafted_system_prompt = f"Context: {conversation_context}. The contact's dialogue always begins with 'user:' the Assistant's dialogue always begins with 'assistant:' \n\n"
    crafted_system_prompt += "Instructions:\n"
    crafted_system_prompt += "Based on the transcript, answer the questions provided. "
    crafted_system_prompt += "Summarize the call, following the JSON structure shown in the example below.\n\n"
    crafted_system_prompt += f"Example JSON structure:\n{json_example_str}\n\n"
    
    crafted_system_prompt += "\nQuestions to answer:\n"
    for title, question in questions_to_answer.items():
        crafted_system_prompt += f"- {title}: {question}\n"
    
    crafted_system_prompt += "\nPlease structure the response as a JSON object with answers to the questions, and a summary of the call with all the details surrounding the metrics. "
    crafted_system_prompt += "Include all questions even if the answer is none or n/a."
    crafted_system_prompt += "The response should strictly follow the example's structure and include nothing beyond it."
    
    try:
        print("Sending request to OpenAI for call analysis...")
        response = client.chat.completions.create(
            model="gpt-3.5-turbo-0125",
            messages=[
                {"role": "system", "content": crafted_system_prompt},
                {"role": "user", "content": transcript}
            ]
        )
        print("Response received from OpenAI successfully.")
        
        # OpenAI's response as text
        analysis_response = response.choices[0].message.content.strip()
        print(f"Analysis response: {analysis_response}")
        
        # Here, implement parsing of the structured text response into a JSON object
        # This example does not include specific parsing logic but assumes successful structure adherence
        
        return {"insights": analysis_response}
    except Exception as e:
        print(f"Error during call analysis: {e}")
        return {"error": str(e)}

@functions_framework.http
def process_call_data(request):
    print("Processing call data...")
    
    request_data = request.get_json(silent=True)
    print("the request data: {request_data}")
    if not request_data:
        print("Bad Request: No JSON payload provided.")
        return abort(400, "Bad Request: No JSON payload provided.")

    # Extracting data from the request_data dictionary
    call_id = request_data.get("call_id", "")
    callTimestamp = request_data["variables"].get("now_utc", "")
    call_length = request_data.get("call_length", 0)
    to_number = request_data.get("to", "")
    from_number = request_data.get("from", "")
    language = request_data["request_data"].get("language", "")
    completed = request_data.get("completed", False)
    created_at = request_data.get("created_at", "")
    inbound = request_data.get("inbound", True)
    queue_status = request_data.get("queue_status", "")
    endpoint_url = request_data.get("endpoint_url", "")
    max_duration = request_data.get("max_duration", 0)
    error_message = request_data.get("error_message", "")
    recording_url = request_data.get("recording_url", "")
    concatenated_transcript = request_data.get("concatenated_transcript", "")
    status = request_data.get("status", "")
    corrected_duration = request_data.get("corrected_duration", "")
    end_at = request_data.get("end_at", "")
    call_cost = request_data.get("price", 0)

   
    organization_id = request_data['variables'].get("agent_org", "")
    team_member_id = request_data['variables'].get("agent_id", "")

    ###GRAB INSIGHTS FOR TEAM COACHING

    insights_instructions = grab_coaching_insights(organization_id)
    print(f"Insight Doc: {insights_instructions}")
    if insights_instructions is None:
        return jsonify({"success": False, "message": "Failed to fetch system prompt."})

    # Perform call analysis
    insights_response = call_insights(openai_client, insights_instructions[0], concatenated_transcript)
    print(f"Call notes: {insights_response}")

    try:
        insights_data = json.loads(insights_response.get("insights", "{}"))
        print("Successfully parsed analysis response into a dictionary.")
    except json.JSONDecodeError as e:
        print(f"Error parsing analysis response into a dictionary: {e}")
        return jsonify({"success": False, "message": "Failed to parse analysis response."})

    # Store the analysis result in the callsAnswered collection
    try:
        doc_ref = db.collection('Calls').document(call_id)
        doc_ref.set({
            "call_length": call_length,
            "callTimestamp": callTimestamp,
            "to_number": to_number,
            "from_number": from_number,
            "call_type": "coaching",
            "language": language,
            "completed": completed,
            "created_at": created_at,
            "inbound": inbound,
            "original_request":{
                "organization_id": organization_id,
                "team_member_id": team_member_id
            },
            "queue_status": queue_status,
            "endpoint_url": endpoint_url,
            "max_duration": max_duration,
            "error_message": error_message,
            "answered_by": 'human',
            "recording_url": recording_url,
            "concatenated_transcript": concatenated_transcript,
            "status": status,
            "corrected_duration": corrected_duration,
            "end_at": end_at,
            "call_cost": call_cost,
            "call_analysis": insights_data,  # Assuming call_notes is a structured string or a dictionary
            "processed_at": firestore.SERVER_TIMESTAMP  # This adds a timestamp of when the document was created/updated
        })
        print("Successfully stored call analysis in Calls collection.")

        return jsonify({"success": True, "message": "Call data processed and stored successfully."})
    except Exception as e:
        print(f"Error storing call analysis: {e}")
        return jsonify({"success": False, "message": "Failed to store call analysis."})
