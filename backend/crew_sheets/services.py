import os
import re
import json
import time
import base64
import logging
from typing import List, Dict, Any, Optional, Tuple
from openai import OpenAI
from openai.types.chat import ChatCompletion
from openai._exceptions import APIError, APITimeoutError, APIConnectionError
from django.conf import settings
from django.core.files.storage import default_storage
from datetime import datetime
from django.utils import timezone
from .analytics import LearningSystem, QualityValidator, ExtractionLogger, ContinuousLearner
from .models import CrewSheet, ExtractionExample, SheetTemplate, CompanyLearningProfile, SmartReviewQueue
import httpx

logger = logging.getLogger(__name__)


class OpenAIService:
    """Service for interacting with OpenAI's API."""

    @staticmethod
    def get_client():
        """Get OpenAI client with proper configuration."""
        return OpenAI(
            api_key=os.environ.get("OPENAI_API_KEY"),
            timeout=180.0,  # 3 minutes timeout for large images
            http_client=httpx.Client(proxies=None, timeout=180.0)
        )

    @staticmethod
    def _call_openai_api_with_retry(client, messages, max_tokens=4096, max_retries=2, timeout=120):
        """Call OpenAI API with retry logic."""
        for attempt in range(max_retries):
            try:
                logger.info(f"OpenAI API call attempt {attempt + 1}/{max_retries}")
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=0.1,
                    response_format={"type": "json_object"},
                    timeout=timeout
                )
                return response
            except (APITimeoutError, APIConnectionError, APIError) as e:
                if attempt < max_retries - 1:
                    wait_time = (2 ** attempt)  # Exponential backoff
                    logger.warning(f"API call failed, retrying in {wait_time}s: {str(e)}")
                    time.sleep(wait_time)
                else:
                    raise e

    @staticmethod
    def _make_api_call(client, messages):
        """Make the API call to OpenAI."""
        start_time = time.time()
        try:
            response = OpenAIService._call_openai_api_with_retry(
                client, messages, max_tokens=4096, max_retries=2, timeout=120)
            content = response.choices[0].message.content
            duration = time.time() - start_time

            # Parse JSON response
            try:
                extracted_data = json.loads(content)
                logger.info(
                    "Successfully parsed JSON from OpenAI response")

                # Add validation flag if not present
                if "valid" not in extracted_data:
                    extracted_data["valid"] = True

                # Add performance metrics for learning system
                extracted_data["_performance_metrics"] = {
                    "extraction_time_seconds": time.time() - start_time,
                    "api_call_duration": duration,
                    "token_usage": {
                        "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                        "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                        "total_tokens": response.usage.total_tokens if response.usage else 0
                    }
                }

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

                        # Add performance metrics
                        extracted_data["_performance_metrics"] = {
                            "extraction_time_seconds": time.time() - start_time,
                            "api_call_duration": duration,
                            "token_usage": {
                                "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                                "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                                "total_tokens": response.usage.total_tokens if response.usage else 0
                            },
                            "used_regex_fallback": True
                        }

                        return extracted_data
                except Exception as regex_err:
                    logger.error(
                        f"Regex JSON extraction failed: {str(regex_err)}")

                error_message = f"Failed to parse JSON response: {str(e)}"

        except APITimeoutError as e:
            logger.warning(
                f"OpenAI API timeout: {str(e)}")
            error_message = f"API timeout: {str(e)}"
        except APIConnectionError as e:
            logger.warning(
                f"OpenAI API connection error: {str(e)}")
            error_message = f"API connection error: {str(e)}"
        except APIError as e:
            logger.warning(
                f"OpenAI API error: {str(e)}")
            error_message = f"API error: {str(e)}"
        except Exception as e:
            logger.error(
                f"Unexpected error: {str(e)}")
            error_message = f"Unexpected error: {str(e)}"

        return {
            "valid": False,
            "error_message": error_message or "Failed to extract data"
        }

    @staticmethod
    def extract_crew_sheet_data(image_path):
        """Extract crew sheet data from image using OpenAI Vision API."""
        logger.info(f"Starting extraction for image: {image_path}")

        # Validate image exists and read it
        try:
            with open(image_path, "rb") as image_file:
                base64_image = base64.b64encode(image_file.read()).decode('utf-8')
        except Exception as e:
            error_message = f"Failed to read or encode image: {str(e)}"
            return {
                "valid": False,
                "error_message": error_message
            }

        # Prepare OpenAI client with increased timeout
        client = OpenAIService.get_client()

        # Configure the system prompt for data extraction
        messages = [
            {
                "role": "system",
                "content": """You are an expert at extracting data from crew/timesheets. These sheets track WHO (crew/people) does WHAT (task) WHERE (cost center), for HOW LONG (hours), and HOW FAST (pieces).

CRITICAL ANALYSIS STEPS:
1. FIRST: Study the sheet layout carefully - identify the table structure, hierarchical headers, and data organization
2. SECOND: Map out ALL headers including multi-level hierarchical relationships (cost centers → tasks → job columns)
3. THIRD: Identify how cost centers and tasks relate to job columns in the header structure
4. FOURTH: Extract data with precise column matching

HIERARCHICAL HEADER STRUCTURE (VERY IMPORTANT):
- Many crew sheets use a THREE-LEVEL HIERARCHY in their headers:
  * TOP LEVEL: Cost Centers (e.g., "KW13", "270", "CMA")
  * MIDDLE LEVEL: Tasks (e.g., "zero", "socker", "irrigation")
  * BOTTOM LEVEL: Job columns (e.g., "Job No Hrs", "Job Piece Work")
- CAPTURE THIS HIERARCHY in your column naming using this format: COST_CENTER_TASK_JOBTYPE
  * Example: "KW13_ZERO_JOB_NO_HRS" where KW13 is cost center, ZERO is task, JOB_NO_HRS is job type
  * If cost center or task is missing, use format: TASK_JOBTYPE or JOBTYPE as appropriate
- CONSISTENTLY APPLY this hierarchy across all similar columns

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
- Cost centers and tasks are often PART OF THE HEADER HIERARCHY, not separate metadata
- They typically appear ABOVE the job columns in the header structure
- Create headers that reflect this relationship: COST_CENTER_TASK_JOB_TYPE
- Number them sequentially only if needed for uniqueness: "KW13_ZERO_JOB_NO_HRS_1", "KW13_SOCKER_JOB_NO_HRS_1". THis is just example. You will need to take care of every center and task.
- INCLUDE the cost center and task values directly in the header names, not just in metadata
- Sometimes there will be no cost centers and tasks above so only job type

DATA PLACEMENT ACCURACY:
- Match data values to the CORRECT hierarchical columns
- Time values must go in precise columns (START_IN, BREAK1_OUT, etc.)
- Job data must go in the corresponding hierarchical columns (COST_CENTER_TASK_JOB_TYPE) for all cost centers and tasks and their job types.
- Only use placeholder marks ("✓") if actually present in original
- Extract actual numeric and text values whenever present

EXTRACTION PROCESS:
1. Scan the ENTIRE sheet first, noting the header structure and hierarchy
2. Map ALL headers, preserving hierarchical relationships
3. Extract employee data row by row
4. Ensure data aligns with the correct hierarchical headers
5. Capture metadata like date, supervisor, sheet title from outside the main table

OUTPUT FORMAT:
{
  "date": "6-23-25",
  "valid": true, 
  "metadata": {
    "notes": "Any notes found on the sheet",
    "supervisor": "Name if found",
    "sheet_title": "Title if present",
    "total_hours": "182.5",
    "employee_count": "23",
    "sheet_number": "Any ID/number found"
  },
  "employees": [
    {
      "name": "John Smith",
      "START_IN": "6:00",
      "BREAK1_OUT": "8:30",
      "BREAK1_IN": "9:00",
      "LUNCH_OUT": "11:30", 
      "LUNCH_IN": "12:00",
      "KW13_ZERO_JOB_NO_HRS": "2",
      "KW13_ZERO_JOB_PIECE_WORK": "9",
      "KW13_SOCKER_JOB_NO_HRS": "1.5", 
      "TOTAL_HRS": "8"
    },
    // Additional employee records...
  ],
  "table_headers": [
    "EMPLOYEE_NAME",
    "START_IN",
    "BREAK1_OUT", 
    "BREAK1_IN",
    "LUNCH_OUT", 
    "LUNCH_IN",
    "KW13_ZERO_JOB_NO_HRS",
    "KW13_ZERO_JOB_PIECE_WORK",
    "KW13_SOCKER_JOB_NO_HRS",
    "TOTAL_HRS"
  ]
}

Remember: correctly identify and preserve ALL hierarchical relationships in the header structure, and extract data into this precise structure."""
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

        return OpenAIService._make_api_call(client, messages)

    @staticmethod
    def extract_crew_sheet_data_with_prompt(image_path: str, custom_prompt: str):
        """Extract crew sheet data using a custom prompt."""
        logger.info(f"Starting extraction with custom prompt for image: {image_path}")

        # Validate image exists and read it
        try:
            with open(image_path, "rb") as image_file:
                base64_image = base64.b64encode(image_file.read()).decode('utf-8')
        except Exception as e:
            error_message = f"Failed to read or encode image: {str(e)}"
            return {
                "valid": False,
                "error_message": error_message
            }

        # Prepare OpenAI client with increased timeout
        client = OpenAIService.get_client()

        # Use the custom prompt
        messages = [
            {
                "role": "system",
                "content": custom_prompt
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

        return OpenAIService._make_api_call(client, messages)


class RAGPipeline:
    """Retrieval-Augmented Generation pipeline for better extractions."""
    
    @staticmethod
    def find_similar_extractions(
        sheet_description: str,
        template_id: str = None,
        limit: int = 3
    ) -> List[dict]:
        """Find similar successful extractions for few-shot learning."""
        from .models import ExtractionExample, SheetTemplate
        
        # Start with high-quality examples
        query = ExtractionExample.objects.filter(
            is_high_quality=True,
            confidence_score__gte=0.8,
            edit_ratio__lte=0.2
        )
        
        # Filter by template if provided
        if template_id:
            try:
                template = SheetTemplate.objects.get(id=template_id)
                query = query.filter(template=template)
            except SheetTemplate.DoesNotExist:
                pass
        
        # Get recent successful examples
        examples = list(query.order_by('-confidence_score', '-user_satisfaction')[:limit])
        
        # Format for few-shot learning
        few_shot_examples = []
        for example in examples:
            few_shot_examples.append({
                'description': example.input_description,
                'extraction': example.extraction_result,
                'confidence': example.confidence_score,
                'template_type': example.template.template_type if example.template else 'unknown'
            })
        
        return few_shot_examples
    
    @staticmethod
    def generate_dynamic_prompt(
        base_prompt: str,
        template: 'SheetTemplate' = None,
        company_profile: 'CompanyLearningProfile' = None,
        few_shot_examples: List[dict] = None,
        recent_corrections: dict = None
    ) -> str:
        """Generate a dynamic prompt based on context and learning data."""
        
        enhanced_prompt = base_prompt
        
        # Add template-specific instructions
        if template:
            enhanced_prompt += f"\n\nTEMPLATE-SPECIFIC GUIDANCE:\n"
            enhanced_prompt += f"Sheet Type: {template.get_template_type_display()}\n"
            enhanced_prompt += f"Expected Fields: {', '.join(template.expected_fields)}\n"
            
            if template.header_structure:
                enhanced_prompt += f"Known Header Structure: {json.dumps(template.header_structure, indent=2)}\n"
        
        # Add company-specific patterns
        if company_profile:
            enhanced_prompt += f"\n\nCOMPANY PATTERNS FOR {company_profile.company_name.upper()}:\n"
            
            if company_profile.common_cost_centers:
                enhanced_prompt += f"- Common Cost Centers: {', '.join(company_profile.common_cost_centers)}\n"
            
            if company_profile.common_tasks:
                enhanced_prompt += f"- Common Tasks: {', '.join(company_profile.common_tasks)}\n"
            
            if company_profile.typical_headers:
                enhanced_prompt += f"- Typical Headers: {', '.join(company_profile.typical_headers)}\n"
            
            if company_profile.time_format_preferences:
                enhanced_prompt += f"- Time Format Preferences: {json.dumps(company_profile.time_format_preferences)}\n"
        
        # Add few-shot examples
        if few_shot_examples:
            enhanced_prompt += f"\n\nSUCCESSFUL EXTRACTION EXAMPLES:\n"
            for i, example in enumerate(few_shot_examples[:2], 1):  # Limit to 2 examples to save tokens
                enhanced_prompt += f"\nExample {i} (Confidence: {example['confidence']:.1%}):\n"
                enhanced_prompt += f"Description: {example['description']}\n"
                enhanced_prompt += f"Result: {json.dumps(example['extraction'], indent=2)}\n"
        
        # Add recent correction patterns
        if recent_corrections and 'most_edited_fields' in recent_corrections:
            enhanced_prompt += f"\n\nRECENT CORRECTION PATTERNS:\n"
            for field, count in list(recent_corrections['most_edited_fields'].items())[:5]:
                enhanced_prompt += f"- Field '{field}' frequently needs correction ({count} times)\n"
        
        enhanced_prompt += f"\n\nRemember: Extract data with high precision, following the patterns shown in examples."
        
        return enhanced_prompt


class TemplateMatchingService:
    """Service for matching sheets to templates and managing templates."""
    
    @staticmethod
    def suggest_template(user, sheet_image_path: str = None) -> List[dict]:
        """Suggest matching templates for a user's sheet."""
        from .models import SheetTemplate
        
        # Get user's templates first
        user_templates = SheetTemplate.objects.filter(
            user=user,
            is_active=True
        ).order_by('-success_rate', '-usage_count')
        
        # TODO: In future, implement image similarity matching
        # For now, return user's best templates
        suggestions = []
        for template in user_templates[:5]:
            suggestions.append({
                'id': str(template.id),
                'name': template.name,
                'description': template.description,
                'template_type': template.template_type,
                'success_rate': template.success_rate,
                'usage_count': template.usage_count,
                'company': template.company
            })
        
        return suggestions
    
    @staticmethod
    def create_template_from_sheet(
        user,
        crew_sheet: 'CrewSheet',
        template_name: str,
        template_type: str,
        description: str = '',
        company: str = ''
    ) -> 'SheetTemplate':
        """Create a new template from a successful extraction."""
        from .models import SheetTemplate
        
        # Extract header structure and expected fields from the crew sheet
        extracted_data = crew_sheet.extracted_data or {}
        header_structure = {}
        expected_fields = extracted_data.get('table_headers', [])
        
        # Analyze header structure
        if 'employees' in extracted_data and extracted_data['employees']:
            first_employee = extracted_data['employees'][0]
            for field_name in expected_fields:
                if '_' in field_name:
                    parts = field_name.split('_')
                    if len(parts) >= 2:
                        category = '_'.join(parts[:-1])
                        if category not in header_structure:
                            header_structure[category] = []
                        header_structure[category].append(field_name)
        
        template = SheetTemplate.objects.create(
            user=user,
            name=template_name,
            description=description,
            company=company,
            template_image=crew_sheet.image,
            header_structure=header_structure,
            expected_fields=expected_fields,
            template_type=template_type,
            success_rate=crew_sheet.confidence_score or 0.8
        )
        
        return template
    
    @staticmethod
    def _update_template_success_rate(template: 'SheetTemplate', new_confidence: float) -> None:
        """Update template success rate based on new usage."""
        # Running average calculation
        current_rate = template.success_rate
        usage_count = template.usage_count
        
        # Weight the new confidence with existing rate
        if usage_count > 1:
            template.success_rate = ((current_rate * (usage_count - 1)) + new_confidence) / usage_count
        else:
            template.success_rate = new_confidence
        
        template.save()
        logger.info(f"Updated template {template.name} success rate to {template.success_rate:.2%}")


class SmartReviewQueueService:
    """Service for managing the intelligent review queue."""
    
    @staticmethod
    def evaluate_for_review(crew_sheet: 'CrewSheet') -> bool:
        """Evaluate if a sheet needs to be added to review queue."""
        from .models import SmartReviewQueue
        
        priority_score = 0.0
        review_reasons = []
        flagged_issues = []
        suggested_actions = []
        
        # Check confidence score
        if crew_sheet.confidence_score < 0.7:
            priority_score += 30
            review_reasons.append('low_confidence')
            flagged_issues.append(f'Low confidence score: {crew_sheet.confidence_score:.2%}')
            suggested_actions.append('Manual verification of extracted data required')
        
        # Check if validation failed
        if crew_sheet.needs_review:
            priority_score += 25
            review_reasons.append('validation_failed')
            flagged_issues.append('Failed automatic validation rules')
            suggested_actions.append('Review validation errors and correct data')
        
        # Check for unusual format (no similar template)
        user_templates_count = crew_sheet.user.sheettemplate_set.filter(is_active=True).count()
        if user_templates_count == 0:
            priority_score += 15
            review_reasons.append('unusual_format')
            flagged_issues.append('No matching template found')
            suggested_actions.append('Consider creating a template for this sheet type')
        
        # Check expected edit frequency based on user history
        user_profile = getattr(crew_sheet.user, 'extraction_profile', None)
        if user_profile and user_profile.total_edits_made > 0:
            avg_edits = user_profile.total_edits_made / max(user_profile.total_sheets_processed, 1)
            if avg_edits > 5:  # High edit frequency
                priority_score += 20
                review_reasons.append('high_edit_frequency')
                flagged_issues.append(f'High expected edit frequency: {avg_edits:.1f} edits/sheet')
                suggested_actions.append('Pre-review recommended due to user edit patterns')
        
        # Add to queue if priority score is high enough
        if priority_score >= 20:
            SmartReviewQueue.objects.update_or_create(
                crew_sheet=crew_sheet,
                defaults={
                    'priority_score': priority_score,
                    'review_reason': review_reasons[0] if review_reasons else 'low_confidence',
                    'flagged_issues': flagged_issues,
                    'suggested_actions': suggested_actions
                }
            )
            return True
        
        return False


class EnhancedExtractionService:
    """Enhanced extraction service with RAG and template-based learning."""
    
    @staticmethod
    def extract_with_intelligence(
        crew_sheet: 'CrewSheet',
        template_id: str = None,
        use_rag: bool = True
    ) -> dict:
        """Extract data using intelligent RAG pipeline and templates."""
        from .analytics import ExtractionLogger, ContinuousLearner
        from .models import SheetTemplate, CompanyLearningProfile
        
        start_time = time.time()
        
        try:
            # Get template if specified
            template = None
            if template_id:
                try:
                    template = SheetTemplate.objects.get(id=template_id, user=crew_sheet.user)
                    template.usage_count += 1
                    template.save()
                except SheetTemplate.DoesNotExist:
                    logger.warning(f"Template {template_id} not found")
            
            # Get company learning profile
            company_profile = None
            try:
                company_profile = CompanyLearningProfile.objects.get(user=crew_sheet.user)
            except CompanyLearningProfile.DoesNotExist:
                pass
            
            # Get recent corrections for this user
            recent_corrections = ContinuousLearner.analyze_corrections(days_back=30) if use_rag else None
            
            # Find similar successful extractions
            few_shot_examples = []
            if use_rag:
                sheet_description = f"Crew sheet for {crew_sheet.user.username}"
                few_shot_examples = RAGPipeline.find_similar_extractions(
                    sheet_description, template_id, limit=2
                )
            
            # Generate dynamic prompt
            base_prompt = ContinuousLearner.generate_improved_prompt()
            enhanced_prompt = RAGPipeline.generate_dynamic_prompt(
                base_prompt=base_prompt,
                template=template,
                company_profile=company_profile,
                few_shot_examples=few_shot_examples,
                recent_corrections=recent_corrections
            )
            
            # Perform extraction with enhanced prompt
            result = OpenAIService.extract_crew_sheet_data_with_prompt(
                crew_sheet.image.path, enhanced_prompt
            )
            
            processing_time = time.time() - start_time
            
            if result.get('valid'):
                # Log the extraction
                confidence_scores = {'overall_confidence': result.get('confidence_score', 0.8)}
                ExtractionLogger.log_extraction(
                    crew_sheet=crew_sheet,
                    raw_extraction=result,
                    confidence_scores=confidence_scores,
                    processing_time=processing_time,
                    api_cost=0.05,  # Estimate
                    token_usage={'prompt_tokens': len(enhanced_prompt.split())}
                )
                
                # Evaluate for review queue
                SmartReviewQueueService.evaluate_for_review(crew_sheet)
                
                # Update template success rate if used
                if template:
                    TemplateMatchingService._update_template_success_rate(
                        template, result.get('confidence_score', 0.8)
                    )
            
            return result
            
        except Exception as e:
            logger.error(f"Enhanced extraction failed: {str(e)}")
            # Fallback to standard extraction
            return OpenAIService.extract_crew_sheet_data(crew_sheet.image.path)
    
    @staticmethod
    def _perform_extraction_with_prompt(crew_sheet: 'CrewSheet', prompt: str) -> dict:
        """Perform extraction with a custom prompt."""
        return OpenAIService.extract_crew_sheet_data_with_prompt(
            crew_sheet.image.path, prompt
        )


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
                crew_sheet.date_processed = timezone.now()
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
                crew_sheet.date_processed = timezone.now()
                crew_sheet.save()
                logger.error(
                    f"Failed to process crew sheet {crew_sheet_id}: {error_message}")
                return False

            # Update the crew sheet with the extracted data - normal flow
            crew_sheet.extracted_data = extracted_data
            crew_sheet.status = 'completed' if extracted_data.get(
                'valid', True) else 'failed'
            crew_sheet.date_processed = timezone.now()

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
                crew_sheet.date_processed = timezone.now()

                # Don't save the error in the extracted data
                if not crew_sheet.extracted_data:
                    crew_sheet.extracted_data = {
                        "valid": False, "error": error_message}

                crew_sheet.save()
            except Exception as inner_e:
                logger.exception(
                    f"Failed to update crew sheet status after error: {str(inner_e)}")

            return False

    @staticmethod
    def process_crew_sheet_with_learning(crew_sheet):
        """
        Process a crew sheet through the complete learning pipeline.

        Args:
            crew_sheet: CrewSheet model instance

        Returns:
            dict: Processing results with learning metrics
        """
        try:
            logger.info(
                f"Processing crew sheet {crew_sheet.id} with learning pipeline")

            # Update status
            crew_sheet.status = 'processing'
            crew_sheet.save()

            # Extract data using OpenAI
            extracted_data = OpenAIService.extract_crew_sheet_data(
                crew_sheet.image.path)

            if not extracted_data.get('valid'):
                crew_sheet.status = 'failed'
                crew_sheet.error_message = extracted_data.get(
                    'error_message', 'Unknown error')
                crew_sheet.save()
                return extracted_data

            # Remove performance metrics from main data before saving
            performance_metrics = extracted_data.pop(
                '_performance_metrics', {})

            # Process through learning system
            learning_results = LearningSystem.process_extraction(
                crew_sheet, extracted_data)

            # Update crew sheet with processed data
            crew_sheet.extracted_data = extracted_data
            crew_sheet.status = 'completed'
            crew_sheet.date_processed = timezone.now()
            crew_sheet.confidence_score = learning_results['confidence_score']
            crew_sheet.needs_review = learning_results['needs_review']
            crew_sheet.save()

            logger.info(
                f"Successfully processed crew sheet {crew_sheet.id} - Confidence: {learning_results['confidence_score']:.2f}")

            return {
                "valid": True,
                "extracted_data": extracted_data,
                "learning_metrics": {
                    "confidence_score": learning_results['confidence_score'],
                    "needs_review": learning_results['needs_review'],
                    "issues_detected": learning_results['issues'],
                    "performance_metrics": performance_metrics
                }
            }

        except Exception as e:
            logger.error(
                f"Error processing crew sheet {crew_sheet.id}: {str(e)}")
            crew_sheet.status = 'failed'
            crew_sheet.error_message = str(e)
            crew_sheet.save()

            return {
                "valid": False,
                "error_message": str(e)
            }
