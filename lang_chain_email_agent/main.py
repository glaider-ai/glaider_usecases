import os
import time
import logging
import threading
from typing import Any
from flask import Flask, request, jsonify

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

import base64
import email
from email.mime.text import MIMEText

# LangChain imports
from langchain.llms import OpenAI
from langchain.agents import initialize_agent, AgentType
from langchain.tools import BaseTool

# OpenAI imports
import openai
from openai import OpenAIError

# Other necessary imports
from langchain.memory import ConversationBufferMemory
import requests

# Set up the scopes for Gmail API
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.modify",
]

# Load or obtain Gmail API credentials
def get_credentials():
    creds = None
    if os.path.exists("email_token.json"):
        creds = Credentials.from_authorized_user_file("email_token.json", SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                print(f"Error refreshing credentials: {e}")
                creds = None
        if not creds:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        with open("email_token.json", "w") as token:
            token.write(creds.to_json())
    return creds

creds = get_credentials()

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class SummarizeEmailTool(BaseTool):
    name = "summarize_email"
    description = "Use this tool to summarize an email."

    def _run(self, email_content: str) -> str:
        try:
            # Summarize the email content using the LLM
            summary = llm(email_content)
            return summary
        except OpenAIError as e:
            return f"An error occurred while summarizing the email: {e}"

    async def _arun(self, email_content: str) -> str:
        raise NotImplementedError("This tool does not support async")

class SendEmailTool(BaseTool):
    name = "send_email"
    description = "Use this tool to send an email. Input should be in the format: 'recipient email address; subject; email body'"

    def _run(self, query: str) -> str:
        try:
            recipient, subject, body = query.strip().split(";", 2)
            service = build("gmail", "v1", credentials=creds)
            message = MIMEText(body.strip())
            message["to"] = recipient.strip()
            message["subject"] = subject.strip()
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
            send_message = service.users().messages().send(
                userId="me",
                body={"raw": raw_message}
            ).execute()
            return f"Email sent to {recipient}"
        except Exception as e:
            return f"An error occurred while sending email: {e}"

    async def _arun(self, query: str) -> str:
        raise NotImplementedError("This tool does not support async")

def process_new_email(message_id):
    try:
        logger.info(f"Processing email with ID: {message_id}")

        # Fetch the email content
        email_content = get_email_content(message_id)
        logger.debug(f"Email content for ID {message_id}:\n{email_content}")

        # Check for prompt injection
        is_injection = check_prompt_injection(email_content)
        if is_injection:
            logger.warning(f"Prompt injection detected in email ID {message_id}. Skipping processing.")
            return

        # Prepare agent input
        input_text = f"Summarize the following email:\n\n{email_content}"
        logger.debug(f"Agent input: {input_text}")

        # Run the agent
        response = agent.run(input_text)
        logger.info(f"Agent response: {response}")

    except Exception as e:
        logger.error(f"An error occurred while processing email ID {message_id}: {e}", exc_info=True)

# Initialize Flask app for webhook
app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def gmail_webhook():
    logger.info("Received a webhook request")
    data = request.get_json()
    logger.info(f"Webhook data: {data}")
    if data.get('message', {}).get('data'):
        message_data = base64.b64decode(data['message']['data']).decode('utf-8')
        logger.info(f"Decoded message data: {message_data}")
        if 'emailAddress' in message_data:
            logger.info("New email detected, starting processing")
            threading.Thread(target=process_new_email, args=(data['message']['messageId'],)).start()
    return jsonify(success=True), 200

# Initialize the language model
llm = OpenAI(
    temperature=0,
    openai_api_key="sk-",
    model_name='gpt-3.5-turbo'  # Or another model if preferred
)

# Initialize the tools
tools = [
    SummarizeEmailTool(),
    SendEmailTool(),
]

# Initialize memory
memory = ConversationBufferMemory(memory_key="chat_history")

# Initialize the agent
agent = initialize_agent(
    tools,
    llm,
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,  # Or another agent type if preferred
    memory=memory,
    verbose=True
)

def start_flask_app():
    try:
        app.run(debug=False, port=5001)
    except Exception as e:
        logger.error(f"Failed to start Flask app: {e}")

def poll_for_new_emails():
    logger.info("Starting to poll for new emails")
    try:
        service = build("gmail", "v1", credentials=creds)

        # Get the list of unread messages at startup
        initial_unread_messages = set()
        results = service.users().messages().list(
            userId="me", labelIds=['INBOX'], q="is:unread"
        ).execute()
        messages = results.get("messages", [])
        for message in messages:
            initial_unread_messages.add(message['id'])
        logger.info(f"Initial unread messages: {initial_unread_messages}")

        processed_messages = set()

        while True:
            logger.info("Checking for new emails")
            results = service.users().messages().list(
                userId="me", labelIds=['INBOX'], q="is:unread"
            ).execute()
            messages = results.get("messages", [])
            for message in messages:
                msg_id = message['id']
                if (msg_id in initial_unread_messages) or (msg_id in processed_messages):
                    logger.info(f"Skipping email with ID {msg_id} as it was unread at startup or already processed.")
                else:
                    process_new_email(msg_id)
                    processed_messages.add(msg_id)
                    # Mark the email as read after processing
                    service.users().messages().modify(
                        userId="me", id=msg_id,
                        body={'removeLabelIds': ['UNREAD']}
                    ).execute()
            time.sleep(60)  # Poll every 60 seconds
    except Exception as e:
        logger.error(f"Error in email polling: {e}")

def check_prompt_injection(prompt: str) -> bool:
    """Check if the given prompt contains a prompt injection."""
    url = "https://api.glaider.it/v1/detect-prompt-injection"

    headers = {
        "Authorization": f"Bearer ",
        "Content-Type": "application/json"
    }

    data = {
        "prompt": prompt,
        "zero_latency": False,  # Synchronous processing
        "strictness": False,        # Adjust as needed: 1, 2, or 3
        "save_message": True,
        "notifications": False
    }

    try:
        response = requests.post(url, json=data, headers=headers)
        response.raise_for_status()
        result = response.json()

        is_injection = result.get("result", {}).get("is_prompt_injection", False)
        return is_injection

    except requests.exceptions.RequestException as e:
        logger.error(f"Error contacting Glaider API: {e}", exc_info=True)
        # Decide how to handle API errors. For safety, return True to err on the side of caution.
        return True

def get_email_content(message_id) -> str:
    """Fetches the email content from Gmail given a message ID."""
    service = build("gmail", "v1", credentials=creds)
    message = service.users().messages().get(userId="me", id=message_id, format='raw').execute()
    msg_str = base64.urlsafe_b64decode(message['raw'].encode('ASCII'))
    email_message = email.message_from_bytes(msg_str)
    email_content = ""

    if email_message.is_multipart():
        for part in email_message.walk():
            content_type = part.get_content_type()
            if content_type == 'text/plain':
                email_content += part.get_payload(decode=True).decode()
    else:
        email_content = email_message.get_payload(decode=True).decode()

    return email_content

if __name__ == "__main__":
    logger.info("Starting the email summarization agent")

    # Start the Flask app (if you need it for webhooks)
    threading.Thread(target=start_flask_app).start()

    # Start the email polling
    threading.Thread(target=poll_for_new_emails, daemon=True).start()

    logger.info("Email summarization agent is running. Waiting for new emails...")

    # Keep the main thread running
    while True:
        time.sleep(1)
        

