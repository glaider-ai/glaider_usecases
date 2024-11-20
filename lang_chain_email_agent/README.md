# LLM Phishing Email Detector

A Python application that uses Glaider and OpenAI to detect phishing attempts in emails while protecting against prompt injection attacks.

## Features

- Phishing email detection using OpenAI's GPT-3.5
- Prompt injection protection using Glaider
- Simple API for email analysis

## Installation

1. Clone the repository
2. Install dependencies:

```bash


pip install -r requirements.txt


```

3. Create a `.env` file with your API keys:

```


GLAIDER_API_KEY=your_glaider_key


OPENAI_API_KEY=your_openai_key


```

## Usage

The application takes an email content and analyzes it for potential phishing attempts:

```python


from main import analyze_email_phishing





email_content = "Your email content here..."


result = analyze_email_phishing(content=email_content)


print(f"Phishing Analysis Result: {result}")


```

## Dependencies

- glaider==0.2.0
- pymailtm==1.1.1

## Security Features

- Prompt injection detection using Glaider's API
- Safe handling of potentially malicious email content
- API key protection through environment variables
