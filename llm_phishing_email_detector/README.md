# LangChain Email Agent

An intelligent email processing system built with LangChain and Gmail API that can summarize emails and detect potential security threats.

## Features

- Gmail API integration for email monitoring
- Email summarization using LangChain and OpenAI
- Prompt injection protection
- Webhook support for real-time notifications
- Multi-threaded email processing
- Automatic handling of unread messages

## Installation

1. Clone the repository
2. Install dependencies:

```bash


pip install -r requirements.txt


```

3. Set up Google OAuth credentials:

**   **- Create a project in Google Cloud Console

**   **- Enable Gmail API

**   **- Download credentials.json

**   **- Place credentials.json in the project root

4. Configure environment variables:

```


OPENAI_API_KEY=your_openai_key


GLAIDER_API_KEY=your_glaider_key


```

## Components

### Email Processing

- Automatic polling for new emails
- Unread message detection
- Multi-threaded processing

### Security

- Prompt injection detection
- Email content sanitization
- Secure credential handling

### API Integration

- Gmail API for email operations
- OpenAI for summarization
- Glaider for security checks

## Usage

Run the application:

```bash


python main.py


```

The agent will:

1. Start monitoring your Gmail inbox
2. Process new unread emails
3. Generate summaries
4. Check for security threats
5. Mark processed emails as read

## Dependencies

- Google API client libraries
- LangChain
- OpenAI
- Flask for webhooks
- Additional utilities (see requirements.txt)
