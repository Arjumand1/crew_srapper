import os
import json
import base64
import logging
import time
import httpx
import re
from datetime import datetime
from .models import CrewSheet
from openai import OpenAI, APITimeoutError, APIConnectionError, APIError

logger = logging.getLogger(__name__)


class OpenAIService:
    """Service for OpenAI API calls."""

    @staticmethod
    def get_client():
        """
        Get an OpenAI client instance.
        """
        api_key = os.environ.get('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        if api_key in ['your-openai-api-key', 'sk-...', 'your_api_key_here']:
            raise ValueError("OPENAI_API_KEY contains a placeholder value")
        try:
            # Increased timeout to 120 seconds to prevent timeouts
            http_client = httpx.Client(proxies=None, timeout=120.0)
            return OpenAI(api_key=api_key, http_client=http_client)
        except Exception as e:
            logger.error(f"Error initializing OpenAI client: {e}")
            # fallback minimal client initialization
            return OpenAI(api_key=api_key)

    @staticmethod
    def _call_openai_api_with_retry(client, messages, max_tokens=4096, max_retries=2, timeout=120):
        """
        Make a call to the OpenAI API with retry logic.

        Args:
            client: OpenAI client
            messages: Messages to send to the API
            max_tokens: Maximum tokens for the response
            max_retries: Maximum number of retries
            timeout: Timeout in seconds for the API call

        Returns:
            The API response or raises an exception if all retries fail
        """
        logger.info("Sending request to OpenAI API")

        # Track retry attempts
        attempts = 0
        last_error = None

        while attempts < max_retries:
            try:
                start_time = time.time()

                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=messages,
                    max_tokens=max_tokens,
                    response_format={"type": "json_object"},
                    timeout=timeout
                )

                elapsed_time = time.time() - start_time
                logger.info(
                    f"OpenAI API call completed in {elapsed_time:.2f} seconds")

                return response

            except (httpx.TimeoutException, httpx.HTTPError) as e:
                attempts += 1
                last_error = e

                if attempts < max_retries:
                    # Calculate backoff time: 2^attempt * 1 second (2, 4, 8 seconds)
                    backoff = min(2 ** attempts, 10)
                    logger.warning(
                        f"API call attempt {attempts} failed: {str(e)}. Retrying in {backoff}s...")
                    time.sleep(backoff)
                else:
                    logger.error(
                        f"API call failed after {max_retries} attempts: {str(e)}")
                    raise

            except Exception as e:
                # Don't retry on non-timeout/HTTP errors
                logger.error(f"API call failed with error: {str(e)}")
                raise

        # If we get here, we've exceeded retries
        if last_error:
            raise last_error
        else:
            raise Exception("Maximum retries exceeded with unknown error")

    @staticmethod
    def extract_crew_sheet_data(image_path):
        """
        Extracts structured data from a crew sheet image using OpenAI's GPT-4o model.

        Args:
            image_path: Path to the crew sheet image file.

        Returns:
            Dictionary containing the extracted data or error information.
        """
        # Initialize error message with empty string to prevent NULL values
        error_message = ""

        # Pre-check: Verify image exists and log size
        if not os.path.exists(image_path):
            return {
                "valid": False,
                "error_message": f"Image file not found: {image_path}"
            }

        try:
            file_size_mb = os.path.getsize(image_path) / (1024 * 1024)
            logger.info(
                f"Processing image: {image_path} (Size: {file_size_mb:.2f}MB)")

            if file_size_mb > 10:
                logger.warning(
                    f"Large image detected ({file_size_mb:.2f}MB), may cause timeouts")
        except Exception as e:
            logger.error(f"Error checking image file: {str(e)}")

        # Encode image to base64
        try:
            with open(image_path, "rb") as image_file:
                base64_image = base64.b64encode(
                    image_file.read()).decode("utf-8")
        except Exception as e:
            error_message = f"Failed to read or encode image: {str(e)}"
            return {
                "valid": False,
                "error_message": error_message
            }

        # Prepare OpenAI client with increased timeout
        client = OpenAI(
            api_key=os.environ.get("OPENAI_API_KEY"),
            timeout=180.0,  # Increased timeout to 3 minutes for large images
        )

        # Configure the system prompt for data extraction
        messages = [
            {
                "role": "system",
                "content": """You are an expert at extracting data from crew/timesheets. These sheets track WHO (crew/people) does WHAT (task) WHERE (cost center), for HOW LONG (hours), and HOW FAST (pieces).

CRITICAL ANALYSIS STEPS:
1. FIRST: Study the sheet layout carefully - identify the table structure, nested headers, and data organization
2. SECOND: Map out all headers including parent-child relationships
3. THIRD: Identify cost centers and tasks within the table structure
4. FOURTH: Extract data with precise column matching

NESTED HEADER RULES (VERY IMPORTANT):
- Look for headers that span multiple columns with sub-headers below
- Examples:
  * "START" header with only "IN" column below → "START_IN"
  * "BREAK 1" header with "OUT" and "IN" columns below → "BREAK1_OUT", "BREAK1_IN"
  * "LUNCH" header with "OUT" and "IN" columns below → "LUNCH_OUT", "LUNCH_IN"
  * "BREAK 2" header with "OUT" and "IN" columns below → "BREAK2_OUT", "BREAK2_IN"
- NEVER use just "START", "BREAK 1", "LUNCH" if they have sub-columns
- Always include the sub-column identifier in the header name

COST CENTER & TASK HANDLING:
- Cost centers and tasks are often integrated into the main table structure
- Look for patterns like "JOB NO. HRS." and "JOB NO. PIECE WORK" columns
- These often repeat for different cost centers/tasks
- Number them sequentially: "JOB_NO_HRS_1", "JOB_NO_PIECE_WORK_1", "JOB_NO_HRS_2", "JOB_NO_PIECE_WORK_2", etc.
- Extract the actual cost center and task values from the sheet context

DATA PLACEMENT ACCURACY:
- Time values (like "6:05", "8:30", "11:00") must go in the correct nested column
- "✓" marks indicate presence/completion in that specific column
- Empty cells should remain empty, not filled with "✓" unless actually marked
- Each piece of data must match its exact column position

EXTRACTION PROCESS:
1. Identify the complete table structure including all nested headers
2. Create proper header names that reflect the nested structure
3. Extract cost centers and tasks from sheet context or embedded locations
4. Map each data cell to its correct header with precision
5. Capture all metadata and additional information

OUTPUT FORMAT:
{
  "date": "extracted date",
  "valid": true,
  "metadata": {
    "sheet_title": "title if present",
    "total_hours": "if calculated on sheet",
    "employee_count": "number of employees",
    "supervisor": "supervisor name if present",
    "department": "department if present",
    "project": "project info if present",
    "cost_centers": ["all cost centers found"],
    "tasks": ["all task codes/descriptions found"],
    "notes": "any additional notes or information",
    "sheet_number": "sheet number if present"
  },
  "table_headers": ["EMPLOYEE_NAME", "START_IN", "BREAK1_OUT", "BREAK1_IN", "LUNCH_OUT", "LUNCH_IN", "BREAK2_OUT", "BREAK2_IN", "STOP", "JOB_NO_HRS_1", "JOB_NO_PIECE_WORK_1", "JOB_NO_HRS_2", "JOB_NO_PIECE_WORK_2", "TOTAL_HRS"],
  "employees": [
    {
      "name": "Employee Name",
      "START_IN": "actual time or ✓",
      "BREAK1_OUT": "actual time or ✓",
      "BREAK1_IN": "actual time or ✓",
      "LUNCH_OUT": "actual time or ✓",
      "LUNCH_IN": "actual time or ✓",
      "BREAK2_OUT": "actual time or ✓",
      "BREAK2_IN": "actual time or ✓",
      "STOP": "actual time or ✓",
      "JOB_NO_HRS_1": "hours for job 1",
      "JOB_NO_PIECE_WORK_1": "pieces for job 1",
      "TOTAL_HRS": "total hours"
    }
  ]
}

CRITICAL: Study the image carefully before extracting. Look at the actual column structure, not just the main headers. Each time value must go in the correct nested column."""
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Extract all data from this crew sheet image as structured JSON. Include all headers, rows, and metadata."
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}"
                        }
                    }
                ]
            }
        ]

        # Track attempt count for retries
        attempt = 1
        max_attempts = 2
        backoff_factor = 2  # For exponential backoff

        while attempt <= max_attempts:
            try:
                logger.info(
                    f"Attempt {attempt}/{max_attempts}: Calling OpenAI API...")
                start_time = time.time()

                # Make the API call with response_format specified for JSON
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=messages,
                    max_tokens=4096,
                    temperature=0.1,  # Low temperature for more deterministic output
                    response_format={"type": "json_object"},
                    timeout=180,  # Setting timeout at API call level as well
                )

                # Log the duration and token usage
                duration = time.time() - start_time
                logger.info(f"OpenAI API call completed in {duration:.2f}s")

                # Get the response content
                content = response.choices[0].message.content

                # Parse JSON response
                try:
                    extracted_data = json.loads(content)
                    logger.info(
                        "Successfully parsed JSON from OpenAI response")

                    # Add validation flag if not present
                    if "valid" not in extracted_data:
                        extracted_data["valid"] = True

                    return extracted_data
                except json.JSONDecodeError as e:
                    logger.error(f"JSON parsing error: {str(e)}")

                    # Attempt to extract JSON using regex as fallback
                    logger.info(
                        "Attempting to extract JSON with regex fallback")
                    try:
                        # Look for content between curly braces, including nested structures
                        json_match = re.search(r'({[\s\S]*})', content)
                        if json_match:
                            extracted_json_str = json_match.group(1)
                            extracted_data = json.loads(extracted_json_str)
                            logger.info(
                                "Successfully extracted JSON with regex fallback")

                            # Add validation flag if not present
                            if "valid" not in extracted_data:
                                extracted_data["valid"] = True

                            return extracted_data
                    except Exception as regex_err:
                        logger.error(
                            f"Regex JSON extraction failed: {str(regex_err)}")

                    error_message = f"Failed to parse JSON response: {str(e)}"

            except APITimeoutError as e:
                logger.warning(
                    f"OpenAI API timeout on attempt {attempt}/{max_attempts}: {str(e)}")
                error_message = f"API timeout: {str(e)}"
            except APIConnectionError as e:
                logger.warning(
                    f"OpenAI API connection error on attempt {attempt}/{max_attempts}: {str(e)}")
                error_message = f"API connection error: {str(e)}"
            except APIError as e:
                logger.warning(
                    f"OpenAI API error on attempt {attempt}/{max_attempts}: {str(e)}")
                error_message = f"API error: {str(e)}"
            except Exception as e:
                logger.error(
                    f"Unexpected error on attempt {attempt}/{max_attempts}: {str(e)}")
                error_message = f"Unexpected error: {str(e)}"

            # If we haven't reached max attempts, back off and retry
            if attempt < max_attempts:
                wait_time = backoff_factor ** attempt
                logger.info(
                    f"Backing off for {wait_time} seconds before retry...")
                time.sleep(wait_time)

            attempt += 1

        # If we've exhausted all attempts, return an error
        return {
            "valid": False,
            "error_message": error_message or "Failed to extract data after multiple attempts"
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
        # Initialize with empty error message to avoid NULL constraint violations
        error_message = ""

        try:
            # Get the crew sheet
            crew_sheet = CrewSheet.objects.get(id=crew_sheet_id)

            # Update status
            crew_sheet.status = 'processing'
            crew_sheet.error_message = ""  # Clear any previous errors
            crew_sheet.save()

            # Check if image file exists
            if not crew_sheet.image or not os.path.exists(crew_sheet.image.path):
                error_message = "Image file not found or inaccessible"
                crew_sheet.status = 'failed'
                crew_sheet.error_message = error_message
                crew_sheet.date_processed = datetime.now()
                crew_sheet.save()
                return False

            logger.info(
                f"Processing crew sheet: {crew_sheet_id}, image: {crew_sheet.image.path}")

            # Process the image using OpenAI Vision
            extracted_data = OpenAIService.extract_crew_sheet_data(
                crew_sheet.image.path)

            # Check if there was an error in processing
            if "error" in extracted_data:
                # Save the error message separately, but keep the status as failed
                error_message = extracted_data.pop("error") or "Unknown error"
                crew_sheet.status = 'failed'
                crew_sheet.error_message = error_message
                crew_sheet.extracted_data = extracted_data  # Save the cleaned data
                crew_sheet.date_processed = datetime.now()
                crew_sheet.save()
                logger.error(
                    f"Failed to process crew sheet {crew_sheet_id}: {error_message}")
                return False

            # Update the crew sheet with the extracted data - normal flow
            crew_sheet.extracted_data = extracted_data
            crew_sheet.status = 'completed' if extracted_data.get(
                'valid', True) else 'failed'
            crew_sheet.date_processed = datetime.now()

            # Only set error message if the sheet is invalid
            if not extracted_data.get('valid', True):
                error_message = extracted_data.get(
                    'reason', 'Invalid crew sheet')
                crew_sheet.error_message = error_message
            else:
                # Use empty string for NOT NULL constraint
                crew_sheet.error_message = ""

            crew_sheet.save()
            logger.info(f"Successfully processed crew sheet {crew_sheet_id}")
            return True

        except Exception as e:
            error_message = str(e) if str(e) else "Unknown error occurred"
            logger.exception(
                f"Error processing crew sheet {crew_sheet_id}: {error_message}")

            try:
                # Try to update the crew sheet status
                crew_sheet = CrewSheet.objects.get(id=crew_sheet_id)
                crew_sheet.status = 'failed'
                # Use empty string instead of None for NOT NULL constraint
                crew_sheet.error_message = error_message
                crew_sheet.date_processed = datetime.now()

                # Don't save the error in the extracted data
                if not crew_sheet.extracted_data:
                    crew_sheet.extracted_data = {
                        "valid": False, "error": error_message}

                crew_sheet.save()
            except Exception as inner_e:
                logger.exception(
                    f"Failed to update crew sheet status after error: {str(inner_e)}")

            return False
