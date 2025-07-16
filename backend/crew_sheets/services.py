import os
import json
import base64
import logging
from datetime import datetime
from django.conf import settings
import openai
from .models import CrewSheet

logger = logging.getLogger(__name__)

class OpenAIService:
    """Service for interacting with OpenAI's GPT-4 Vision API."""
    
    @staticmethod
    def get_client():
        """Get an initialized OpenAI client."""
        api_key = os.environ.get('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        
        return openai.OpenAI(api_key=api_key)
    
    @staticmethod
    def extract_crew_sheet_data(image_path):
        """
        Extract structured data from a crew sheet image using GPT-4 Vision.
        
        Args:
            image_path: Path to the crew sheet image file
            
        Returns:
            dict: Structured data extracted from the crew sheet
        """
        client = OpenAIService.get_client()
        
        try:
            # Read the image as base64
            with open(image_path, "rb") as image_file:
                # Create the API request
                response = client.chat.completions.create(
                    model="gpt-4-vision-preview",  # Use GPT-4 Vision model
                    messages=[
                        {
                            "role": "system",
                            "content": """
                            You are a specialized AI designed to extract data from crew sheets and timesheets.
                            Analyze the provided image and extract all relevant information in a structured JSON format.
                            
                            Follow these guidelines:
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
                               - Any summary or total information
                            3. Format the output as a clean JSON object.
                            4. If any text is unclear or potentially inaccurate, mark it with "uncertain": true.
                            
                            Return ONLY the JSON object with no additional text.
                            """
                        },
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": "Extract all data from this crew sheet into structured JSON format."
                                },
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/jpeg;base64,{base64.b64encode(image_file.read()).decode('utf-8')}"
                                    }
                                }
                            ]
                        }
                    ],
                    max_tokens=4000
                )
                
                # Extract and parse the JSON response
                result = response.choices[0].message.content
                
                try:
                    # Try to parse as JSON
                    return json.loads(result)
                except json.JSONDecodeError:
                    # If not valid JSON, return error
                    logger.error(f"Failed to parse GPT-4 Vision response as JSON: {result}")
                    return {"valid": False, "reason": "AI response was not in valid JSON format", "raw_response": result}
                
        except Exception as e:
            logger.exception(f"Error calling GPT-4 Vision API: {str(e)}")
            return {"valid": False, "reason": str(e)}


class CrewSheetProcessor:
    """Service for processing crew sheet images."""
    
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
            extracted_data = OpenAIService.extract_crew_sheet_data(crew_sheet.image.path)
            
            # Update the crew sheet with the extracted data
            crew_sheet.extracted_data = extracted_data
            crew_sheet.status = 'completed' if extracted_data.get('valid', True) else 'failed'
            crew_sheet.date_processed = datetime.now()
            
            if not extracted_data.get('valid', True):
                crew_sheet.error_message = extracted_data.get('reason', 'Unknown error')
                
            crew_sheet.save()
            return True
            
        except Exception as e:
            logger.exception(f"Error processing crew sheet {crew_sheet_id}: {str(e)}")
            
            try:
                # Try to update the crew sheet status
                crew_sheet = CrewSheet.objects.get(id=crew_sheet_id)
                crew_sheet.status = 'failed'
                crew_sheet.error_message = str(e)
                crew_sheet.date_processed = datetime.now()
                crew_sheet.save()
            except Exception:
                pass
                
            return False