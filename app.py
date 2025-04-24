from flask import Flask, render_template, request
import anthropic  # Replace Google Generative AI with Anthropic
import os, tempfile
from dotenv import load_dotenv
import json
from werkzeug.utils import secure_filename
from process_history_file import protobuf_to_json


app = Flask(__name__)
load_dotenv()  # Load environment variables from .env

# Configure the Anthropic API
try:
    ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    model = "claude-3-haiku-20240307"  # Using Claude 3 Haiku as a default model (fast and cost-effective)
except KeyError:
    print("Error: ANTHROPIC_API_KEY is not set in the .env file. The application may not function correctly.")
    client = None  # Set client to None to prevent errors later.

# Define allowed file types
ALLOWED_EXTENSIONS = {'json','proto'}

def allowed_file(filename):
    """Checks if the file extension is allowed."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def generate_claude_response(data):
    """
    Generates a response from the Anthropic Claude API based on the provided JSON data.

    Args:
        data (str): The data submitted by the user.

    Returns:
        str: The response from the Anthropic API, or an error message.
    """
    if client is None:
        return "Error: Anthropic API key is not configured."

    prompt = f"""
        You are an expert Temporal user. You can analyze workflow history exports in a JSON format and provide guidance to help the user diagnose issues they are having.
        Here is the information you need to interpret the workflow history.

        Always report the status of the workflow. The status is obtained by looking at the last event. A terminated status has an eventType of "WorkflowExecutionTerminated". Failed status has an eventType of "WorkflowExecutionFailed". Completed status has an eventType of "WorkflowExecutionCompleted". If you encounter any other status strip off the "WorkflowExecution" part of the eventType and report that. If the last eventType does not start with "WorkflowExecution" then the status is running.
        If the status is failed, explain why it failed by displaying the failure and the cause.
        This information can be found in the last event, looking at the failure message and cause message.
        When you encounter an eventType of "WorkflowTaskFailed", display the failure message.
        For events that are WORKFLOW_TASK_FAILED_CAUSE_NON_DETERMINISTIC_ERROR,
        provide guidance that they have two options:
        Either revert the workflow code back to the previous state, or
        Terminate the existing workflow execution, and Reset the workflow.

        Events that are failing due to a potential deadlock detected, explain that code in workflows must not take a long time. Provide guidance that they can either optimize their code to reduce the time the code takes to run in the context of a workflow, or move the longer running code into an activity.
        Also look at the number of attempts and report if you find an event that occurred more than 3 times.

        Output Desired
        Report the Workflow Status. Regardless of the status, please also report any other anomalies in the workflow history and provide guidance as stated above.

        Here is the Workflow Export in JSON Format:
        {data}
        """
    try:
        # Create a message using Anthropic's API
        message = client.messages.create(
            model=model,
            max_tokens=4096,
            temperature=0,  # Low temperature for more deterministic responses
            system="You are an expert Temporal workflow analyzer that provides concise, accurate analysis.",
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        # Return the content from the assistant's response
        return message.content[0].text
    except Exception as e:
        return f"Error generating response: {e}"

@app.route('/', methods=['GET', 'POST'])
def index():
    """
    Handles the main page of the application.

    GET: Renders the initial page with the text area.
    POST: Processes the submitted JSON data.
          If the data is not empty, calls the Anthropic API and returns the response.
          If the data is empty, returns an error message.
    """
    if request.method == 'POST':
        json_data = request.form['json_data']
        uploaded_file = request.files['file']
        claude_response = ""

        if json_data:
            claude_response = generate_claude_response(json_data)
            return render_template('index.html', gemini_response=claude_response, previous_json_data=json_data, show_inputs=False)
        elif uploaded_file and allowed_file(uploaded_file.filename):
            filename = secure_filename(uploaded_file.filename)
            # Create a temporary file. The file is automatically deleted
            # when the block exits
            with tempfile.NamedTemporaryFile(delete=True) as temp_file:
                uploaded_file.save(temp_file.name)
                temp_file.seek(0)
                if filename.endswith('.json'):
                    file_contents = temp_file.read().decode('utf-8')
                else:
                    print(f"reading protobuf contents {temp_file.name}")
                    file_contents = protobuf_to_json(temp_file.name)

            claude_response = generate_claude_response(file_contents)
            return render_template('index.html', gemini_response=claude_response, show_inputs=False)
        else:
            error_message = "Please paste JSON content into the text area or upload a .json or .proto file."
            print(f"An error occurred: {error_message}")
            return render_template('index.html', error_message=error_message, show_inputs=True)
    return render_template('index.html', show_inputs=True)

if __name__ == '__main__':
    app.run(debug=True)