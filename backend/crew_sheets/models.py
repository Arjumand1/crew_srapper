from django.db import models
from django.conf import settings
import uuid
import json


class CrewSheet(models.Model):
    """Model for storing uploaded crew sheets and their extracted data."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='crew_sheets')
    name = models.CharField(max_length=255, blank=True)
    date_uploaded = models.DateTimeField(auto_now_add=True)
    image = models.ImageField(upload_to='crew_sheets/')

    # Extracted data stored as JSON
    extracted_data = models.JSONField(null=True, blank=True)

    # Processing status
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='pending')

    # Metadata
    date_processed = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)

    # Phase 1: Confidence and quality tracking
    confidence_score = models.FloatField(default=0.0)
    quality_score = models.FloatField(default=0.0)
    needs_review = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.name or 'Unnamed'} - {self.date_uploaded.strftime('%Y-%m-%d %H:%M')}"


class ExtractionSession(models.Model):
    """Track user sessions for behavior analytics."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    crew_sheet = models.ForeignKey(
        CrewSheet, on_delete=models.CASCADE, related_name='sessions')
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                             on_delete=models.CASCADE)

    # Session timing
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.FloatField(null=True, blank=True)

    # Session outcome
    OUTCOME_CHOICES = [
        ('saved', 'Saved'),
        ('exported', 'Exported'),
        ('abandoned', 'Abandoned'),
    ]
    outcome = models.CharField(
        max_length=20, choices=OUTCOME_CHOICES, null=True, blank=True)

    # Behavior metrics
    fields_edited = models.JSONField(
        default=list)  # List of field names edited
    edit_count = models.IntegerField(default=0)
    time_to_first_edit = models.FloatField(null=True, blank=True)  # Seconds

    class Meta:
        ordering = ['-started_at']


class FieldConfidence(models.Model):
    """Store confidence scores for individual fields."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    crew_sheet = models.ForeignKey(
        CrewSheet, on_delete=models.CASCADE, related_name='field_confidences')

    field_name = models.CharField(max_length=255)
    employee_index = models.IntegerField(
        null=True, blank=True)  # For employee-specific fields

    # Confidence metrics
    ocr_confidence = models.FloatField(default=0.0)  # OCR quality
    structure_confidence = models.FloatField(
        default=0.0)  # Header structure detection
    data_consistency_score = models.FloatField(
        default=0.0)  # Data format consistency
    historical_accuracy = models.FloatField(
        default=0.0)  # Based on similar sheets

    # Combined confidence
    overall_confidence = models.FloatField(default=0.0)

    # Quality flags
    is_uncertain = models.BooleanField(default=False)
    needs_review = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['crew_sheet', 'field_name', 'employee_index']


class UserEdit(models.Model):
    """Track individual user edits for learning."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(
        ExtractionSession, on_delete=models.CASCADE, related_name='edits')

    field_name = models.CharField(max_length=255)
    employee_index = models.IntegerField(null=True, blank=True)

    original_value = models.TextField(null=True, blank=True)
    new_value = models.TextField(null=True, blank=True)

    # Edit context
    # field_edit, header_add, row_add, etc.
    edit_type = models.CharField(max_length=50, default='field_edit')
    edit_time_seconds = models.FloatField(
        default=0.0)  # Time spent on this edit

    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['timestamp']


class QualityAssessment(models.Model):
    """Store quality assessment results for sheets."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    crew_sheet = models.ForeignKey(
        CrewSheet, on_delete=models.CASCADE, related_name='quality_assessments')

    # Overall scores
    extraction_accuracy = models.FloatField(default=0.0)
    data_completeness = models.FloatField(default=0.0)
    format_consistency = models.FloatField(default=0.0)

    # Issue detection
    issues_detected = models.JSONField(default=list)  # List of issues found
    validation_errors = models.JSONField(
        default=list)  # Validation rule failures

    # Assessment metadata
    assessed_at = models.DateTimeField(auto_now_add=True)
    assessment_version = models.CharField(max_length=50, default='1.0')

    class Meta:
        ordering = ['-assessed_at']


class UserProfile(models.Model):
    """Learn user-specific patterns and preferences."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='extraction_profile')

    # Company-specific patterns
    common_cost_centers = models.JSONField(default=list)
    common_tasks = models.JSONField(default=list)
    typical_headers = models.JSONField(default=list)

    # Edit patterns
    frequently_edited_fields = models.JSONField(
        default=dict)  # field_name: edit_count
    avg_session_duration = models.FloatField(default=0.0)
    abandonment_rate = models.FloatField(default=0.0)

    # Learning metrics
    total_sheets_processed = models.IntegerField(default=0)
    total_edits_made = models.IntegerField(default=0)
    accuracy_improvement = models.FloatField(default=0.0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class ExtractionLog(models.Model):
    """Log all extractions for learning and analysis."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    crew_sheet = models.ForeignKey(
        CrewSheet, on_delete=models.CASCADE, related_name='extraction_logs')

    # Raw extraction data
    raw_extraction = models.JSONField()  # Original AI response
    processed_extraction = models.JSONField()  # After processing/validation
    final_data = models.JSONField(null=True, blank=True)  # After user edits

    # Performance metrics
    extraction_time_seconds = models.FloatField(default=0.0)
    api_cost_estimate = models.FloatField(default=0.0)
    token_usage = models.JSONField(default=dict)

    # Learning signals
    user_satisfaction_score = models.FloatField(
        null=True, blank=True)  # Derived from behavior
    edit_ratio = models.FloatField(default=0.0)  # Edits / total fields

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
