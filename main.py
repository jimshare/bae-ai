import os
from pathlib import Path
from fastapi import FastAPI, Form, Request, BackgroundTasks
from fastapi.responses import PlainTextResponse
from twilio.rest import Client
from twilio.request_validator import RequestValidator
from anthropic import Anthropic
from dotenv import load_dotenv
import asyncio
import time

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

def generate_prompt(message: str) -> str:
    """
    Generate a prompt that includes context and the user's message.
    
    Args:
        message: The user's SMS message
        context: The content from context.txt
        
    Returns:
        Formatted prompt string
    """
    return f"""Please answer the following question using the context provided below.
The question may or may not be in English. If the question is not in English, write your response in the language of the question.

Question:
{message}

Answer the question specifically referencing relevant information from the context, which is rules and information on the CalFresh program. 
It's very important that you keep your response concise and suitable for SMS with no more than 100 words.
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

async def process_message_and_respond(from_number: str, to_number: str, message_body: str):
    """
    Process message with Anthropic and send response via Twilio
    """
    try:
        # Get context and generate prompt
        context = load_context()
        prompt = generate_prompt(message_body)
        
        # Get completion from Claude with timeout
        start_time = time.time()
        message = claude.beta.prompt_caching.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1024,
            messages=[{
                "role": "user",
                "content": prompt
            }],
            system=[
                {
                    "type": "text",
                    "text": "You are an SMS chatbot. It is very important that you keep responses concise and under 640 characters to fit in SMS messages."
                },
                {
                    "type": "text",
                    "text": context,
                    "cache_control": {"type": "ephemeral"}
                }
            ]
        )
        
        # Extract response
        response = message.content[0].text
        
        # Log processing time
        processing_time = time.time() - start_time
        print(f"Claude processing time: {processing_time:.2f} seconds")
        
        # Send SMS response via Twilio
        twilio_client.messages.create(
            body=response,
            from_=to_number,
            to=from_number
        )
        
    except Exception as e:
        print(f"Error in background task: {str(e)}")
        # Send error message to user
        try:
            error_message = "Sorry, I'm having trouble processing your message. Please try again in a moment."
            twilio_client.messages.create(
                body=error_message,
                from_=to_number,
                to=from_number
            )
        except Exception as send_error:
            print(f"Error sending error message: {str(send_error)}")


@app.post("/sms", response_class=PlainTextResponse)
async def handle_sms(
    background_tasks: BackgroundTasks,
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
    
    # Queue the message processing in background
    background_tasks.add_task(
        process_message_and_respond,
        from_number=From,
        to_number=To,
        message_body=Body
    )
    
    # Return immediate acknowledgment
    # Using empty response to avoid Twilio sending any immediate message
    return PlainTextResponse("")

