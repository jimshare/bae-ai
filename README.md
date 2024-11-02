# CalFresh Navigator with FastAPI, Twilio, and Anthropic

This project implements an SMS chatbot using FastAPI that:
1. Receives incoming SMS messages via Twilio webhooks
2. Processes messages using Anthropic's Claude API, referencing rules and regulations on accessing CalFresh in California
3. Sends responses back via SMS

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Copy `.env.example` to `.env` and fill in your API keys:
- ANTHROPIC_API_KEY: Your Anthropic API key
- TWILIO_ACCOUNT_SID: Your Twilio Account SID
- TWILIO_AUTH_TOKEN: Your Twilio Auth Token

3. If you plan to use ngrok for local development, set permissions for `start-dev.sh` and run it:
```bash
chmod +x start-dev.sh
./start-dev.sh
```

4. Otherwise, you run the server directly:
```bash
uvicorn main:app --reload
```

5. Configure your Twilio webhook:
- Go to your Twilio phone number settings
- Set the webhook URL for incoming messages to: `https://your-domain.com/sms`
- Make sure webhook method is set to POST

## Security
The application validates incoming webhooks using Twilio's request validation to ensure requests are legitimate.

## Environment Variables
- ANTHROPIC_API_KEY: API key for Anthropic
- TWILIO_ACCOUNT_SID: Your Twilio account SID
- TWILIO_AUTH_TOKEN: Your Twilio auth token

## Error Handling
The application includes basic error handling for:
- Invalid webhooks (403 response)
- Processing errors (500 response with user-friendly message)