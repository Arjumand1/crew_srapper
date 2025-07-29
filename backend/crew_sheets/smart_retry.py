"""
Smart Retry Strategies for Better AI Extraction Results
Implements multiple extraction strategies with intelligent fallback mechanisms.
"""
import logging
import time
from typing import Dict, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass
from .image_processor import ImagePreprocessor, AdaptivePreprocessor
from .models import SheetTemplate, CompanyLearningProfile
from .analytics import QualityValidator

logger = logging.getLogger(__name__)


class RetryStrategy(Enum):
    """Available retry strategies."""
    TEMPLATE_GUIDED = "template_guided"
    HIGH_DETAIL = "high_detail"
    STRUCTURE_FIRST = "structure_first"
    CONSERVATIVE = "conservative"
    AGGRESSIVE = "aggressive"


@dataclass
class StrategyConfig:
    """Configuration for a retry strategy."""
    name: str
    description: str
    preprocess: bool
    use_template: bool
    use_multi_stage: bool
    temperature: float
    max_tokens: int
    confidence_threshold: float
    timeout: int
    priority: int  # Lower number = higher priority


class SmartRetryService:
    """Intelligent retry service with multiple extraction strategies."""

    # Define available strategies
    STRATEGIES = {
        RetryStrategy.TEMPLATE_GUIDED: StrategyConfig(
            name="template_guided",
            description="Use template guidance with standard processing",
            preprocess=True,
            use_template=True,
            use_multi_stage=True,
            temperature=0.1,
            max_tokens=4096,
            confidence_threshold=0.8,
            timeout=120,
            priority=1
        ),
        RetryStrategy.HIGH_DETAIL: StrategyConfig(
            name="high_detail",
            description="Maximum detail extraction with larger context",
            preprocess=True,
            use_template=False,
            use_multi_stage=True,
            temperature=0.0,
            max_tokens=6000,
            confidence_threshold=0.75,
            timeout=180,
            priority=2
        ),
        RetryStrategy.STRUCTURE_FIRST: StrategyConfig(
            name="structure_first",
            description="Focus on structure analysis before data extraction",
            preprocess=False,
            use_template=False,
            use_multi_stage=True,
            temperature=0.2,
            max_tokens=4096,
            confidence_threshold=0.7,
            timeout=150,
            priority=3
        ),
        RetryStrategy.CONSERVATIVE: StrategyConfig(
            name="conservative",
            description="Conservative approach with basic prompting",
            preprocess=True,
            use_template=True,
            use_multi_stage=False,
            temperature=0.0,
            max_tokens=3000,
            confidence_threshold=0.6,
            timeout=90,
            priority=4
        ),
        RetryStrategy.AGGRESSIVE: StrategyConfig(
            name="aggressive",
            description="Aggressive preprocessing and high-temperature extraction",
            preprocess=True,
            use_template=False,
            use_multi_stage=False,
            temperature=0.3,
            max_tokens=4096,
            confidence_threshold=0.5,
            timeout=120,
            priority=5
        )
    }

    @staticmethod
    def extract_with_smart_retry(
        crew_sheet,
        template_id: Optional[str] = None,
        max_strategies: int = 3,
        min_confidence: float = 0.7
    ) -> Dict:
        """
        Extract using smart retry with multiple strategies.

        Args:
            crew_sheet: CrewSheet model instance
            template_id: Optional template ID for guidance
            max_strategies: Maximum number of strategies to try
            min_confidence: Minimum acceptable confidence score

        Returns:
            Best extraction result with metadata about attempts
        """
        logger.info(
            f"Starting smart retry extraction for crew sheet: {crew_sheet.id}")

        # Get template and company profile if available
        template = None
        company_profile = None

        if template_id:
            try:
                template = SheetTemplate.objects.get(
                    id=template_id, user=crew_sheet.user)
            except SheetTemplate.DoesNotExist:
                logger.warning(f"Template {template_id} not found")

        try:
            company_profile = CompanyLearningProfile.objects.get(
                user=crew_sheet.user)
        except CompanyLearningProfile.DoesNotExist:
            pass

        # Assess image quality to inform strategy selection
        image_quality = ImagePreprocessor.assess_image_quality(
            crew_sheet.image.path)

        # Select strategies based on context
        selected_strategies = SmartRetryService._select_strategies(
            image_quality, template, max_strategies
        )

        best_result = None
        best_confidence = 0.0
        attempt_history = []

        for strategy_enum in selected_strategies:
            strategy = SmartRetryService.STRATEGIES[strategy_enum]

            logger.info(f"Attempting strategy: {strategy.name}")
            start_time = time.time()

            try:
                # Execute strategy
                result = SmartRetryService._execute_strategy(
                    crew_sheet, strategy, template, company_profile
                )

                # Record attempt
                attempt_duration = time.time() - start_time
                attempt_info = {
                    'strategy': strategy.name,
                    'duration_seconds': round(attempt_duration, 2),
                    'success': result.get('valid', False),
                    'confidence_score': result.get('confidence_score', 0.0),
                    'error': result.get('error_message') if not result.get('valid') else None
                }
                attempt_history.append(attempt_info)

                # Check if this result is better
                current_confidence = result.get('confidence_score', 0.0)
                if result.get('valid', False) and current_confidence > best_confidence:
                    best_result = result
                    best_confidence = current_confidence

                    logger.info(
                        f"Strategy {strategy.name} achieved confidence: {current_confidence:.3f}")

                    # If we achieve high confidence, stop trying
                    if current_confidence >= min_confidence:
                        logger.info(
                            f"Target confidence {min_confidence} achieved, stopping retry")
                        break

            except Exception as e:
                logger.error(
                    f"Strategy {strategy.name} failed with error: {str(e)}")
                attempt_history.append({
                    'strategy': strategy.name,
                    'duration_seconds': round(time.time() - start_time, 2),
                    'success': False,
                    'confidence_score': 0.0,
                    'error': str(e)
                })
                continue

        # Prepare final result
        if best_result:
            # Add retry metadata
            best_result['retry_metadata'] = {
                'strategies_attempted': len(attempt_history),
                'successful_attempts': sum(1 for a in attempt_history if a['success']),
                'best_strategy': next(
                    (a['strategy'] for a in attempt_history
                     if a['confidence_score'] == best_confidence),
                    'unknown'
                ),
                'attempt_history': attempt_history,
                'image_quality_score': image_quality.get('overall_quality', 0.0),
                'total_processing_time': sum(a['duration_seconds'] for a in attempt_history)
            }

            logger.info(
                f"Smart retry completed. Best confidence: {best_confidence:.3f}")
            return best_result
        else:
            # All strategies failed
            logger.error("All retry strategies failed")
            return {
                'valid': False,
                'error_message': 'All retry strategies failed',
                'retry_metadata': {
                    'strategies_attempted': len(attempt_history),
                    'successful_attempts': 0,
                    'attempt_history': attempt_history,
                    'image_quality_score': image_quality.get('overall_quality', 0.0),
                    'total_processing_time': sum(a['duration_seconds'] for a in attempt_history)
                }
            }

    @staticmethod
    def _select_strategies(
        image_quality: Dict,
        template: Optional[SheetTemplate],
        max_strategies: int
    ) -> List[RetryStrategy]:
        """Select best strategies based on context."""

        strategies = []
        quality_score = image_quality.get('overall_quality', 0.5)

        # Always try template-guided first if template available
        if template:
            strategies.append(RetryStrategy.TEMPLATE_GUIDED)

        # For poor quality images, prioritize preprocessing strategies
        if quality_score < 0.4:
            strategies.extend([
                RetryStrategy.AGGRESSIVE,
                RetryStrategy.HIGH_DETAIL,
                RetryStrategy.STRUCTURE_FIRST
            ])
        elif quality_score < 0.7:
            strategies.extend([
                RetryStrategy.HIGH_DETAIL,
                RetryStrategy.STRUCTURE_FIRST,
                RetryStrategy.CONSERVATIVE
            ])
        else:
            # Good quality image - use standard approaches
            strategies.extend([
                RetryStrategy.STRUCTURE_FIRST,
                RetryStrategy.HIGH_DETAIL,
                RetryStrategy.CONSERVATIVE
            ])

        # Remove duplicates while preserving order
        seen = set()
        unique_strategies = []
        for strategy in strategies:
            if strategy not in seen:
                seen.add(strategy)
                unique_strategies.append(strategy)

        # Limit to max_strategies
        return unique_strategies[:max_strategies]

    @staticmethod
    def _execute_strategy(
        crew_sheet,
        strategy: StrategyConfig,
        template: Optional[SheetTemplate],
        company_profile: Optional[CompanyLearningProfile]
    ) -> Dict:
        """Execute a specific extraction strategy."""

        image_path = crew_sheet.image.path

        # Apply preprocessing if required
        processed_image_path = image_path
        if strategy.preprocess:
            if strategy.name == "aggressive":
                # Use aggressive preprocessing
                processed_image_path = ImagePreprocessor.optimize_for_ocr(
                    image_path, aggressive=True)
            else:
                # Use adaptive preprocessing
                processed_image_path = AdaptivePreprocessor.preprocess_adaptive(
                    image_path)

        # Choose extraction method
        if strategy.use_multi_stage:
            # Use multi-stage extraction
            from .multi_stage_extractor import MultiStageExtractor

            return MultiStageExtractor.extract_with_stages(
                processed_image_path,
                template if strategy.use_template else None,
                company_profile,
                use_preprocessing=False  # Already preprocessed above
            )
        else:
            # Use single-stage extraction with custom parameters
            return SmartRetryService._single_stage_extraction(
                processed_image_path,
                strategy,
                template if strategy.use_template else None,
                company_profile
            )

    @staticmethod
    def _single_stage_extraction(
        image_path: str,
        strategy: StrategyConfig,
        template: Optional[SheetTemplate],
        company_profile: Optional[CompanyLearningProfile]
    ) -> Dict:
        """Perform single-stage extraction with strategy parameters."""

        # Build prompt based on strategy
        if strategy.name == "conservative":
            prompt = SmartRetryService._build_conservative_prompt(
                template, company_profile)
        elif strategy.name == "aggressive":
            prompt = SmartRetryService._build_aggressive_prompt(
                template, company_profile)
        else:
            prompt = SmartRetryService._build_standard_prompt(
                template, company_profile)

        try:
            from .services import OpenAIService

            # Get OpenAI client
            client = OpenAIService.get_client()

            # Read and encode image
            import base64
            with open(image_path, "rb") as image_file:
                base64_image = base64.b64encode(
                    image_file.read()).decode('utf-8')

            # Prepare messages
            messages = [
                {
                    "role": "system",
                    "content": prompt
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Extract all data from this crew sheet image as structured JSON."
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

            # Make API call with strategy parameters
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                max_tokens=strategy.max_tokens,
                temperature=strategy.temperature,
                response_format={"type": "json_object"},
                timeout=strategy.timeout
            )

            # Parse response
            import json
            content = response.choices[0].message.content
            result = json.loads(content)

            # Add strategy metadata
            result['extraction_strategy'] = strategy.name
            result['strategy_parameters'] = {
                'temperature': strategy.temperature,
                'max_tokens': strategy.max_tokens,
                'timeout': strategy.timeout
            }

            # Validate result
            if result.get('valid', False):
                confidence, issues = QualityValidator.validate_extraction(
                    result)
                result['confidence_score'] = confidence
                if issues:
                    result['quality_issues'] = issues

            return result

        except Exception as e:
            logger.error(f"Single-stage extraction failed: {str(e)}")
            return {
                'valid': False,
                'error_message': f'Extraction failed: {str(e)}',
                'extraction_strategy': strategy.name
            }

    @staticmethod
    def _build_conservative_prompt(
        template: Optional[SheetTemplate],
        company_profile: Optional[CompanyLearningProfile]
    ) -> str:
        """Build conservative extraction prompt."""

        prompt = """You are an expert at extracting data from crew sheets. Extract only clearly visible data.

CONSERVATIVE EXTRACTION RULES:
1. Only extract data you are 100% confident about
2. Use empty string for unclear or missing values
3. Preserve exact formatting of visible text
4. Do not guess or interpolate missing information

OUTPUT FORMAT:
{
  "valid": true,
  "confidence_score": 0.95,
  "date": "found_date_or_empty",
  "employees": [
    {
      "name": "Clearly visible name",
      "field1": "only_if_clearly_visible",
      "field2": ""
    }
  ],
  "table_headers": ["header1", "header2"],
  "metadata": {
    "extraction_notes": "Any uncertainties noted here"
  }
}"""

        if template:
            prompt += f"\n\nTEMPLATE REFERENCE:\nExpected fields: {', '.join(template.expected_fields or [])}"

        if company_profile and company_profile.common_cost_centers:
            prompt += f"\n\nKNOWN COST CENTERS: {', '.join(company_profile.common_cost_centers)}"

        return prompt

    @staticmethod
    def _build_aggressive_prompt(
        template: Optional[SheetTemplate],
        company_profile: Optional[CompanyLearningProfile]
    ) -> str:
        """Build aggressive extraction prompt."""

        prompt = """You are an expert at extracting data from crew sheets. Use all available context to extract maximum data.

AGGRESSIVE EXTRACTION RULES:
1. Extract all visible data, even if partially obscured
2. Use context clues to infer missing information when reasonable
3. Apply pattern recognition to fill gaps
4. Cross-reference with known patterns and templates

ADVANCED TECHNIQUES:
- Look for partial text and complete based on context
- Use mathematical relationships (totals, calculations)
- Apply time sequence logic for missing time entries
- Use employee name patterns to correct OCR errors

OUTPUT FORMAT:
{
  "valid": true,
  "confidence_score": 0.75,
  "date": "extracted_or_inferred_date",
  "employees": [
    {
      "name": "Name with OCR corrections if needed",
      "field1": "extracted_or_reasonably_inferred",
      "field2": "value_with_pattern_matching"
    }
  ],
  "table_headers": ["comprehensive_header_list"],
  "inference_notes": ["List of inferences made"],
  "metadata": {
    "extraction_confidence_by_field": {
      "field1": 0.9,
      "field2": 0.6
    }
  }
}"""

        if template:
            prompt += f"\n\nTEMPLATE CONTEXT:\n"
            prompt += f"Type: {template.get_template_type_display()}\n"
            prompt += f"Expected fields: {', '.join(template.expected_fields or [])}\n"
            if template.header_structure:
                prompt += f"Header patterns: {template.header_structure}\n"

        if company_profile:
            if company_profile.common_cost_centers:
                prompt += f"\n\nCOST CENTER PATTERNS: {', '.join(company_profile.common_cost_centers)}"
            if company_profile.common_tasks:
                prompt += f"\nTASK PATTERNS: {', '.join(company_profile.common_tasks)}"

        return prompt

    @staticmethod
    def _build_standard_prompt(
        template: Optional[SheetTemplate],
        company_profile: Optional[CompanyLearningProfile]
    ) -> str:
        """Build standard extraction prompt."""

        prompt = """You are an expert at extracting data from crew sheets.

EXTRACTION GUIDELINES:
1. Extract all clearly visible data accurately
2. Maintain data structure and relationships
3. Use consistent formatting for similar fields
4. Preserve hierarchical header relationships

OUTPUT FORMAT:
{
  "valid": true,
  "confidence_score": 0.85,
  "date": "sheet_date",
  "employees": [
    {
      "name": "Employee Name",
      "additional_fields": "based_on_sheet_structure"
    }
  ],
  "table_headers": ["complete_header_list"],
  "metadata": {
    "supervisor": "if_found",
    "total_hours": "if_calculated",
    "employee_count": number
  }
}"""

        # Add context if available
        context_parts = []

        if template:
            context_parts.append(
                f"Template type: {template.get_template_type_display()}")
            if template.expected_fields:
                context_parts.append(
                    f"Expected fields: {', '.join(template.expected_fields)}")

        if company_profile:
            if company_profile.common_cost_centers:
                context_parts.append(
                    f"Known cost centers: {', '.join(company_profile.common_cost_centers)}")
            if company_profile.common_tasks:
                context_parts.append(
                    f"Known tasks: {', '.join(company_profile.common_tasks)}")

        if context_parts:
            prompt += f"\n\nCONTEXT:\n" + \
                "\n".join(f"- {part}" for part in context_parts)

        return prompt


class RetryAnalytics:
    """Analytics for retry strategy performance."""

    @staticmethod
    def analyze_strategy_performance(attempt_history: List[Dict]) -> Dict:
        """Analyze performance of different strategies."""

        if not attempt_history:
            return {}

        successful_attempts = [a for a in attempt_history if a['success']]

        analytics = {
            'total_attempts': len(attempt_history),
            'successful_attempts': len(successful_attempts),
            'success_rate': len(successful_attempts) / len(attempt_history),
            'average_duration': sum(a['duration_seconds'] for a in attempt_history) / len(attempt_history),
            'best_confidence': max((a['confidence_score'] for a in successful_attempts), default=0.0),
            'strategy_performance': {}
        }

        # Analyze by strategy
        strategy_stats = {}
        for attempt in attempt_history:
            strategy = attempt['strategy']
            if strategy not in strategy_stats:
                strategy_stats[strategy] = {
                    'attempts': 0,
                    'successes': 0,
                    'total_duration': 0,
                    'best_confidence': 0.0
                }

            stats = strategy_stats[strategy]
            stats['attempts'] += 1
            stats['total_duration'] += attempt['duration_seconds']

            if attempt['success']:
                stats['successes'] += 1
                stats['best_confidence'] = max(
                    stats['best_confidence'], attempt['confidence_score'])

        # Calculate derived metrics
        for strategy, stats in strategy_stats.items():
            analytics['strategy_performance'][strategy] = {
                'success_rate': stats['successes'] / stats['attempts'],
                'average_duration': stats['total_duration'] / stats['attempts'],
                'best_confidence': stats['best_confidence']
            }

        return analytics
