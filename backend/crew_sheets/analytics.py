"""
Analytics and Quality Assessment Services for Crew Sheet Extraction
Implements Phase 1: Implicit Feedback Collection
"""
import re
import json
import logging
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models import Avg, Count, Q
from .models import (
    CrewSheet, ExtractionSession, FieldConfidence, UserEdit,
    QualityAssessment, UserProfile, ExtractionLog
)

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
        """Track a user edit."""
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

        return {
            "total_sheets": profile.total_sheets_processed,
            "total_edits": profile.total_edits_made,
            "avg_edits_per_sheet": profile.total_edits_made / max(profile.total_sheets_processed, 1),
            "avg_session_duration": profile.avg_session_duration,
            "abandonment_rate": profile.abandonment_rate,
            "most_edited_fields": dict(sorted(
                profile.frequently_edited_fields.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10]),
            "recent_activity": sessions.count(),
            "completion_rate": 1 - profile.abandonment_rate
        }


class LearningSystem:
    """Main learning system that coordinates all analytics."""

    @staticmethod
    def process_extraction(crew_sheet: CrewSheet, raw_extraction: dict) -> dict:
        """Process a new extraction through the learning pipeline."""
        # Quality assessment
        confidence_score, issues = QualityValidator.validate_extraction(
            raw_extraction, crew_sheet)

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

        return {
            "confidence_score": confidence_score,
            "needs_review": crew_sheet.needs_review,
            "issues": issues,
            "processed_data": raw_extraction
        }

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
