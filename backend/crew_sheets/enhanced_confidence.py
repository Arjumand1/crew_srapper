"""
Enhanced Confidence Scoring System
Provides more accurate quality assessment for crew sheet extractions
"""
import re
import logging
import numpy as np
from typing import Dict, Optional, Any
from datetime import timedelta
from django.utils import timezone
from .models import CrewSheet, UserEdit, CompanyLearningProfile, SheetTemplate

logger = logging.getLogger(__name__)


class EnhancedConfidenceScorer:
    """Advanced confidence scoring with multiple quality indicators."""

    # Weight configuration for different confidence factors
    CONFIDENCE_WEIGHTS = {
        'structure_score': 0.25,        # Header structure quality
        'data_consistency': 0.20,       # Internal data consistency
        'template_match': 0.15,         # Template matching quality
        'field_accuracy': 0.20,         # Individual field accuracy
        'historical_performance': 0.10,  # Historical accuracy for similar sheets
        'extraction_metadata': 0.10     # Technical extraction quality
    }

    @staticmethod
    def calculate_enhanced_confidence(
        extraction_result: Dict,
        crew_sheet: Optional['CrewSheet'] = None,
        template: Optional['SheetTemplate'] = None,
        company_profile: Optional['CompanyLearningProfile'] = None
    ) -> Dict[str, Any]:
        """
        Calculate enhanced confidence score with detailed breakdown.

        Returns:
            Dict with confidence scores and detailed analysis
        """
        logger.info("Calculating enhanced confidence score")

        confidence_breakdown = {
            'structure_score': 0.0,
            'data_consistency': 0.0,
            'template_match': 0.0,
            'field_accuracy': 0.0,
            'historical_performance': 0.0,
            'extraction_metadata': 0.0
        }

        quality_indicators = {
            'red_flags': [],       # Critical issues
            'warnings': [],        # Minor concerns
            'strengths': [],       # Quality indicators
            'recommendations': []  # Improvement suggestions
        }

        # 1. Structure Quality Score
        confidence_breakdown['structure_score'] = EnhancedConfidenceScorer._analyze_structure_quality(
            extraction_result, quality_indicators
        )

        # 2. Data Consistency Score
        confidence_breakdown['data_consistency'] = EnhancedConfidenceScorer._analyze_data_consistency(
            extraction_result, quality_indicators
        )

        # 3. Template Match Score
        if template:
            confidence_breakdown['template_match'] = EnhancedConfidenceScorer._analyze_template_match(
                extraction_result, template, quality_indicators
            )
        else:
            # Neutral when no template
            confidence_breakdown['template_match'] = 0.5

        # 4. Field Accuracy Score
        confidence_breakdown['field_accuracy'] = EnhancedConfidenceScorer._analyze_field_accuracy(
            extraction_result, quality_indicators
        )

        # 5. Historical Performance Score
        if crew_sheet:
            confidence_breakdown['historical_performance'] = EnhancedConfidenceScorer._analyze_historical_performance(
                crew_sheet, extraction_result, quality_indicators
            )
        else:
            # Neutral when no history
            confidence_breakdown['historical_performance'] = 0.5

        # 6. Extraction Metadata Score
        confidence_breakdown['extraction_metadata'] = EnhancedConfidenceScorer._analyze_extraction_metadata(
            extraction_result, quality_indicators
        )

        # Calculate weighted overall confidence
        overall_confidence = sum(
            score * EnhancedConfidenceScorer.CONFIDENCE_WEIGHTS[factor]
            for factor, score in confidence_breakdown.items()
        )

        # Apply confidence adjustments based on quality indicators
        overall_confidence = EnhancedConfidenceScorer._apply_quality_adjustments(
            overall_confidence, quality_indicators
        )

        # Generate confidence level and recommendations
        confidence_level = EnhancedConfidenceScorer._determine_confidence_level(
            overall_confidence)

        return {
            'overall_confidence': round(overall_confidence, 3),
            'confidence_level': confidence_level,
            'confidence_breakdown': confidence_breakdown,
            'quality_indicators': quality_indicators,
            'needs_review': overall_confidence < 0.7,
            'review_priority': EnhancedConfidenceScorer._calculate_review_priority(
                overall_confidence, quality_indicators
            )
        }

    @staticmethod
    def _analyze_structure_quality(extraction_result: Dict, quality_indicators: Dict) -> float:
        """Analyze the quality of extracted structure."""
        score = 1.0

        employees = extraction_result.get('employees', [])
        headers = extraction_result.get('table_headers', [])

        # Check basic structure
        if not employees:
            quality_indicators['red_flags'].append(
                'No employee data extracted')
            return 0.0

        if not headers:
            quality_indicators['red_flags'].append(
                'No table headers extracted')
            return 0.0

        # Analyze header complexity and consistency
        hierarchical_headers = [
            h for h in headers if '_' in h and len(h.split('_')) >= 2]
        if hierarchical_headers:
            quality_indicators['strengths'].append(
                f'Detected {len(hierarchical_headers)} hierarchical headers')
            score += 0.1

        # Check for time tracking structure
        time_headers = [h for h in headers if any(keyword in h.upper()
                                                  for keyword in ['START', 'BREAK', 'LUNCH', 'END'])]
        if time_headers:
            quality_indicators['strengths'].append(
                f'Proper time tracking structure with {len(time_headers)} columns')
        else:
            quality_indicators['warnings'].append(
                'No time tracking columns detected')
            score -= 0.2

        # Check for job assignment structure
        job_headers = [h for h in headers if any(keyword in h.upper()
                                                 for keyword in ['HRS', 'HOURS', 'PCS', 'PIECE', 'WORK'])]
        if job_headers:
            quality_indicators['strengths'].append(
                f'Job assignment structure with {len(job_headers)} columns')
        else:
            quality_indicators['warnings'].append(
                'Limited job assignment structure')
            score -= 0.1

        # Check data completeness across employees
        if employees:
            first_employee_fields = set(employees[0].keys())
            header_fields = set(headers)

            missing_in_data = header_fields - first_employee_fields
            if missing_in_data:
                quality_indicators['warnings'].append(
                    f'Headers missing in data: {list(missing_in_data)[:3]}')
                score -= 0.1

            # Check field consistency across employees
            inconsistent_fields = 0
            for header in headers[:10]:  # Check first 10 headers
                values = [emp.get(header, '') for emp in employees]
                non_empty = [v for v in values if str(v).strip()]
                if len(non_empty) < len(employees) * 0.3:  # Less than 30% filled
                    inconsistent_fields += 1

            if inconsistent_fields > len(headers) * 0.5:
                quality_indicators['warnings'].append(
                    'Many columns have sparse data')
                score -= 0.2

        return max(0.0, min(1.0, score))

    @staticmethod
    def _analyze_data_consistency(extraction_result: Dict, quality_indicators: Dict) -> float:
        """Analyze internal data consistency."""
        score = 1.0

        employees = extraction_result.get('employees', [])
        if not employees:
            return 0.0

        # Time format consistency
        time_fields = [h for h in extraction_result.get('table_headers', [])
                       if any(keyword in h.upper() for keyword in ['START', 'BREAK', 'LUNCH', 'END'])]

        if time_fields:
            time_pattern = re.compile(r'^\d{1,2}:?\d{0,2}$|^✓$|^$')
            invalid_times = 0
            total_times = 0

            for employee in employees:
                for field in time_fields:
                    value = str(employee.get(field, '')).strip()
                    if value:
                        total_times += 1
                        if not time_pattern.match(value):
                            invalid_times += 1

            if total_times > 0:
                time_consistency = 1.0 - (invalid_times / total_times)
                if time_consistency < 0.8:
                    quality_indicators['warnings'].append(
                        f'Time format inconsistency: {invalid_times}/{total_times} invalid')
                    score -= 0.3
                else:
                    quality_indicators['strengths'].append(
                        f'Good time format consistency: {time_consistency:.1%}')

        # Numeric data consistency
        numeric_fields = [h for h in extraction_result.get('table_headers', [])
                          if any(keyword in h.upper() for keyword in ['HRS', 'HOURS', 'PCS', 'PIECE'])]

        if numeric_fields:
            invalid_numbers = 0
            total_numbers = 0

            for employee in employees:
                for field in numeric_fields:
                    value = str(employee.get(field, '')).strip()
                    if value and value != '✓':
                        total_numbers += 1
                        try:
                            float_val = float(value.replace(',', ''))
                            if float_val < 0 or float_val > 100:  # Reasonable bounds
                                invalid_numbers += 1
                        except ValueError:
                            invalid_numbers += 1

            if total_numbers > 0:
                numeric_consistency = 1.0 - (invalid_numbers / total_numbers)
                if numeric_consistency < 0.9:
                    quality_indicators['warnings'].append(
                        f'Numeric data inconsistency: {invalid_numbers}/{total_numbers} invalid')
                    score -= 0.2
                else:
                    quality_indicators['strengths'].append(
                        f'Good numeric data consistency: {numeric_consistency:.1%}')

        # Employee name consistency
        names = [emp.get('name', '').strip() for emp in employees]
        valid_names = [name for name in names if name and len(
            name) > 1 and ' ' in name]

        if names:
            name_consistency = len(valid_names) / len(names)
            if name_consistency < 0.8:
                quality_indicators['warnings'].append(
                    f'Employee name quality issues: {name_consistency:.1%} valid')
                score -= 0.2
            else:
                quality_indicators['strengths'].append(
                    f'Good employee name extraction: {name_consistency:.1%}')

        return max(0.0, min(1.0, score))

    @staticmethod
    def _analyze_template_match(
        extraction_result: Dict,
        template: 'SheetTemplate',
        quality_indicators: Dict
    ) -> float:
        """Analyze how well extraction matches the template."""
        score = 1.0

        extracted_headers = set(extraction_result.get('table_headers', []))
        expected_headers = set(template.expected_fields or [])

        if not expected_headers:
            return 0.5  # Neutral if template has no expected fields

        # Calculate header match percentage
        matched_headers = extracted_headers & expected_headers
        missing_headers = expected_headers - extracted_headers
        extra_headers = extracted_headers - expected_headers

        match_percentage = len(matched_headers) / \
            len(expected_headers) if expected_headers else 0

        if match_percentage > 0.8:
            quality_indicators['strengths'].append(
                f'Excellent template match: {match_percentage:.1%}')
        elif match_percentage > 0.6:
            quality_indicators['strengths'].append(
                f'Good template match: {match_percentage:.1%}')
        else:
            quality_indicators['warnings'].append(
                f'Poor template match: {match_percentage:.1%}')
            score -= 0.4

        if missing_headers:
            quality_indicators['warnings'].append(
                f'Missing expected fields: {list(missing_headers)[:3]}')
            score -= 0.2

        if extra_headers and len(extra_headers) > len(expected_headers) * 0.5:
            quality_indicators['warnings'].append(
                f'Many unexpected fields detected: {len(extra_headers)}')
            score -= 0.1

        # Check template success rate
        if template.success_rate < 0.7:
            quality_indicators['warnings'].append(
                f'Template has low success rate: {template.success_rate:.1%}')
            score -= 0.1

        return max(0.0, min(1.0, score))

    @staticmethod
    def _analyze_field_accuracy(extraction_result: Dict, quality_indicators: Dict) -> float:
        """Analyze individual field accuracy indicators."""
        score = 1.0

        employees = extraction_result.get('employees', [])
        if not employees:
            return 0.0

        # Analyze data density (how many fields are filled)
        total_fields = 0
        filled_fields = 0
        placeholder_fields = 0

        for employee in employees:
            for field, value in employee.items():
                if field != 'name':  # Skip name field
                    total_fields += 1
                    str_value = str(value).strip()
                    if str_value:
                        filled_fields += 1
                        if str_value == '✓':
                            placeholder_fields += 1

        if total_fields > 0:
            fill_rate = filled_fields / total_fields
            placeholder_rate = placeholder_fields / \
                filled_fields if filled_fields > 0 else 0

            if fill_rate > 0.7:
                quality_indicators['strengths'].append(
                    f'High data density: {fill_rate:.1%}')
            elif fill_rate < 0.3:
                quality_indicators['warnings'].append(
                    f'Low data density: {fill_rate:.1%}')
                score -= 0.3

            if placeholder_rate > 0.8:
                quality_indicators['warnings'].append(
                    f'High placeholder rate: {placeholder_rate:.1%}')
                score -= 0.2

        # Check for obvious OCR errors
        ocr_error_patterns = [
            r'[0O]{3,}',  # Multiple zeros/O's
            r'[Il1]{3,}',  # Multiple I/l/1's
            r'[^\w\s:✓\-\.]+',  # Unusual characters
        ]

        error_count = 0
        total_values = 0

        for employee in employees:
            for field, value in employee.items():
                str_value = str(value).strip()
                if str_value and str_value != '✓':
                    total_values += 1
                    for pattern in ocr_error_patterns:
                        if re.search(pattern, str_value):
                            error_count += 1
                            break

        if total_values > 0:
            error_rate = error_count / total_values
            if error_rate > 0.1:
                quality_indicators['warnings'].append(
                    f'Potential OCR errors detected: {error_rate:.1%}')
                score -= 0.2

        return max(0.0, min(1.0, score))

    @staticmethod
    def _analyze_historical_performance(
        crew_sheet: 'CrewSheet',
        extraction_result: Dict,
        quality_indicators: Dict
    ) -> float:
        """Analyze performance based on historical data."""
        score = 0.5  # Default neutral score

        try:
            # Get user's recent sheets
            recent_sheets = CrewSheet.objects.filter(
                user=crew_sheet.user,
                date_processed__gte=timezone.now() - timedelta(days=30),
                status='completed'
            ).exclude(id=crew_sheet.id)[:10]

            if not recent_sheets:
                return score

            # Calculate average confidence for recent sheets
            confidences = [
                sheet.confidence_score for sheet in recent_sheets if sheet.confidence_score]
            if confidences:
                avg_confidence = sum(confidences) / len(confidences)

                if avg_confidence > 0.8:
                    quality_indicators['strengths'].append(
                        f'User has high extraction success rate: {avg_confidence:.1%}')
                    score = 0.8
                elif avg_confidence < 0.6:
                    quality_indicators['warnings'].append(
                        f'User has low extraction success rate: {avg_confidence:.1%}')
                    score = 0.3
                else:
                    score = avg_confidence

            # Check edit patterns
            recent_edits = UserEdit.objects.filter(
                session__crew_sheet__user=crew_sheet.user,
                timestamp__gte=timezone.now() - timedelta(days=30)
            ).count()

            recent_sheet_count = len(recent_sheets)
            if recent_sheet_count > 0:
                edit_ratio = recent_edits / recent_sheet_count
                if edit_ratio > 10:  # High edit ratio
                    quality_indicators['warnings'].append(
                        f'User typically makes many edits: {edit_ratio:.1f} per sheet')
                    score -= 0.1
                elif edit_ratio < 2:  # Low edit ratio
                    quality_indicators['strengths'].append(
                        f'User typically needs few edits: {edit_ratio:.1f} per sheet')
                    score += 0.1

        except Exception as e:
            logger.warning(f"Error analyzing historical performance: {str(e)}")

        return max(0.0, min(1.0, score))

    @staticmethod
    def _analyze_extraction_metadata(extraction_result: Dict, quality_indicators: Dict) -> float:
        """Analyze technical extraction quality from metadata."""
        score = 0.8  # Default good score

        # Check for extraction strategy metadata
        if 'retry_metadata' in extraction_result:
            retry_meta = extraction_result['retry_metadata']
            strategies_attempted = retry_meta.get('strategies_attempted', 1)
            successful_attempts = retry_meta.get('successful_attempts', 1)

            if strategies_attempted > 1:
                if successful_attempts == strategies_attempted:
                    quality_indicators['strengths'].append(
                        f'All {strategies_attempted} retry strategies succeeded')
                    score += 0.1
                else:
                    quality_indicators['warnings'].append(
                        f'Required {strategies_attempted} strategies, {successful_attempts} succeeded')
                    score -= 0.1

        # Check for multi-stage metadata
        if 'extraction_metadata' in extraction_result:
            extraction_meta = extraction_result['extraction_metadata']
            stages_completed = extraction_meta.get('stages_completed', 1)

            if stages_completed >= 3:
                quality_indicators['strengths'].append(
                    'Used multi-stage extraction pipeline')
                score += 0.1

        # Check for validation issues
        if 'validation' in extraction_result:
            validation_info = extraction_result['validation']
            validation_issues = validation_info.get('validation_issues', [])

            if validation_issues:
                quality_indicators['warnings'].append(
                    f'Validation issues: {len(validation_issues)}')
                score -= 0.1 * len(validation_issues)

        return max(0.0, min(1.0, score))

    @staticmethod
    def _apply_quality_adjustments(base_confidence: float, quality_indicators: Dict) -> float:
        """Apply adjustments based on quality indicators."""
        adjusted_confidence = base_confidence

        red_flag_count = len(quality_indicators['red_flags'])
        warning_count = len(quality_indicators['warnings'])
        strength_count = len(quality_indicators['strengths'])

        # Apply penalties for red flags and warnings
        adjusted_confidence -= red_flag_count * 0.2
        adjusted_confidence -= warning_count * 0.05

        # Apply bonuses for strengths (capped)
        adjusted_confidence += min(strength_count * 0.02, 0.1)

        return max(0.0, min(1.0, adjusted_confidence))

    @staticmethod
    def _determine_confidence_level(confidence: float) -> str:
        """Determine confidence level category."""
        if confidence >= 0.9:
            return 'EXCELLENT'
        elif confidence >= 0.8:
            return 'HIGH'
        elif confidence >= 0.7:
            return 'GOOD'
        elif confidence >= 0.6:
            return 'MODERATE'
        elif confidence >= 0.4:
            return 'LOW'
        else:
            return 'POOR'

    @staticmethod
    def _calculate_review_priority(confidence: float, quality_indicators: Dict) -> str:
        """Calculate review priority level."""
        red_flags = len(quality_indicators['red_flags'])
        warnings = len(quality_indicators['warnings'])

        if red_flags > 0 or confidence < 0.5:
            return 'URGENT'
        elif warnings > 3 or confidence < 0.7:
            return 'HIGH'
        elif warnings > 1 or confidence < 0.8:
            return 'MEDIUM'
        else:
            return 'LOW'


class ConfidenceAnalytics:
    """Analytics for confidence scoring performance."""

    @staticmethod
    def analyze_confidence_accuracy(days_back: int = 30) -> Dict:
        """Analyze how accurate confidence scores are compared to user edits."""
        logger.info(f"Analyzing confidence accuracy for last {days_back} days")

        # Get recent sheets with confidence scores
        recent_sheets = CrewSheet.objects.filter(
            date_processed__gte=timezone.now() - timedelta(days=days_back),
            status='completed',
            confidence_score__isnull=False
        ).select_related('user')

        if not recent_sheets:
            return {'error': 'No recent sheets with confidence scores found'}

        # Analyze correlation between confidence and actual quality
        confidence_vs_quality = []

        for sheet in recent_sheets:
            # Calculate actual quality based on user edits
            edit_count = UserEdit.objects.filter(
                session__crew_sheet=sheet
            ).count()

            # Simple quality metric: fewer edits = higher quality
            total_fields = len(sheet.extracted_data.get(
                'table_headers', [])) * len(sheet.extracted_data.get('employees', []))
            actual_quality = max(
                0, 1 - (edit_count / max(total_fields, 1))) if total_fields > 0 else 0

            confidence_vs_quality.append({
                'predicted_confidence': sheet.confidence_score,
                'actual_quality': actual_quality,
                'edit_count': edit_count,
                'total_fields': total_fields
            })

        # Calculate correlation coefficient
        if len(confidence_vs_quality) > 1:
            predicted = [item['predicted_confidence']
                         for item in confidence_vs_quality]
            actual = [item['actual_quality'] for item in confidence_vs_quality]

            correlation = np.corrcoef(predicted, actual)[
                0, 1] if len(predicted) > 1 else 0
        else:
            correlation = 0

        return {
            'total_sheets_analyzed': len(confidence_vs_quality),
            'confidence_accuracy_correlation': round(correlation, 3),
            'average_predicted_confidence': round(np.mean([item['predicted_confidence'] for item in confidence_vs_quality]), 3),
            'average_actual_quality': round(np.mean([item['actual_quality'] for item in confidence_vs_quality]), 3),
            # Limit to first 20 for display
            'confidence_vs_quality_data': confidence_vs_quality[:20]
        }
