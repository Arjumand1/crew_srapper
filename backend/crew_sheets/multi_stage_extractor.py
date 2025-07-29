"""
Multi-Stage Extraction Pipeline for Better Accuracy
Breaks down extraction into stages: structure analysis → data extraction → validation
"""
import json
import logging
from typing import Dict, Optional
# Remove the import that causes the circular dependency
# from .services import OpenAIService
from .models import SheetTemplate, CompanyLearningProfile
from .image_processor import ImagePreprocessor, AdaptivePreprocessor

logger = logging.getLogger(__name__)


class MultiStageExtractor:
    """Multi-stage extraction pipeline for improved accuracy."""

    @staticmethod
    def extract_with_stages(
        image_path: str,
        template: Optional[SheetTemplate] = None,
        company_profile: Optional[CompanyLearningProfile] = None,
        use_preprocessing: bool = True
    ) -> Dict:
        """
        Extract data using multi-stage pipeline.

        Args:
            image_path: Path to the crew sheet image
            template: Optional template for guidance
            company_profile: Optional company learning profile
            use_preprocessing: Whether to preprocess the image

        Returns:
            Complete extraction result with confidence metrics
        """
        logger.info(f"Starting multi-stage extraction for: {image_path}")

        try:
            # Stage 0: Image preprocessing (if enabled)
            processed_image_path = image_path
            image_quality_metrics = {}

            if use_preprocessing:
                logger.info("Stage 0: Image preprocessing")
                image_quality_metrics = ImagePreprocessor.assess_image_quality(
                    image_path)
                processed_image_path = AdaptivePreprocessor.preprocess_adaptive(
                    image_path)
                logger.info(
                    f"Image quality score: {image_quality_metrics.get('overall_quality', 0):.3f}")

            # Stage 1: Structure Analysis
            logger.info("Stage 1: Structure analysis")
            structure_result = MultiStageExtractor._analyze_structure(
                processed_image_path, template, company_profile
            )

            if not structure_result.get('valid', False):
                return {
                    'valid': False,
                    'error_message': 'Structure analysis failed',
                    'stage_failed': 'structure_analysis',
                    'image_quality_metrics': image_quality_metrics
                }

            # Stage 2: Data Extraction
            logger.info("Stage 2: Data extraction")
            data_result = MultiStageExtractor._extract_data_with_structure(
                processed_image_path, structure_result, template, company_profile
            )

            if not data_result.get('valid', False):
                return {
                    'valid': False,
                    'error_message': 'Data extraction failed',
                    'stage_failed': 'data_extraction',
                    'structure_analysis': structure_result,
                    'image_quality_metrics': image_quality_metrics
                }

            # Stage 3: Cross-validation and Enhancement
            logger.info("Stage 3: Cross-validation")
            final_result = MultiStageExtractor._cross_validate_and_enhance(
                structure_result, data_result, template, company_profile
            )

            # Add metadata about the extraction process
            final_result['extraction_metadata'] = {
                'stages_completed': 3,
                'preprocessing_used': use_preprocessing,
                'image_quality_metrics': image_quality_metrics,
                'template_used': template.name if template else None,
                'company_profile_used': company_profile.company_name if company_profile else None
            }

            logger.info(
                f"Multi-stage extraction completed with confidence: {final_result.get('confidence_score', 0):.3f}")
            return final_result

        except Exception as e:
            logger.error(f"Multi-stage extraction failed: {str(e)}")
            return {
                'valid': False,
                'error_message': f'Multi-stage extraction failed: {str(e)}',
                'stage_failed': 'pipeline_error'
            }

    @staticmethod
    def _analyze_structure(
        image_path: str,
        template: Optional[SheetTemplate] = None,
        company_profile: Optional[CompanyLearningProfile] = None
    ) -> Dict:
        """Stage 1: Analyze the structure and layout of the sheet."""
        # Import OpenAIService here to avoid circular imports
        from .services import OpenAIService

        # Build structure analysis prompt
        structure_prompt = MultiStageExtractor._build_structure_prompt(
            template, company_profile)

        try:
            # Extract structure using OpenAI
            structure_result = OpenAIService.extract_crew_sheet_data_with_prompt(
                image_path, structure_prompt
            )

            if structure_result.get('valid', False):
                # Enhance structure analysis with template knowledge
                if template and template.header_structure:
                    structure_result = MultiStageExtractor._enhance_structure_with_template(
                        structure_result, template
                    )

                # Validate structure makes sense
                structure_result = MultiStageExtractor._validate_structure_analysis(
                    structure_result)

            return structure_result

        except Exception as e:
            logger.error(f"Structure analysis failed: {str(e)}")
            return {
                'valid': False,
                'error_message': f'Structure analysis failed: {str(e)}'
            }

    @staticmethod
    def _build_structure_prompt(
        template: Optional[SheetTemplate] = None,
        company_profile: Optional[CompanyLearningProfile] = None
    ) -> str:
        """Build prompt for structure analysis stage."""

        base_prompt = """You are an expert at analyzing crew sheet layouts and structures.

ANALYZE THIS CREW SHEET IMAGE AND IDENTIFY:

1. TABLE STRUCTURE:
   - Overall table boundaries
   - Number of header rows (1, 2, or 3 levels)
   - Number of data rows visible
   - Column boundaries and alignment

2. HEADER HIERARCHY:
   - Main headers (top level)
   - Sub-headers (middle level) 
   - Column headers (bottom level)
   - How headers span across columns
   - Header groupings and relationships

3. LAYOUT CHARACTERISTICS:
   - Sheet orientation (portrait/landscape)
   - Text size and clarity
   - Handwritten vs printed sections
   - Table vs form layout

4. CONTENT CATEGORIES:
   - Time tracking sections (start, breaks, lunch, end)
   - Job/task sections (cost centers, tasks, job codes)
   - Employee information section
   - Summary/total sections

RETURN ONLY STRUCTURE ANALYSIS AS JSON:
{
  "valid": true,
  "layout": {
    "orientation": "landscape|portrait",
    "table_boundaries": {"top": 0, "left": 0, "right": 100, "bottom": 80},
    "header_rows": 2,
    "data_rows": 15,
    "column_count": 12
  },
  "header_structure": {
    "levels": 2,
    "main_headers": ["EMPLOYEE", "TIME TRACKING", "JOB ASSIGNMENTS"],
    "header_spans": {
      "TIME TRACKING": ["START", "BREAK1_OUT", "BREAK1_IN", "LUNCH_OUT", "LUNCH_IN"],
      "JOB ASSIGNMENTS": ["KW13_ZERO_HRS", "KW13_ZERO_PCS", "270_SOCKER_HRS"]
    }
  },
  "content_sections": {
    "employee_info": {"present": true, "columns": ["EMPLOYEE_NAME"]},
    "time_tracking": {"present": true, "columns": ["START", "BREAK1_OUT", "BREAK1_IN"]},
    "job_assignments": {"present": true, "columns": ["KW13_ZERO_HRS", "270_SOCKER_HRS"]},
    "totals": {"present": true, "columns": ["TOTAL_HRS"]}
  },
  "quality_indicators": {
    "text_clarity": "high|medium|low",
    "handwritten_sections": false,
    "partial_visibility": false
  }
}"""

        # Add template-specific guidance
        if template:
            base_prompt += f"\n\nTEMPLATE CONTEXT:\n"
            base_prompt += f"Expected template type: {template.get_template_type_display()}\n"
            if template.expected_fields:
                base_prompt += f"Expected fields: {', '.join(template.expected_fields)}\n"
            if template.header_structure:
                base_prompt += f"Known header patterns: {json.dumps(template.header_structure, indent=2)}\n"

        # Add company-specific guidance
        if company_profile:
            base_prompt += f"\n\nCOMPANY CONTEXT:\n"
            if company_profile.common_cost_centers:
                base_prompt += f"Known cost centers: {', '.join(company_profile.common_cost_centers)}\n"
            if company_profile.common_tasks:
                base_prompt += f"Known tasks: {', '.join(company_profile.common_tasks)}\n"

        return base_prompt

    @staticmethod
    def _extract_data_with_structure(
        image_path: str,
        structure_result: Dict,
        template: Optional[SheetTemplate] = None,
        company_profile: Optional[CompanyLearningProfile] = None
    ) -> Dict:
        """Stage 2: Extract data using discovered structure."""
        # Import OpenAIService here to avoid circular imports
        from .services import OpenAIService

        # Build data extraction prompt using structure
        data_prompt = MultiStageExtractor._build_data_extraction_prompt(
            structure_result, template, company_profile
        )

        try:
            # Extract data using enhanced prompt
            data_result = OpenAIService.extract_crew_sheet_data_with_prompt(
                image_path, data_prompt
            )

            if data_result.get('valid', False):
                # Enhance data with structure knowledge
                data_result = MultiStageExtractor._align_data_with_structure(
                    data_result, structure_result
                )

            return data_result

        except Exception as e:
            logger.error(f"Data extraction failed: {str(e)}")
            return {
                'valid': False,
                'error_message': f'Data extraction failed: {str(e)}'
            }

    @staticmethod
    def _build_data_extraction_prompt(
        structure_result: Dict,
        template: Optional[SheetTemplate] = None,
        company_profile: Optional[CompanyLearningProfile] = None
    ) -> str:
        """Build data extraction prompt based on structure analysis."""

        # Get structure information
        header_structure = structure_result.get('header_structure', {})
        content_sections = structure_result.get('content_sections', {})

        base_prompt = """You are an expert at extracting data from crew sheets. 

BASED ON THE STRUCTURE ANALYSIS, EXTRACT ALL DATA FROM THIS CREW SHEET.

STRUCTURE CONTEXT:
"""

        # Add structure context
        if header_structure:
            base_prompt += f"Header Structure: {json.dumps(header_structure, indent=2)}\n"

        if content_sections:
            base_prompt += f"Content Sections: {json.dumps(content_sections, indent=2)}\n"

        base_prompt += """
EXTRACTION RULES:
1. Use the EXACT header names identified in the structure analysis
2. Extract data for each employee row
3. Preserve hierarchical relationships in column names
4. Include all metadata (date, supervisor, notes, etc.)

EXPECTED OUTPUT FORMAT:
{
  "date": "extracted_date",
  "valid": true,
  "confidence_score": 0.85,
  "metadata": {
    "supervisor": "name_if_found",
    "sheet_title": "title_if_present",
    "total_hours": "calculated_or_found",
    "employee_count": number_of_employees
  },
  "employees": [
    {
      "name": "Employee Name",
      // ... all other fields based on structure
    }
  ],
  "table_headers": ["EMPLOYEE_NAME", "field1", "field2", ...]
}"""

        # Add template-specific instructions
        if template:
            base_prompt += f"\n\nTEMPLATE GUIDANCE:\n"
            base_prompt += f"Template type: {template.get_template_type_display()}\n"
            if template.expected_fields:
                base_prompt += f"Expected fields: {', '.join(template.expected_fields)}\n"

        # Add company-specific patterns
        if company_profile:
            base_prompt += f"\n\nCOMPANY PATTERNS:\n"
            if company_profile.common_cost_centers:
                base_prompt += f"Known cost centers: {', '.join(company_profile.common_cost_centers)}\n"
            if company_profile.common_tasks:
                base_prompt += f"Known tasks: {', '.join(company_profile.common_tasks)}\n"

        return base_prompt

    @staticmethod
    def _cross_validate_and_enhance(
        structure_result: Dict,
        data_result: Dict,
        template: Optional[SheetTemplate] = None,
        company_profile: Optional[CompanyLearningProfile] = None
    ) -> Dict:
        """Stage 3: Cross-validate results and enhance accuracy."""

        # Start with data result as base
        final_result = data_result.copy()

        # Cross-validate structure vs data
        validation_issues = []
        confidence_adjustments = 0.0

        # Check if extracted headers match structure
        extracted_headers = data_result.get('table_headers', [])
        expected_sections = structure_result.get('content_sections', {})

        for section_name, section_info in expected_sections.items():
            if section_info.get('present', False):
                expected_columns = section_info.get('columns', [])
                missing_columns = [
                    col for col in expected_columns if col not in extracted_headers]

                if missing_columns:
                    validation_issues.append(
                        f"Missing expected columns from {section_name}: {missing_columns}")
                    confidence_adjustments -= 0.05 * len(missing_columns)

        # Check data consistency
        employees = data_result.get('employees', [])
        if employees:
            # Validate each employee has expected fields
            first_employee_fields = set(employees[0].keys())
            header_fields = set(extracted_headers)

            # Check for missing fields
            missing_in_data = header_fields - first_employee_fields
            if missing_in_data:
                validation_issues.append(
                    f"Headers defined but missing in data: {list(missing_in_data)}")
                confidence_adjustments -= 0.03 * len(missing_in_data)

            # Check for extra fields
            extra_in_data = first_employee_fields - header_fields
            if extra_in_data and 'name' not in extra_in_data:  # 'name' is expected
                validation_issues.append(
                    f"Data fields not in headers: {list(extra_in_data)}")

        # Apply confidence adjustments
        original_confidence = final_result.get('confidence_score', 0.8)
        adjusted_confidence = max(
            0.1, original_confidence + confidence_adjustments)
        final_result['confidence_score'] = adjusted_confidence

        # Add validation metadata
        final_result['validation'] = {
            'cross_validation_performed': True,
            'validation_issues': validation_issues,
            'confidence_adjustment': confidence_adjustments,
            'original_confidence': original_confidence,
            'structure_data_alignment': len(validation_issues) == 0
        }

        # Enhance with template knowledge if available
        if template:
            final_result = MultiStageExtractor._enhance_with_template_knowledge(
                final_result, template
            )

        # Enhance with company patterns if available
        if company_profile:
            final_result = MultiStageExtractor._enhance_with_company_patterns(
                final_result, company_profile
            )

        return final_result

    @staticmethod
    def _enhance_structure_with_template(
        structure_result: Dict,
        template: SheetTemplate
    ) -> Dict:
        """Enhance structure analysis with template knowledge."""

        if template.header_structure:
            # Merge template header structure with discovered structure
            discovered_headers = structure_result.get('header_structure', {})
            template_headers = template.header_structure

            # Combine known patterns
            enhanced_structure = discovered_headers.copy()
            enhanced_structure['template_patterns'] = template_headers

            structure_result['header_structure'] = enhanced_structure

        return structure_result

    @staticmethod
    def _validate_structure_analysis(structure_result: Dict) -> Dict:
        """Validate that structure analysis makes sense."""

        if not structure_result.get('valid', False):
            return structure_result

        issues = []

        # Check basic layout validity
        layout = structure_result.get('layout', {})
        if layout.get('header_rows', 0) < 1:
            issues.append("No header rows detected")

        if layout.get('data_rows', 0) < 1:
            issues.append("No data rows detected")

        if layout.get('column_count', 0) < 2:
            issues.append("Too few columns detected")

        # Check content sections
        content_sections = structure_result.get('content_sections', {})
        if not content_sections.get('employee_info', {}).get('present', False):
            issues.append("No employee information section detected")

        # Adjust confidence based on issues
        if issues:
            original_confidence = structure_result.get('confidence_score', 0.8)
            adjusted_confidence = max(
                0.3, original_confidence - (0.1 * len(issues)))
            structure_result['confidence_score'] = adjusted_confidence
            structure_result['validation_issues'] = issues

        return structure_result

    @staticmethod
    def _align_data_with_structure(data_result: Dict, structure_result: Dict) -> Dict:
        """Align extracted data with discovered structure."""

        # Get expected structure
        expected_headers = []
        content_sections = structure_result.get('content_sections', {})

        for section_info in content_sections.values():
            if section_info.get('present', False):
                expected_headers.extend(section_info.get('columns', []))

        # Ensure extracted headers align with expected structure
        extracted_headers = data_result.get('table_headers', [])

        # Add missing headers that were expected
        for expected_header in expected_headers:
            if expected_header not in extracted_headers:
                extracted_headers.append(expected_header)

        data_result['table_headers'] = extracted_headers

        # Ensure employee data has all expected fields
        employees = data_result.get('employees', [])
        for employee in employees:
            for header in extracted_headers:
                if header not in employee:
                    employee[header] = ''  # Add missing field with empty value

        return data_result

    @staticmethod
    def _enhance_with_template_knowledge(result: Dict, template: SheetTemplate) -> Dict:
        """Enhance result using template knowledge."""

        # Add template metadata
        result.setdefault('template_enhancement', {})
        result['template_enhancement']['template_used'] = {
            'id': str(template.id),
            'name': template.name,
            'type': template.template_type,
            'success_rate': template.success_rate
        }

        # Validate against expected fields
        expected_fields = set(template.expected_fields or [])
        extracted_headers = set(result.get('table_headers', []))

        missing_expected = expected_fields - extracted_headers
        if missing_expected:
            result['template_enhancement']['missing_expected_fields'] = list(
                missing_expected)
            # Slightly reduce confidence
            current_confidence = result.get('confidence_score', 0.8)
            result['confidence_score'] = max(
                0.1, current_confidence - (0.02 * len(missing_expected)))

        return result

    @staticmethod
    def _enhance_with_company_patterns(result: Dict, company_profile: CompanyLearningProfile) -> Dict:
        """Enhance result using company learning patterns."""

        result.setdefault('company_enhancement', {})
        result['company_enhancement']['company_profile_used'] = company_profile.company_name

        # Validate cost centers
        if company_profile.common_cost_centers:
            extracted_centers = MultiStageExtractor._extract_cost_centers_from_result(
                result)
            unknown_centers = extracted_centers - \
                set(company_profile.common_cost_centers)

            if unknown_centers:
                result['company_enhancement']['unknown_cost_centers'] = list(
                    unknown_centers)

        # Validate tasks
        if company_profile.common_tasks:
            extracted_tasks = MultiStageExtractor._extract_tasks_from_result(
                result)
            unknown_tasks = extracted_tasks - set(company_profile.common_tasks)

            if unknown_tasks:
                result['company_enhancement']['unknown_tasks'] = list(
                    unknown_tasks)

        return result

    @staticmethod
    def _extract_cost_centers_from_result(result: Dict) -> set:
        """Extract cost centers mentioned in the result."""
        cost_centers = set()

        headers = result.get('table_headers', [])
        for header in headers:
            # Look for cost center patterns in headers (e.g., "KW13_TASK_HRS")
            parts = header.split('_')
            if len(parts) >= 2 and parts[0].isalnum():
                cost_centers.add(parts[0])

        return cost_centers

    @staticmethod
    def _extract_tasks_from_result(result: Dict) -> set:
        """Extract tasks mentioned in the result."""
        tasks = set()

        headers = result.get('table_headers', [])
        for header in headers:
            # Look for task patterns in headers (e.g., "CENTER_TASK_HRS")
            parts = header.split('_')
            if len(parts) >= 3:
                tasks.add(parts[1])

        return tasks
