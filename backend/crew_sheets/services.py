import os
import json
import base64
import logging
from datetime import datetime
from .models import CrewSheet
from openai import OpenAI
import httpx

logger = logging.getLogger(__name__)

# Configure OpenAI client once at module level
try:
    # Create custom httpx client with explicit settings to avoid proxy issues
    http_client = httpx.Client(
        proxies=None,  # Explicitly disable proxies
        timeout=60.0   # Set a reasonable timeout
    )

    # Create OpenAI client with custom http_client
    openai_client = OpenAI(
        api_key=os.environ.get('OPENAI_API_KEY'),
        http_client=http_client
    )
    logger.info("OpenAI client initialized successfully with custom HTTP client")
except Exception as e:
    logger.warning(
        f"Custom HTTP client initialization failed: {e}. Trying minimal client...")
    try:
        # Fallback to minimal client
        openai_client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))
        logger.info("OpenAI client initialized with minimal configuration")
    except Exception as e:
        logger.error(f"Failed to initialize OpenAI client: {e}")
        openai_client = None


class OpenAIService:
    """Service for interacting with OpenAI's GPT-4 Vision API."""

    @staticmethod
    def extract_crew_sheet_data(image_path):
        """
        Extract data from a crew sheet image using OpenAI's GPT-4 Vision API.

        Args:
            image_path: Path to the image file

        Returns:
            dict: Extracted data in JSON format or error information
        """
        # Verify API key is set
        api_key = os.environ.get('OPENAI_API_KEY')
        if not api_key:
            logger.error("OPENAI_API_KEY environment variable not set")
            return {
                "valid": True,
                "error": "OpenAI API key is not configured",
                "data": {}
            }

        if api_key in ['your-openai-api-key', 'sk-...', 'your_api_key_here']:
            logger.error("OPENAI_API_KEY contains a placeholder value")
            return {
                "valid": True,
                "error": "OpenAI API key contains a placeholder value",
                "data": {}
            }

        # Verify client is initialized
        if openai_client is None:
            logger.error("OpenAI client failed to initialize")
            return {
                "valid": True,
                "error": "OpenAI client could not be initialized",
                "data": {}
            }

        try:
            # Read and encode the image to base64
            with open(image_path, "rb") as image_file:
                image_data = base64.b64encode(
                    image_file.read()).decode('utf-8')

            # Create the message structure for GPT-4 Vision
            messages = [
                {
                    "role": "system",
                    "content": "You are an expert at extracting data from crew sheets and timesheets. Extract all relevant information into a structured JSON format."
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": """
                            Please extract all information from this crew sheet or timesheet image into structured data.
                            Follow these steps:
                            1. First determine if this is a valid crew sheet or timesheet. If not, respond with {"valid": false, "reason": "explanation"}.
                            2. If valid, extract the following:
                               - Date of the sheet
                               - Any header information or metadata (location, project, etc.)
                               - Table headers (column names)
                               - For each employee row:
                                 - Employee name
                                 - Hours worked (if available)
                                 - Tasks performed (if available)
                                 - Any other data in the row
                            3. Return the extracted data in a clean, structured JSON format with appropriate nesting.
                            """
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_data}"
                            }
                        }
                    ]
                }
            ]

            # Make the API call using the module-level client
            logger.info("Making API call to OpenAI using GPT-4o")
            response = openai_client.chat.completions.create(
                model="gpt-4o",  # Using GPT-4o which now supports vision capabilities
                messages=messages,
                max_tokens=4096,
                # Request JSON formatted response
                response_format={"type": "json_object"},
            )

            # Extract and parse the response
            result = response.choices[0].message.content
            logger.info(f"Received response from OpenAI: {result[:100]}...")

            try:
                # Parse the JSON response
                parsed_data = json.loads(result)
                logger.info("Successfully parsed JSON response")
                return parsed_data
            except json.JSONDecodeError as json_err:
                # Log the full error and response for debugging
                logger.error(f"JSON parsing error: {json_err}")
                logger.error(f"Failed JSON content: {result}")

                # Try to fix common JSON issues (missing brackets, extra text, etc.)
                try:
                    # Look for JSON-like structure within the text
                    import re
                    json_match = re.search(r'(\{.*\})', result, re.DOTALL)
                    if json_match:
                        json_str = json_match.group(1)
                        return json.loads(json_str)
                    else:
                        raise ValueError("No JSON structure found in response")
                except Exception as e:
                    logger.exception("Failed to repair malformed JSON")
                    return {
                        "valid": True,
                        "error": f"Failed to parse OpenAI response as JSON: {str(json_err)}",
                        "data": {},
                        # Include partial response for debugging
                        "raw_response": result[:500]
                    }
        except Exception as e:
            error_msg = f"Failed to process image: {str(e)}"
            logger.exception(error_msg)
            return {
                "valid": True,
                "error": error_msg,
                "data": {}
            }


class CrewSheetProcessor:
    """Service for processing crew sheets."""

    @staticmethod
    def process_crew_sheet(crew_sheet_id):
        """
        Process a crew sheet image and extract its data.

        Args:
            crew_sheet_id: ID of the CrewSheet to process

        Returns:
            bool: True if processing was successful, False otherwise
        """
        try:
            # Get the crew sheet
            crew_sheet = CrewSheet.objects.get(id=crew_sheet_id)

            # Update status
            crew_sheet.status = 'processing'
            crew_sheet.save()

            # Process the image using OpenAI Vision
            extracted_data = OpenAIService.extract_crew_sheet_data(
                crew_sheet.image.path)

            # Check if there was an error in processing
            if "error" in extracted_data:
                # Save the error message separately, but keep the status as failed
                crew_sheet.status = 'failed'
                crew_sheet.error_message = extracted_data.pop(
                    "error")  # Remove error from extracted data
                crew_sheet.extracted_data = extracted_data  # Save the cleaned data
                crew_sheet.date_processed = datetime.now()
                crew_sheet.save()
                return False

            # Update the crew sheet with the extracted data - normal flow
            crew_sheet.extracted_data = extracted_data
            crew_sheet.status = 'completed' if extracted_data.get(
                'valid', True) else 'failed'
            crew_sheet.date_processed = datetime.now()

            # Only set error message if the sheet is invalid
            if not extracted_data.get('valid', True):
                crew_sheet.error_message = extracted_data.get(
                    'reason', 'Unknown error')
            else:
                crew_sheet.error_message = ""  # Use empty string instead of None for NOT NULL constraint

            crew_sheet.save()
            return True

        except Exception as e:
            logger.exception(
                f"Error processing crew sheet {crew_sheet_id}: {str(e)}")

            try:
                # Try to update the crew sheet status
                crew_sheet = CrewSheet.objects.get(id=crew_sheet_id)
                crew_sheet.status = 'failed'
                crew_sheet.error_message = str(e) if str(e) else ""  # Use empty string instead of None for NOT NULL constraint
                crew_sheet.date_processed = datetime.now()

                # Don't save the error in the extracted data
                if not crew_sheet.extracted_data:
                    crew_sheet.extracted_data = {"valid": True, "data": {}}

                crew_sheet.save()
            except Exception as inner_e:
                logger.exception(
                    f"Failed to update crew sheet status after error: {str(inner_e)}")

            return False
