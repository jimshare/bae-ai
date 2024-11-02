import os
from pathlib import Path
from fastapi import FastAPI, Form, Request
from fastapi.responses import PlainTextResponse
from twilio.rest import Client
from twilio.request_validator import RequestValidator
from anthropic import Anthropic
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(title="CalFresh Navigator")

def load_context() -> str:
    """
    Load context from context.txt file.
    Returns empty string if file doesn't exist.
    """
    try:
        context_path = Path("context.txt")
        if context_path.exists():
            return context_path.read_text().strip()
        else:
            print("Warning: context.txt file not found")
            return ""
    except Exception as e:
        print(f"Error loading context.txt: {str(e)}")
        return ""

def generate_prompt(message: str, context: str) -> str:
    """
    Generate a prompt that includes context and the user's message.
    
    Args:
        message: The user's SMS message
        context: The content from context.txt
        
    Returns:
        Formatted prompt string
    """
    if not context:
        return message
        
    return f"""Please answer the following question using the context provided below. 
Keep your response concise and suitable for SMS (under 320 characters).

Context:
{context}

Question:
{message}

Answer the question specifically referencing relevant information from the context. 
If the question cannot be answered using the context, inform the user that you don't have the information to answer their question."""


# Initialize clients
claude = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
twilio_client = Client(
    os.getenv("TWILIO_ACCOUNT_SID"),
    os.getenv("TWILIO_AUTH_TOKEN")
)

# Initialize Twilio validator
validator = RequestValidator(os.getenv("TWILIO_AUTH_TOKEN"))

async def verify_twilio_request(request: Request) -> bool:
    """Verify that incoming requests are from Twilio"""
    # Get the request URL and values
    url = str(request.url)
    params = dict(request.query_params)
    
    # Get the X-Twilio-Signature header
    signature = request.headers.get("X-Twilio-Signature", "")
    
    # Get form data (body)
    body = await request.form()
    form_data = dict(body)
    
    # Validate the request
    return validator.validate(
        url,
        form_data,
        signature
    )

@app.post("/sms", response_class=PlainTextResponse)
async def handle_sms(
    request: Request,
    From: str = Form(...),
    To: str = Form(...),
    Body: str = Form(...),
):
    """
    Handle incoming SMS messages:
    1. Verify the request is from Twilio
    2. Process the message with Claude
    3. Send the response back via SMS
    """
    # Verify request is from Twilio
    if not await verify_twilio_request(request):
        return PlainTextResponse("Invalid request", status_code=403)
    
    try:
        # Load context from file
        context = load_context()
        
        # Generate prompt with context
        prompt = generate_prompt(Body, context)

        # Get completion from Claude
        message = claude.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1024,
            messages=[{
                "role": "user",
                "content": prompt
            }],
            system="You are an SMS chatbot. Keep responses concise and under 320 characters to fit in two SMS messages."
        )
        
        # Extract response
        response = message.content[0].text
        
        return PlainTextResponse(response)
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return PlainTextResponse(
            "Sorry, there was an error processing your message.",
            status_code=500
        )