"""
Analytics and Quality Assessment Services for Crew Sheet Extraction
Implements Phase 1: Implicit Feedback Collection
"""
import re
import logging
from typing import List, Tuple, Optional
from datetime import timedelta
from django.utils import timezone
from django.db.models import Avg, Count
from .models import (
    CrewSheet, ExtractionSession, FieldConfidence, UserEdit,
    QualityAssessment, UserProfile, ExtractionLog
)
from .enhanced_confidence import EnhancedConfidenceScorer
from .realtime_learning import RealTimeLearningEngine
from .context_aware_validation import ContextAwareValidator

logger = logging.getLogger(__name__)


class QualityValidator:
    """Automatic quality assessment for extractions."""

    @staticmethod
    def validate_extraction(extracted_data: dict, crew_sheet=None) -> Tuple[float, List[str]]:
        """
        Validate extracted data and return confidence score and issues.

        Args:
            extracted_data: The extracted data from AI
            crew_sheet: Optional crew sheet instance for context

        Returns:
            Tuple of (confidence_score, issues_list)
        """
        confidence_score = 1.0
        issues = []

        if not extracted_data or not isinstance(extracted_data, dict):
            return 0.0, ["Invalid extraction data format"]

        # Check for required structure
        if 'employees' not in extracted_data:
            issues.append("Missing employees data")
            confidence_score -= 0.3

        if 'table_headers' not in extracted_data:
            issues.append("Missing table headers")
            confidence_score -= 0.2

        employees = extracted_data.get('employees', [])
        headers = extracted_data.get('table_headers', [])

        if not employees:
            issues.append("No employee data found")
            confidence_score -= 0.4

        # Validate time format consistency
        time_confidence = QualityValidator._validate_time_formats(
            employees, headers)
        confidence_score *= time_confidence
        if time_confidence < 0.8:
            issues.append("Inconsistent time formats detected")

        # Check for missing employee names
        name_confidence = QualityValidator._validate_employee_names(employees)
        confidence_score *= name_confidence
        if name_confidence < 0.9:
            issues.append("Missing or invalid employee names")

        # Validate header structure
        header_confidence = QualityValidator._validate_header_structure(
            headers)
        confidence_score *= header_confidence
        if header_confidence < 0.8:
            issues.append("Irregular header structure")

        # Check data consistency
        consistency_score = QualityValidator._check_data_consistency(
            employees, headers)
        confidence_score *= consistency_score
        if consistency_score < 0.7:
            issues.append("Data consistency issues detected")

        # Ensure confidence is between 0 and 1
        confidence_score = max(0.0, min(1.0, confidence_score))

        return confidence_score, issues

    @staticmethod
    def _validate_time_formats(employees: List[dict], headers: List[str]) -> float:
        """Validate time format consistency."""
        time_fields = [h for h in headers if any(keyword in h.upper()
                                                 for keyword in ['START', 'BREAK', 'LUNCH', 'STOP', 'END'])]

        if not time_fields:
            return 1.0  # No time fields to validate

        time_pattern = re.compile(r'^\d{1,2}:?\d{0,2}$|^\d{1,2}$')
        valid_times = 0
        total_times = 0

        for employee in employees:
            for field in time_fields:
                value = str(employee.get(field, '')).strip()
                if value:
                    total_times += 1
                    if time_pattern.match(value):
                        valid_times += 1

        return valid_times / total_times if total_times > 0 else 1.0

    @staticmethod
    def _validate_employee_names(employees: List[dict]) -> float:
        """Validate employee names are present and reasonable."""
        if not employees:
            return 0.0

        valid_names = 0
        for employee in employees:
            name = employee.get('name', '').strip()
            if name and len(name) > 1 and ' ' in name:  # Basic name validation
                valid_names += 1

        return valid_names / len(employees)

    @staticmethod
    def _validate_header_structure(headers: List[str]) -> float:
        """Validate header structure makes sense."""
        if not headers:
            return 0.0

        # Check for employee name header
        has_employee_name = any('name' in h.lower() or 'employee' in h.lower()
                                for h in headers)

        # Check for time-related headers
        has_time_headers = any(keyword in h.upper()
                               for h in headers
                               for keyword in ['START', 'BREAK', 'LUNCH', 'STOP'])

        # Check for job-related headers
        has_job_headers = any(keyword in h.upper()
                              for h in headers
                              for keyword in ['JOB', 'WORK', 'HRS', 'HOURS'])

        score = 0.0
        if has_employee_name:
            score += 0.4
        if has_time_headers:
            score += 0.3
        if has_job_headers:
            score += 0.3

        return score

    @staticmethod
    def _check_data_consistency(employees: List[dict], headers: List[str]) -> float:
        """Check for data consistency issues."""
        if not employees or not headers:
            return 0.0

        consistency_score = 1.0

        # Check for unusual patterns
        for header in headers:
            values = [str(emp.get(header, '')).strip() for emp in employees]
            non_empty_values = [v for v in values if v]

            if non_empty_values:
                # Check if all values are identical (suspicious)
                if len(set(non_empty_values)) == 1 and len(non_empty_values) > 3:
                    consistency_score -= 0.1

                # Check for placeholder values
                placeholder_patterns = ['✓', '?', 'TBD', 'NA', 'N/A']
                placeholder_count = sum(1 for v in non_empty_values
                                        if any(p in v for p in placeholder_patterns))
                if placeholder_count > len(non_empty_values) * 0.5:
                    consistency_score -= 0.2

        return max(0.0, consistency_score)


class ConfidenceScorer:
    """Calculate confidence scores for extracted fields."""

    @staticmethod
    def calculate_field_confidence(
        field_name: str,
        value: str,
        extraction_context: dict = None,
        historical_data: dict = None
    ) -> dict:
        """
        Calculate confidence score for a specific field.

        Returns:
            dict with confidence metrics
        """
        scores = {
            'ocr_confidence': 0.8,  # Default, would come from OCR engine
            'structure_confidence': 0.0,
            'data_consistency_score': 0.0,
            'historical_accuracy': 0.0,
            'overall_confidence': 0.0
        }

        # Structure confidence based on field type
        scores['structure_confidence'] = ConfidenceScorer._get_structure_confidence(
            field_name, value)

        # Data consistency based on format
        scores['data_consistency_score'] = ConfidenceScorer._get_data_consistency(
            field_name, value)

        # Historical accuracy (if available)
        if historical_data:
            scores['historical_accuracy'] = ConfidenceScorer._get_historical_accuracy(
                field_name, value, historical_data)
        else:
            scores['historical_accuracy'] = 0.5  # Neutral when no history

        # Calculate overall confidence
        weights = {
            'ocr_confidence': 0.3,
            'structure_confidence': 0.3,
            'data_consistency_score': 0.2,
            'historical_accuracy': 0.2
        }

        scores['overall_confidence'] = sum(
            scores[key] * weights[key] for key in weights
        )

        return scores

    @staticmethod
    def _get_structure_confidence(field_name: str, value: str) -> float:
        """Get confidence based on expected field structure."""
        if not value or not isinstance(value, str):
            return 0.0

        field_name = field_name.upper()
        value = value.strip()

        # Time fields
        if any(keyword in field_name for keyword in ['START', 'BREAK', 'LUNCH', 'STOP']):
            time_pattern = re.compile(r'^\d{1,2}:?\d{0,2}$|^\d{1,2}$')
            return 0.9 if time_pattern.match(value) else 0.3

        # Job hours fields
        if 'HRS' in field_name or 'HOURS' in field_name:
            try:
                float_val = float(value.replace(',', ''))
                return 0.9 if 0 <= float_val <= 24 else 0.5
            except ValueError:
                return 0.2

        # Piece work fields
        if 'PIECE' in field_name or 'PCS' in field_name:
            try:
                int_val = int(value.replace(',', ''))
                return 0.9 if int_val >= 0 else 0.5
            except ValueError:
                return 0.2

        # Employee name
        if 'NAME' in field_name or 'EMPLOYEE' in field_name:
            return 0.9 if len(value) > 1 and ' ' in value else 0.4

        return 0.7  # Default for unknown field types

    @staticmethod
    def _get_data_consistency(field_name: str, value: str) -> float:
        """Check data consistency score."""
        if not value:
            return 0.0

        # Check for placeholder indicators
        placeholder_patterns = ['✓', '?', 'TBD', 'NA', 'unclear', 'uncertain']
        if any(pattern in value.lower() for pattern in placeholder_patterns):
            return 0.2

        # Check for reasonable length
        if len(value.strip()) < 1:
            return 0.0
        elif len(value.strip()) > 100:  # Suspiciously long
            return 0.3

        return 0.8

    @staticmethod
    def _get_historical_accuracy(field_name: str, value: str, historical_data: dict) -> float:
        """Calculate accuracy based on historical corrections."""
        field_history = historical_data.get(field_name, {})

        if not field_history:
            return 0.5  # Neutral when no history

        # Check if this value has been corrected before
        corrections = field_history.get('corrections', {})
        if value in corrections:
            # Lower confidence if often corrected
            return 1.0 - corrections[value]

        # Use overall field accuracy
        return field_history.get('accuracy', 0.5)


class UserBehaviorAnalytics:
    """Analyze user behavior patterns for learning."""

    @staticmethod
    def start_session(crew_sheet: CrewSheet, user) -> ExtractionSession:
        """Start tracking a user session."""
        session = ExtractionSession.objects.create(
            crew_sheet=crew_sheet,
            user=user
        )
        logger.info(
            f"Started session {session.id} for user {user.id} on sheet {crew_sheet.id}")
        return session

    @staticmethod
    def end_session(session: ExtractionSession, outcome: str = 'saved') -> None:
        """End a user session and calculate metrics."""
        session.ended_at = timezone.now()
        session.outcome = outcome

        if session.started_at:
            session.duration_seconds = (
                session.ended_at - session.started_at
            ).total_seconds()

        session.save()

        # Update user profile
        UserBehaviorAnalytics._update_user_profile(session)

        logger.info(f"Ended session {session.id} with outcome: {outcome}")

    @staticmethod
    def track_edit(
        session: ExtractionSession,
        field_name: str,
        original_value: str,
        new_value: str,
        employee_index: Optional[int] = None,
        edit_type: str = 'field_edit',
        edit_time_seconds: Optional[float] = None
    ) -> UserEdit:
        """Track a user edit with real-time learning."""
        edit = UserEdit.objects.create(
            session=session,
            field_name=field_name,
            employee_index=employee_index,
            original_value=original_value,
            new_value=new_value,
            edit_type=edit_type,
            edit_time_seconds=edit_time_seconds or 0.0
        )

        # Update session metrics
        session.edit_count += 1
        if field_name not in session.fields_edited:
            session.fields_edited.append(field_name)

        # Calculate time to first edit if this is the first
        if session.edit_count == 1 and session.started_at:
            session.time_to_first_edit = (
                timezone.now() - session.started_at
            ).total_seconds()

        session.save()

        # Process real-time learning feedback
        try:
            feedback_result = RealTimeLearningEngine.process_user_feedback(
                user_edit=edit,
                immediate_update=True
            )
            logger.info(
                f"Real-time learning processed for field {field_name}: {len(feedback_result.get('learning_updates', []))} updates")
        except Exception as e:
            logger.warning(
                f"Real-time learning failed for edit {edit.id}: {str(e)}")

        logger.debug(f"Tracked edit in session {session.id}: {field_name}")
        return edit

    @staticmethod
    def _update_user_profile(session: ExtractionSession) -> None:
        """Update user profile based on session data."""
        user = session.user
        profile, created = UserProfile.objects.get_or_create(user=user)

        # Check if this is a new sheet being processed (not just reopening the same sheet)
        # Only increment if this is the first session for this sheet by this user
        existing_sessions = ExtractionSession.objects.filter(
            user=user,
            crew_sheet=session.crew_sheet
        ).order_by('started_at')

        # If this is the first session for this sheet, increment the counter
        if existing_sessions.count() == 1 and existing_sessions[0].id == session.id:
            profile.total_sheets_processed += 1

        # Always update edits count
        profile.total_edits_made += session.edit_count

        # Update average session duration
        if session.duration_seconds:
            current_avg = profile.avg_session_duration
            total_sessions = profile.total_sheets_processed or 1  # Avoid division by zero
            profile.avg_session_duration = (
                (current_avg * (total_sessions - 1) +
                 session.duration_seconds) / total_sessions
            )

        # Update abandonment rate
        if session.outcome == 'abandoned':
            abandoned_sessions = ExtractionSession.objects.filter(
                user=user,
                outcome='abandoned'
            ).count()
            total_sessions = ExtractionSession.objects.filter(
                user=user
            ).count()
            profile.abandonment_rate = abandoned_sessions / \
                total_sessions if total_sessions > 0 else 0

        # Update frequently edited fields
        for field_name in session.fields_edited:
            if field_name in profile.frequently_edited_fields:
                profile.frequently_edited_fields[field_name] += 1
            else:
                profile.frequently_edited_fields[field_name] = 1

        profile.save()

    @staticmethod
    def get_user_insights(user) -> dict:
        """Get behavioral insights for a user."""
        try:
            profile = user.extraction_profile
        except UserProfile.DoesNotExist:
            return {"message": "No user profile data available"}

        sessions = ExtractionSession.objects.filter(user=user)

        # Convert string values to integers for sorting
        sorted_fields = sorted(
            [(k, int(v)) for k, v in profile.frequently_edited_fields.items()],
            key=lambda x: x[1],
            reverse=True
        )

        return {
            "total_sheets": profile.total_sheets_processed,
            "total_edits": profile.total_edits_made,
            "avg_edits_per_sheet": profile.total_edits_made / max(profile.total_sheets_processed, 1),
            "avg_session_duration": profile.avg_session_duration,
            "abandonment_rate": profile.abandonment_rate,
            "most_edited_fields": dict(sorted_fields[:10]),
            "recent_activity": sessions.count(),
            "completion_rate": 1 - profile.abandonment_rate
        }


class LearningSystem:
    """Main learning system that coordinates all analytics."""

    @staticmethod
    def process_extraction(crew_sheet: CrewSheet, raw_extraction: dict) -> dict:
        """Process a new extraction through the learning pipeline."""
        # Enhanced quality assessment
        confidence_score, issues = QualityValidator.validate_extraction(
            raw_extraction, crew_sheet)

        # Get enhanced confidence scoring if available
        enhanced_confidence_result = None
        try:
            from .models import SheetTemplate, CompanyLearningProfile

            # Get template and company profile
            template = None
            company_profile = None

            # Try to get template from extraction metadata
            extraction_metadata = raw_extraction.get('extraction_metadata', {})
            template_used = extraction_metadata.get('template_used')
            if template_used:
                try:
                    template = SheetTemplate.objects.get(
                        id=template_used['id'])
                except (SheetTemplate.DoesNotExist, KeyError):
                    pass

            # Get company profile
            try:
                company_profile = CompanyLearningProfile.objects.get(
                    user=crew_sheet.user)
            except CompanyLearningProfile.DoesNotExist:
                pass

            # Calculate enhanced confidence
            enhanced_confidence_result = EnhancedConfidenceScorer.calculate_enhanced_confidence(
                extraction_result=raw_extraction,
                crew_sheet=crew_sheet,
                template=template,
                company_profile=company_profile
            )

            # Apply context-aware validation
            context_validation_result = None
            try:
                context_validation_result = ContextAwareValidator.validate_extraction_with_context(
                    extraction_result=raw_extraction,
                    crew_sheet=crew_sheet,
                    template=template,
                    company_profile=company_profile
                )

                if context_validation_result and 'adjusted_confidence' in context_validation_result:
                    # Use context-aware adjusted confidence
                    confidence_score = context_validation_result['adjusted_confidence']
                    logger.info(
                        f"Using context-aware confidence score: {confidence_score:.3f}")
                elif enhanced_confidence_result:
                    confidence_score = enhanced_confidence_result['overall_confidence']
                    logger.info(
                        f"Using enhanced confidence score: {confidence_score:.3f}")
            except Exception as e:
                logger.warning(f"Context-aware validation failed: {str(e)}")
                if enhanced_confidence_result:
                    confidence_score = enhanced_confidence_result['overall_confidence']
                    logger.info(
                        f"Using enhanced confidence score: {confidence_score:.3f}")

        except Exception as e:
            logger.warning(
                f"Enhanced confidence scoring failed, using basic: {str(e)}")

        # Update crew sheet with confidence metrics
        crew_sheet.confidence_score = confidence_score
        crew_sheet.needs_review = confidence_score < 0.7 or len(issues) > 2
        crew_sheet.save()

        # Create quality assessment record
        QualityAssessment.objects.create(
            crew_sheet=crew_sheet,
            extraction_accuracy=confidence_score,
            data_completeness=LearningSystem._calculate_completeness(
                raw_extraction),
            format_consistency=LearningSystem._calculate_format_consistency(
                raw_extraction),
            issues_detected=issues
        )

        # Calculate field-level confidence scores
        LearningSystem._create_field_confidence_scores(
            crew_sheet, raw_extraction)

        # Create extraction log
        ExtractionLog.objects.create(
            crew_sheet=crew_sheet,
            raw_extraction=raw_extraction,
            processed_extraction=raw_extraction  # Could be different after processing
        )

        result = {
            "confidence_score": confidence_score,
            "needs_review": crew_sheet.needs_review,
            "issues": issues,
            "processed_data": raw_extraction
        }

        # Add enhanced confidence data if available
        if enhanced_confidence_result:
            result.update({
                "enhanced_confidence": enhanced_confidence_result,
                "confidence_level": enhanced_confidence_result.get('confidence_level'),
                "quality_indicators": enhanced_confidence_result.get('quality_indicators'),
                "review_priority": enhanced_confidence_result.get('review_priority')
            })

        # Add context validation data if available
        if context_validation_result:
            result.update({
                "context_validation": context_validation_result,
                "validation_corrections": context_validation_result.get('validation_corrections', []),
                "context_insights": context_validation_result.get('context_insights', []),
                "accuracy_improvements": context_validation_result.get('accuracy_improvements', [])
            })

        return result

    @staticmethod
    def _calculate_completeness(extraction: dict) -> float:
        """Calculate data completeness score."""
        if not extraction or 'employees' not in extraction:
            return 0.0

        employees = extraction['employees']
        headers = extraction.get('table_headers', [])

        if not employees or not headers:
            return 0.0

        total_fields = len(employees) * len(headers)
        filled_fields = 0

        for employee in employees:
            for header in headers:
                if employee.get(header, '').strip():
                    filled_fields += 1

        return filled_fields / total_fields if total_fields > 0 else 0.0

    @staticmethod
    def _calculate_format_consistency(extraction: dict) -> float:
        """Calculate format consistency score."""
        # This would implement more sophisticated format checking
        return 0.8  # Placeholder

    @staticmethod
    def _create_field_confidence_scores(crew_sheet: CrewSheet, extraction: dict) -> None:
        """Create confidence scores for individual fields."""
        employees = extraction.get('employees', [])
        headers = extraction.get('table_headers', [])

        for header in headers:
            for emp_idx, employee in enumerate(employees):
                value = str(employee.get(header, '')).strip()

                scores = ConfidenceScorer.calculate_field_confidence(
                    header, value, extraction
                )

                FieldConfidence.objects.update_or_create(
                    crew_sheet=crew_sheet,
                    field_name=header,
                    employee_index=emp_idx,
                    defaults={
                        'ocr_confidence': scores['ocr_confidence'],
                        'structure_confidence': scores['structure_confidence'],
                        'data_consistency_score': scores['data_consistency_score'],
                        'historical_accuracy': scores['historical_accuracy'],
                        'overall_confidence': scores['overall_confidence'],
                        'is_uncertain': scores['overall_confidence'] < 0.6,
                        'needs_review': scores['overall_confidence'] < 0.4
                    }
                )

    @staticmethod
    def get_improvement_suggestions() -> dict:
        """Generate suggestions for improving extraction accuracy."""
        # Analyze recent extractions and user edits
        recent_assessments = QualityAssessment.objects.filter(
            assessed_at__gte=timezone.now() - timedelta(days=30)
        )

        common_issues = []
        for assessment in recent_assessments:
            common_issues.extend(assessment.issues_detected)

        # Count issue frequency
        issue_counts = {}
        for issue in common_issues:
            issue_counts[issue] = issue_counts.get(issue, 0) + 1

        # Get most frequently edited fields
        frequent_edits = UserEdit.objects.filter(
            timestamp__gte=timezone.now() - timedelta(days=30)
        ).values('field_name').annotate(
            edit_count=Count('id')
        ).order_by('-edit_count')[:10]

        return {
            "most_common_issues": sorted(issue_counts.items(), key=lambda x: x[1], reverse=True)[:10],
            "frequently_edited_fields": list(frequent_edits),
            "avg_confidence_score": recent_assessments.aggregate(
                avg_confidence=Avg('extraction_accuracy')
            )['avg_confidence'] or 0.0,
            "sheets_needing_review": CrewSheet.objects.filter(needs_review=True).count(),
            "recommendations": LearningSystem._generate_recommendations(issue_counts, frequent_edits)
        }

    @staticmethod
    def _generate_recommendations(issue_counts: dict, frequent_edits) -> List[str]:
        """Generate actionable recommendations."""
        recommendations = []

        # Check for common issues
        if "Inconsistent time formats detected" in issue_counts:
            recommendations.append(
                "Consider improving time format normalization in the AI prompt")

        if "Missing or invalid employee names" in issue_counts:
            recommendations.append(
                "Enhance employee name extraction validation")

        # Check for frequently edited fields
        if frequent_edits:
            top_edited_field = frequent_edits[0]['field_name']
            recommendations.append(
                f"Field '{top_edited_field}' is frequently edited - review extraction logic")

        if not recommendations:
            recommendations.append(
                "Extraction quality is stable - continue monitoring")

        return recommendations


class ExtractionLogger:
    """Centralized logging for all extractions and user behaviors."""

    @staticmethod
    def log_extraction(
        crew_sheet: CrewSheet,
        raw_extraction: dict,
        confidence_scores: dict,
        processing_time: float,
        api_cost: float = 0.0,
        token_usage: dict = None
    ) -> ExtractionLog:
        """Log a complete extraction with all metadata."""
        logger.info(f"Logging extraction for crew sheet {crew_sheet.id}")

        # Create extraction log
        extraction_log = ExtractionLog.objects.create(
            crew_sheet=crew_sheet,
            raw_extraction=raw_extraction,
            processed_extraction=raw_extraction,
            extraction_time_seconds=processing_time,
            api_cost_estimate=api_cost,
            token_usage=token_usage or {}
        )

        # Calculate initial user satisfaction score based on confidence
        overall_confidence = confidence_scores.get('overall_confidence', 0.0)
        extraction_log.user_satisfaction_score = overall_confidence

        # Calculate edit ratio (will be updated after user edits)
        total_fields = len(raw_extraction.get('table_headers', []))
        employees_count = len(raw_extraction.get('employees', []))
        extraction_log.edit_ratio = 0.0  # Will be updated after edits

        extraction_log.save()
        return extraction_log

    @staticmethod
    def log_user_behavior(
        session: ExtractionSession,
        behavior_type: str,
        metadata: dict = None
    ) -> None:
        """Log user behavior patterns for learning."""
        logger.debug(
            f"Logging user behavior: {behavior_type} for session {session.id}")

        # Update session with behavior data
        if not hasattr(session, 'behavior_logs'):
            session.behavior_logs = []

        behavior_log = {
            'timestamp': timezone.now().isoformat(),
            'behavior_type': behavior_type,
            'metadata': metadata or {}
        }

        session.behavior_logs.append(behavior_log)
        session.save()

    @staticmethod
    def update_extraction_outcome(
        crew_sheet: CrewSheet,
        final_data: dict,
        user_satisfaction: float = None
    ) -> None:
        """Update extraction log with final outcome after user edits."""
        try:
            extraction_log = crew_sheet.extraction_logs.latest('created_at')
            extraction_log.final_data = final_data

            # Calculate edit ratio
            original_data = extraction_log.raw_extraction
            if original_data and 'employees' in original_data:
                total_fields = len(original_data.get(
                    'table_headers', [])) * len(original_data.get('employees', []))

                # Count actual edits by comparing original vs final
                edit_count = ExtractionLogger._count_data_differences(
                    original_data, final_data
                )
                extraction_log.edit_ratio = edit_count / max(total_fields, 1)

            # Update user satisfaction if provided
            if user_satisfaction is not None:
                extraction_log.user_satisfaction_score = user_satisfaction

            extraction_log.save()
            logger.info(
                f"Updated extraction outcome for crew sheet {crew_sheet.id}")

        except ExtractionLog.DoesNotExist:
            logger.warning(
                f"No extraction log found for crew sheet {crew_sheet.id}")

    @staticmethod
    def _count_data_differences(original: dict, final: dict) -> int:
        """Count differences between original and final data."""
        if not original or not final:
            return 0

        original_employees = original.get('employees', [])
        final_employees = final.get('employees', [])

        if len(original_employees) != len(final_employees):
            # Major structural change
            return len(original_employees) + len(final_employees)

        edit_count = 0
        for i, (orig_emp, final_emp) in enumerate(zip(original_employees, final_employees)):
            for key in set(orig_emp.keys()) | set(final_emp.keys()):
                if str(orig_emp.get(key, '')).strip() != str(final_emp.get(key, '')).strip():
                    edit_count += 1

        return edit_count


class ContinuousLearner:
    """Continuous learning system that analyzes corrections and improves prompts."""

    @staticmethod
    def analyze_corrections(days_back: int = 30) -> dict:
        """Analyze user corrections to find common error patterns."""
        logger.info(f"Analyzing corrections from last {days_back} days")

        # Get recent user edits
        recent_edits = UserEdit.objects.filter(
            timestamp__gte=timezone.now() - timedelta(days=days_back)
        ).select_related('session__crew_sheet')

        # Analyze patterns
        field_errors = {}
        header_issues = {}
        common_corrections = {}

        for edit in recent_edits:
            field_name = edit.field_name
            original = edit.original_value
            corrected = edit.new_value

            # Track field-specific errors
            if field_name not in field_errors:
                field_errors[field_name] = []
            field_errors[field_name].append({
                'original': original,
                'corrected': corrected,
                'timestamp': edit.timestamp
            })

            # Track header structure issues
            if '_' in field_name:
                header_parts = field_name.split('_')
                if len(header_parts) >= 2:
                    header_type = '_'.join(header_parts[:-1])
                    if header_type not in header_issues:
                        header_issues[header_type] = 0
                    header_issues[header_type] += 1

            # Track common correction patterns
            correction_pattern = f"{original} -> {corrected}"
            if correction_pattern not in common_corrections:
                common_corrections[correction_pattern] = 0
            common_corrections[correction_pattern] += 1

        # Generate insights
        insights = {
            'total_edits': recent_edits.count(),
            'most_edited_fields': dict(sorted(
                {field: len(errors)
                 for field, errors in field_errors.items()}.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10]),
            'problematic_headers': dict(sorted(
                header_issues.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10]),
            'common_corrections': dict(sorted(
                common_corrections.items(),
                key=lambda x: x[1],
                reverse=True
            )[:20]),
            'field_error_details': field_errors
        }

        return insights

    @staticmethod
    def generate_improved_prompt(
        sheet_type: str = None,
        company_patterns: dict = None,
        recent_errors: dict = None
    ) -> str:
        """Generate improved extraction prompt based on learning data."""
        logger.info("Generating improved extraction prompt")

        base_prompt = """You are an expert at extracting data from crew/timesheets. These sheets track WHO (crew/people) does WHAT (task) WHERE (cost center), for HOW LONG (hours), and HOW FAST (pieces).

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
- CAPTURE THIS HIERARCHY in your column naming using this format: COST_CENTER_TASK_JOBTYPE"""

        # Add company-specific patterns
        if company_patterns:
            base_prompt += f"\n\nCOMPANY-SPECIFIC PATTERNS:\n"
            if 'common_cost_centers' in company_patterns:
                base_prompt += f"- Common cost centers: {', '.join(company_patterns['common_cost_centers'])}\n"
            if 'common_tasks' in company_patterns:
                base_prompt += f"- Common tasks: {', '.join(company_patterns['common_tasks'])}\n"
            if 'typical_headers' in company_patterns:
                base_prompt += f"- Typical headers: {', '.join(company_patterns['typical_headers'])}\n"

        # Add error-specific corrections
        if recent_errors and 'most_edited_fields' in recent_errors:
            base_prompt += f"\n\nCOMMON ERROR CORRECTIONS:\n"
            for field, count in list(recent_errors['most_edited_fields'].items())[:5]:
                base_prompt += f"- Pay special attention to '{field}' field (frequently corrected)\n"

        # Add time format improvements
        base_prompt += """
NESTED HEADER RULES (VERY IMPORTANT):
- Look for headers that span multiple columns with sub-headers below
- Examples:
  * "START" header with only "IN" column below → "START_IN"
  * "BREAK 1" header with "OUT" and "IN" columns below → "BREAK1_OUT", "BREAK1_IN"
  * "LUNCH" header with "OUT" and "IN" columns below → "LUNCH_OUT", "LUNCH_IN"
  * "BREAK 2" header with "OUT" and "IN" columns below → "BREAK2_OUT", "BREAK2_IN"
- NEVER use just "START", "BREAK 1", "LUNCH" if they have sub-columns
- Always include the sub-column identifier in the header name

DATA PLACEMENT ACCURACY:
- Match data values to the CORRECT hierarchical columns
- Time values must go in precise columns (START_IN, BREAK1_OUT, etc.)
- Job data must go in the corresponding hierarchical columns (COST_CENTER_TASK_JOB_TYPE)
- Only use placeholder marks ("✓") if actually present in original
- Extract actual numeric and text values whenever present"""

        return base_prompt

    @staticmethod
    def update_model_prompts(insights: dict) -> dict:
        """Update model prompts based on insights and run A/B testing."""
        logger.info("Updating model prompts based on insights")

        # Generate improved prompt
        improved_prompt = ContinuousLearner.generate_improved_prompt(
            recent_errors=insights
        )

        # Store prompt version for A/B testing
        prompt_version = {
            'version': f"v_{timezone.now().strftime('%Y%m%d_%H%M%S')}",
            'prompt': improved_prompt,
            'based_on_insights': insights,
            'created_at': timezone.now().isoformat()
        }

        # In a real implementation, you'd store this in a PromptVersion model
        # For now, log it
        logger.info(
            f"Generated new prompt version: {prompt_version['version']}")

        return {
            'prompt_version': prompt_version,
            'improvements_made': [
                'Added company-specific patterns',
                'Incorporated common error corrections',
                'Enhanced header structure rules',
                'Improved time format handling'
            ]
        }
