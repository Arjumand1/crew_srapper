"""
Real-time Learning System
Provides continuous improvement through real-time feedback and adaptation
"""
import logging
from typing import Dict, List, Optional, Any
from datetime import timedelta
from django.utils import timezone
from django.db.models import Avg
from django.core.cache import cache
from .models import (
    CrewSheet, UserEdit, FieldConfidence,
    CompanyLearningProfile
)

logger = logging.getLogger(__name__)


class RealTimeLearningEngine:
    """Real-time learning engine that adapts to user feedback immediately."""

    # Cache keys for real-time data
    CACHE_PREFIX = "rtl_"
    PATTERN_CACHE_TIMEOUT = 300  # 5 minutes
    FEEDBACK_CACHE_TIMEOUT = 60   # 1 minute

    @staticmethod
    def process_user_feedback(
        user_edit: 'UserEdit',
        immediate_update: bool = True
    ) -> Dict[str, Any]:
        """
        Process user feedback in real-time and update learning models.

        Args:
            user_edit: UserEdit instance representing user correction
            immediate_update: Whether to immediately update learning models

        Returns:
            Dictionary with learning updates and recommendations
        """
        logger.info(
            f"Processing real-time feedback for field: {user_edit.field_name}")

        feedback_result = {
            'feedback_processed': True,
            'learning_updates': [],
            'immediate_improvements': [],
            'pattern_discoveries': [],
            'recommendations': []
        }

        try:
            # 1. Immediate field-level learning
            field_learning = RealTimeLearningEngine._update_field_learning(
                user_edit)
            feedback_result['learning_updates'].append(field_learning)

            # 2. Pattern recognition and update
            pattern_updates = RealTimeLearningEngine._detect_and_update_patterns(
                user_edit)
            feedback_result['pattern_discoveries'].extend(pattern_updates)

            # 3. Template learning
            if user_edit.session.crew_sheet.template_used:
                template_learning = RealTimeLearningEngine._update_template_learning(
                    user_edit)
                feedback_result['learning_updates'].append(template_learning)

            # 4. Company-wide learning
            company_learning = RealTimeLearningEngine._update_company_learning(
                user_edit)
            feedback_result['learning_updates'].append(company_learning)

            # 5. Generate immediate improvements
            if immediate_update:
                improvements = RealTimeLearningEngine._generate_immediate_improvements(
                    user_edit)
                feedback_result['immediate_improvements'].extend(improvements)

            # 6. Cache insights for quick access
            RealTimeLearningEngine._cache_learning_insights(
                user_edit, feedback_result)

            # 7. Generate recommendations for future extractions
            recommendations = RealTimeLearningEngine._generate_recommendations(
                user_edit)
            feedback_result['recommendations'].extend(recommendations)

        except Exception as e:
            logger.error(f"Error processing real-time feedback: {str(e)}")
            feedback_result['error'] = str(e)

        return feedback_result

    @staticmethod
    def _update_field_learning(user_edit: 'UserEdit') -> Dict[str, Any]:
        """Update field-specific learning based on user correction."""
        field_name = user_edit.field_name
        original_value = user_edit.original_value
        corrected_value = user_edit.new_value

        learning_update = {
            'type': 'field_learning',
            'field_name': field_name,
            'correction_pattern': f"{original_value} → {corrected_value}",
            'confidence_adjustment': 0.0,
            'learning_insights': []
        }

        try:
            # Get or create field confidence record
            field_confidence, created = FieldConfidence.objects.get_or_create(
                crew_sheet=user_edit.session.crew_sheet,
                field_name=field_name,
                employee_index=user_edit.employee_index or 0,
                defaults={
                    'overall_confidence': 0.5,
                    'is_uncertain': True,
                    'needs_review': True
                }
            )

            # Adjust confidence based on correction
            if original_value != corrected_value:
                # Significant correction - reduce confidence
                adjustment = -0.2
                field_confidence.overall_confidence = max(
                    0.1, field_confidence.overall_confidence + adjustment)
                field_confidence.is_uncertain = True
                field_confidence.needs_review = True

                learning_update['confidence_adjustment'] = adjustment
                learning_update['learning_insights'].append(
                    f'Reduced confidence due to correction')
            else:
                # Minor correction - slight confidence boost
                adjustment = 0.05
                field_confidence.overall_confidence = min(
                    1.0, field_confidence.overall_confidence + adjustment)
                learning_update['confidence_adjustment'] = adjustment

            field_confidence.save()

            # Analyze correction pattern
            correction_type = RealTimeLearningEngine._classify_correction_type(
                original_value, corrected_value, field_name
            )
            learning_update['correction_type'] = correction_type
            learning_update['learning_insights'].append(
                f'Correction type: {correction_type}')

        except Exception as e:
            logger.warning(f"Field learning update failed: {str(e)}")
            learning_update['error'] = str(e)

        return learning_update

    @staticmethod
    def _classify_correction_type(
        original: str,
        corrected: str,
        field_name: str
    ) -> str:
        """Classify the type of correction made by the user."""

        # Time format corrections
        if any(keyword in field_name.upper() for keyword in ['START', 'BREAK', 'LUNCH', 'END']):
            if original == '✓' and ':' in corrected:
                return 'checkmark_to_time'
            elif ':' in original and ':' in corrected:
                return 'time_format_correction'
            elif original and not corrected:
                return 'time_deletion'
            else:
                return 'time_other'

        # Numeric corrections
        if any(keyword in field_name.upper() for keyword in ['HRS', 'HOURS', 'PCS', 'PIECE']):
            try:
                float(original)
                float(corrected)
                return 'numeric_adjustment'
            except ValueError:
                if original == '✓' and corrected.replace('.', '').isdigit():
                    return 'checkmark_to_numeric'
                else:
                    return 'numeric_format_correction'

        # Name corrections
        if 'NAME' in field_name.upper() or 'EMPLOYEE' in field_name.upper():
            return 'name_correction'

        # General corrections
        if len(original) > len(corrected):
            return 'value_truncation'
        elif len(corrected) > len(original):
            return 'value_expansion'
        elif original == '✓':
            return 'checkmark_replacement'
        else:
            return 'value_replacement'

    @staticmethod
    def _detect_and_update_patterns(user_edit: 'UserEdit') -> List[Dict[str, Any]]:
        """Detect patterns in user corrections and update learning models."""
        patterns = []

        try:
            user = user_edit.session.crew_sheet.user
            field_name = user_edit.field_name

            # Look for recent corrections in the same field
            recent_edits = UserEdit.objects.filter(
                session__crew_sheet__user=user,
                field_name=field_name,
                timestamp__gte=timezone.now() - timedelta(days=7)
            ).order_by('-timestamp')[:10]

            if len(recent_edits) >= 3:
                # Analyze correction patterns
                correction_patterns = {}
                for edit in recent_edits:
                    pattern = f"{edit.original_value} → {edit.new_value}"
                    correction_patterns[pattern] = correction_patterns.get(
                        pattern, 0) + 1

                # Find frequent patterns
                frequent_patterns = [
                    (k, v) for k, v in correction_patterns.items() if v >= 2]

                if frequent_patterns:
                    pattern_discovery = {
                        'type': 'frequent_correction_pattern',
                        'field_name': field_name,
                        'patterns': frequent_patterns,
                        'confidence': min(1.0, len(frequent_patterns) / len(recent_edits)),
                        'recommendation': f'Consider improving extraction for {field_name}'
                    }
                    patterns.append(pattern_discovery)

                    # Cache this pattern for immediate use
                    cache_key = f"{RealTimeLearningEngine.CACHE_PREFIX}pattern_{user.id}_{field_name}"
                    cache.set(cache_key, pattern_discovery,
                              RealTimeLearningEngine.PATTERN_CACHE_TIMEOUT)

            # Detect cross-field patterns
            cross_field_patterns = RealTimeLearningEngine._detect_cross_field_patterns(
                user_edit)
            patterns.extend(cross_field_patterns)

        except Exception as e:
            logger.warning(f"Pattern detection failed: {str(e)}")

        return patterns

    @staticmethod
    def _detect_cross_field_patterns(user_edit: 'UserEdit') -> List[Dict[str, Any]]:
        """Detect patterns that span across multiple fields."""
        patterns = []

        try:
            session = user_edit.session

            # Get all edits in this session
            session_edits = UserEdit.objects.filter(
                session=session).order_by('timestamp')

            if len(session_edits) >= 3:
                # Look for time sequence corrections
                time_fields = [edit for edit in session_edits
                               if any(keyword in edit.field_name.upper()
                                      for keyword in ['START', 'BREAK', 'LUNCH', 'END'])]

                if len(time_fields) >= 2:
                    patterns.append({
                        'type': 'time_sequence_corrections',
                        'affected_fields': [edit.field_name for edit in time_fields],
                        'pattern': 'Multiple time fields corrected in sequence',
                        'recommendation': 'Review time extraction algorithm'
                    })

                # Look for job assignment corrections
                job_fields = [edit for edit in session_edits
                              if any(keyword in edit.field_name.upper()
                                     for keyword in ['HRS', 'HOURS', 'PCS', 'PIECE', 'WORK'])]

                if len(job_fields) >= 3:
                    patterns.append({
                        'type': 'job_assignment_corrections',
                        'affected_fields': [edit.field_name for edit in job_fields],
                        'pattern': 'Multiple job fields corrected',
                        'recommendation': 'Review hierarchical header extraction'
                    })

        except Exception as e:
            logger.warning(f"Cross-field pattern detection failed: {str(e)}")

        return patterns

    @staticmethod
    def _update_template_learning(user_edit: 'UserEdit') -> Dict[str, Any]:
        """Update template-specific learning based on user correction."""
        template_learning = {
            'type': 'template_learning',
            'template_id': None,
            'field_accuracy_update': {},
            'success_rate_adjustment': 0.0
        }

        try:
            crew_sheet = user_edit.session.crew_sheet

            # Find the template used (this might need to be stored better)
            # For now, try to get from extraction metadata
            if hasattr(crew_sheet, 'template_used') and crew_sheet.template_used:
                template = crew_sheet.template_used
                template_learning['template_id'] = str(template.id)

                # Adjust template success rate slightly
                total_fields = len(
                    crew_sheet.extracted_data.get('table_headers', []))
                # Small impact per correction
                correction_impact = 1.0 / max(total_fields, 1)

                template.success_rate = max(
                    0.1, template.success_rate - correction_impact)
                template.save()

                template_learning['success_rate_adjustment'] = - \
                    correction_impact
                template_learning['field_accuracy_update'][user_edit.field_name] = 'decreased'

        except Exception as e:
            logger.warning(f"Template learning update failed: {str(e)}")
            template_learning['error'] = str(e)

        return template_learning

    @staticmethod
    def _update_company_learning(user_edit: 'UserEdit') -> Dict[str, Any]:
        """Update company-wide learning patterns."""
        company_learning = {
            'type': 'company_learning',
            'pattern_updates': [],
            'vocabulary_updates': []
        }

        try:
            user = user_edit.session.crew_sheet.user

            # Get or create company learning profile
            company_profile, created = CompanyLearningProfile.objects.get_or_create(
                user=user,
                defaults={
                    'company_name': user.username,
                    'common_cost_centers': [],
                    'common_tasks': [],
                    'typical_headers': [],
                    'time_format_preferences': {}
                }
            )

            # Extract patterns from the correction
            field_name = user_edit.field_name
            corrected_value = user_edit.new_value

            # Update cost center patterns
            if '_' in field_name:
                parts = field_name.split('_')
                if len(parts) >= 2 and parts[0].isalnum():
                    cost_center = parts[0]
                    if cost_center not in company_profile.common_cost_centers:
                        company_profile.common_cost_centers.append(cost_center)
                        company_learning['pattern_updates'].append(
                            f'Added cost center: {cost_center}')

            # Update task patterns
            if len(parts) >= 3:
                task = parts[1]
                if task not in company_profile.common_tasks:
                    company_profile.common_tasks.append(task)
                    company_learning['pattern_updates'].append(
                        f'Added task: {task}')

            # Update time format preferences
            if any(keyword in field_name.upper() for keyword in ['START', 'BREAK', 'LUNCH', 'END']):
                if ':' in corrected_value:
                    company_profile.time_format_preferences['prefers_colon_format'] = True
                    company_learning['pattern_updates'].append(
                        'Prefers colon time format')

            company_profile.save()

        except Exception as e:
            logger.warning(f"Company learning update failed: {str(e)}")
            company_learning['error'] = str(e)

        return company_learning

    @staticmethod
    def _generate_immediate_improvements(user_edit: 'UserEdit') -> List[Dict[str, Any]]:
        """Generate immediate improvements that can be applied to future extractions."""
        improvements = []

        try:
            # Generate field-specific improvement
            field_improvement = {
                'type': 'field_extraction_improvement',
                'field_name': user_edit.field_name,
                'improvement': f'Apply correction pattern: {user_edit.original_value} → {user_edit.new_value}',
                'confidence': 0.8,
                'applies_to': 'future_extractions'
            }
            improvements.append(field_improvement)

            # Generate prompt improvement suggestion
            correction_type = RealTimeLearningEngine._classify_correction_type(
                user_edit.original_value, user_edit.new_value, user_edit.field_name
            )

            if correction_type == 'checkmark_to_time':
                improvements.append({
                    'type': 'prompt_improvement',
                    'improvement': f'Add instruction: Extract actual time values for {user_edit.field_name}, not just checkmarks',
                    'priority': 'high',
                    'applies_to': 'extraction_prompt'
                })
            elif correction_type == 'checkmark_to_numeric':
                improvements.append({
                    'type': 'prompt_improvement',
                    'improvement': f'Add instruction: Extract actual numeric values for {user_edit.field_name}, not just checkmarks',
                    'priority': 'high',
                    'applies_to': 'extraction_prompt'
                })

        except Exception as e:
            logger.warning(
                f"Immediate improvement generation failed: {str(e)}")

        return improvements

    @staticmethod
    def _cache_learning_insights(user_edit: 'UserEdit', feedback_result: Dict[str, Any]) -> None:
        """Cache learning insights for quick access during future extractions."""
        try:
            user_id = user_edit.session.crew_sheet.user.id
            field_name = user_edit.field_name

            # Cache field-specific insights
            field_cache_key = f"{RealTimeLearningEngine.CACHE_PREFIX}field_{user_id}_{field_name}"
            field_insights = {
                'recent_corrections': 1,
                'last_correction': {
                    'from': user_edit.original_value,
                    'to': user_edit.new_value,
                    'timestamp': user_edit.timestamp.isoformat()
                },
                'improvement_suggestions': feedback_result.get('immediate_improvements', [])
            }
            cache.set(field_cache_key, field_insights,
                      RealTimeLearningEngine.FEEDBACK_CACHE_TIMEOUT)

            # Cache user-specific insights
            user_cache_key = f"{RealTimeLearningEngine.CACHE_PREFIX}user_{user_id}"
            user_insights = {
                'last_feedback': timezone.now().isoformat(),
                'pattern_discoveries': feedback_result.get('pattern_discoveries', []),
                'recommendations': feedback_result.get('recommendations', [])
            }
            cache.set(user_cache_key, user_insights,
                      RealTimeLearningEngine.FEEDBACK_CACHE_TIMEOUT)

        except Exception as e:
            logger.warning(f"Caching learning insights failed: {str(e)}")

    @staticmethod
    def _generate_recommendations(user_edit: 'UserEdit') -> List[Dict[str, Any]]:
        """Generate recommendations for improving future extractions."""
        recommendations = []

        try:
            user = user_edit.session.crew_sheet.user

            # Analyze user's recent correction patterns
            recent_corrections = UserEdit.objects.filter(
                session__crew_sheet__user=user,
                timestamp__gte=timezone.now() - timedelta(days=7)
            ).count()

            if recent_corrections > 10:  # High correction rate
                recommendations.append({
                    'type': 'high_correction_rate',
                    'message': 'Consider creating or updating templates for better accuracy',
                    'priority': 'high',
                    'action': 'template_creation'
                })

            # Field-specific recommendations
            field_corrections = UserEdit.objects.filter(
                session__crew_sheet__user=user,
                field_name=user_edit.field_name,
                timestamp__gte=timezone.now() - timedelta(days=14)
            ).count()

            if field_corrections >= 3:
                recommendations.append({
                    'type': 'field_specific_issue',
                    'field_name': user_edit.field_name,
                    'message': f'Field {user_edit.field_name} frequently needs correction',
                    'priority': 'medium',
                    'action': 'field_analysis'
                })

            # Time-based recommendations
            if any(keyword in user_edit.field_name.upper() for keyword in ['START', 'BREAK', 'LUNCH']):
                if user_edit.original_value == '✓' and ':' in user_edit.new_value:
                    recommendations.append({
                        'type': 'time_extraction_improvement',
                        'message': 'Consider using higher resolution time extraction for better accuracy',
                        'priority': 'medium',
                        'action': 'prompt_enhancement'
                    })

        except Exception as e:
            logger.warning(f"Recommendation generation failed: {str(e)}")

        return recommendations

    @staticmethod
    def get_real_time_insights(user, field_name: Optional[str] = None) -> Dict[str, Any]:
        """Get real-time learning insights for a user or specific field."""
        insights = {
            'user_insights': {},
            'field_insights': {},
            'recent_patterns': [],
            'active_recommendations': []
        }

        try:
            # Get user-level insights from cache
            user_cache_key = f"{RealTimeLearningEngine.CACHE_PREFIX}user_{user.id}"
            user_insights = cache.get(user_cache_key)
            if user_insights:
                insights['user_insights'] = user_insights

            # Get field-level insights if specified
            if field_name:
                field_cache_key = f"{RealTimeLearningEngine.CACHE_PREFIX}field_{user.id}_{field_name}"
                field_insights = cache.get(field_cache_key)
                if field_insights:
                    insights['field_insights'] = field_insights

            # Get recent patterns
            pattern_keys = cache.keys(
                f"{RealTimeLearningEngine.CACHE_PREFIX}pattern_{user.id}_*")
            for key in pattern_keys:
                pattern = cache.get(key)
                if pattern:
                    insights['recent_patterns'].append(pattern)

            # Generate active recommendations
            insights['active_recommendations'] = RealTimeLearningEngine._get_active_recommendations(
                user)

        except Exception as e:
            logger.warning(f"Getting real-time insights failed: {str(e)}")
            insights['error'] = str(e)

        return insights

    @staticmethod
    def _get_active_recommendations(user) -> List[Dict[str, Any]]:
        """Get currently active recommendations for a user."""
        recommendations = []

        try:
            # High-level recommendations based on recent activity
            recent_sheets = CrewSheet.objects.filter(
                user=user,
                date_processed__gte=timezone.now() - timedelta(days=7),
                status='completed'
            )

            if recent_sheets.exists():
                avg_confidence = recent_sheets.aggregate(
                    avg_conf=Avg('confidence_score')
                )['avg_conf'] or 0.0

                if avg_confidence < 0.7:
                    recommendations.append({
                        'type': 'low_confidence_pattern',
                        'message': f'Average confidence is {avg_confidence:.1%}. Consider updating templates or providing more examples.',
                        'priority': 'high',
                        'action': 'improve_templates'
                    })

                # Check for high edit ratios
                total_edits = UserEdit.objects.filter(
                    session__crew_sheet__in=recent_sheets
                ).count()

                # More than 5 edits per sheet
                if total_edits > len(recent_sheets) * 5:
                    recommendations.append({
                        'type': 'high_edit_ratio',
                        'message': 'High number of corrections needed. Consider template optimization.',
                        'priority': 'medium',
                        'action': 'template_optimization'
                    })

        except Exception as e:
            logger.warning(f"Getting active recommendations failed: {str(e)}")

        return recommendations


class AdaptivePromptManager:
    """Manages adaptive prompts that improve based on real-time feedback."""

    @staticmethod
    def get_adaptive_prompt(
        user,
        base_prompt: str,
        field_insights: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generate an adaptive prompt based on user's real-time learning data."""

        try:
            # Get user's real-time insights
            insights = RealTimeLearningEngine.get_real_time_insights(user)

            # Start with base prompt
            adaptive_prompt = base_prompt

            # Add recent pattern adjustments
            if insights.get('recent_patterns'):
                adaptive_prompt += "\n\nRECENT CORRECTION PATTERNS (AVOID THESE ERRORS):\n"
                for pattern in insights['recent_patterns'][:3]:  # Top 3 patterns
                    if pattern.get('type') == 'frequent_correction_pattern':
                        adaptive_prompt += f"- Field '{pattern['field_name']}': {pattern['patterns'][0][0]}\n"

            # Add active recommendations
            if insights.get('active_recommendations'):
                adaptive_prompt += "\n\nSPECIAL ATTENTION NEEDED:\n"
                # Top 2 recommendations
                for rec in insights['active_recommendations'][:2]:
                    if rec.get('type') == 'field_specific_issue':
                        adaptive_prompt += f"- Pay extra attention to '{rec['field_name']}' - frequently needs correction\n"
                    elif rec.get('type') == 'time_extraction_improvement':
                        adaptive_prompt += "- Extract actual time values, not just checkmarks for time fields\n"

            # Add field-specific improvements if provided
            if field_insights:
                improvement_suggestions = field_insights.get(
                    'improvement_suggestions', [])
                for suggestion in improvement_suggestions:
                    if suggestion.get('type') == 'prompt_improvement':
                        adaptive_prompt += f"\n{suggestion['improvement']}\n"

            return adaptive_prompt

        except Exception as e:
            logger.warning(f"Adaptive prompt generation failed: {str(e)}")
            return base_prompt  # Fall back to base prompt
