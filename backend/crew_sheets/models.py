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


class SheetTemplate(models.Model):
    """Store sample sheet templates for improved extraction."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                             on_delete=models.CASCADE)

    # Template metadata
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    company = models.CharField(max_length=255, blank=True)

    # Template structure
    template_image = models.ImageField(upload_to='templates/')
    header_structure = models.JSONField(
        null=True, blank=True, default=dict)  # Parsed header structure
    expected_fields = models.JSONField(
        null=True, blank=True, default=list)   # List of expected field names

    # Template classification
    TEMPLATE_TYPES = [
        ('time_tracking', 'Time Tracking'),
        ('piece_work', 'Piece Work'),
        ('mixed', 'Mixed Time/Piece'),
        ('custom', 'Custom'),
    ]
    template_type = models.CharField(max_length=20, choices=TEMPLATE_TYPES)

    # Usage metrics
    usage_count = models.IntegerField(default=0)
    success_rate = models.FloatField(default=0.0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-success_rate', '-usage_count']

    def __str__(self):
        return f"{self.name} ({self.company})"


class ExtractionExample(models.Model):
    """Store successful extraction examples for RAG/few-shot learning."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Source information
    crew_sheet = models.ForeignKey(CrewSheet, on_delete=models.CASCADE)
    template = models.ForeignKey(
        SheetTemplate, on_delete=models.SET_NULL, null=True, blank=True)

    # Extraction data
    input_description = models.TextField()  # Description of the input sheet
    extraction_result = models.JSONField()  # The successful extraction
    user_corrections = models.JSONField(
        default=dict)  # Any user corrections applied

    # Quality metrics
    confidence_score = models.FloatField()
    edit_ratio = models.FloatField()  # Ratio of fields edited by user
    user_satisfaction = models.FloatField(default=0.0)

    # Embeddings for similarity search
    embedding = models.JSONField(null=True, blank=True)  # Vector embedding

    # Classification
    # Layout, complexity, etc.
    sheet_characteristics = models.JSONField(default=dict)

    created_at = models.DateTimeField(auto_now_add=True)
    is_high_quality = models.BooleanField(
        default=False)  # Manually curated examples

    class Meta:
        ordering = ['-confidence_score', '-user_satisfaction']


class SmartReviewQueue(models.Model):
    """Intelligent queue for sheets that need review."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    crew_sheet = models.OneToOneField(CrewSheet, on_delete=models.CASCADE)

    # Priority scoring
    priority_score = models.FloatField(default=0.0)

    # Reasons for review
    REVIEW_REASONS = [
        ('low_confidence', 'Low Confidence Score'),
        ('validation_failed', 'Validation Rules Failed'),
        ('unusual_format', 'Unusual Format Detected'),
        ('high_edit_frequency', 'High Edit Frequency Expected'),
        ('user_requested', 'User Requested Review'),
        ('template_mismatch', 'Template Mismatch'),
    ]
    review_reason = models.CharField(max_length=30, choices=REVIEW_REASONS)

    # Review details
    flagged_issues = models.JSONField(default=list)
    suggested_actions = models.JSONField(default=list)

    # Review status
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('skipped', 'Skipped'),
    ]
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='pending')

    # Assignment
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_reviews'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-priority_score', '-created_at']


class CompanyLearningProfile(models.Model):
    """Learn company-specific patterns for better extraction."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                             on_delete=models.CASCADE)

    # Company identification
    company_name = models.CharField(max_length=255, blank=True)
    company_domain = models.CharField(
        max_length=100, blank=True)  # email domain

    # Learned patterns
    common_cost_centers = models.JSONField(default=list)
    common_tasks = models.JSONField(default=list)
    common_crew_names = models.JSONField(
        default=list)  # Known crew member names
    typical_headers = models.JSONField(default=list)
    header_variations = models.JSONField(default=dict)  # Common variations

    # Time patterns
    typical_start_times = models.JSONField(default=list)
    typical_break_patterns = models.JSONField(default=list)
    time_format_preferences = models.JSONField(default=dict)

    # Data patterns
    employee_name_patterns = models.JSONField(default=dict)
    common_job_codes = models.JSONField(default=list)
    typical_hour_ranges = models.JSONField(default=dict)

    # Learning metrics
    sheets_processed = models.IntegerField(default=0)
    accuracy_improvement = models.FloatField(default=0.0)
    confidence_in_patterns = models.FloatField(default=0.0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['user', 'company_name']


class ExtractionHighlights(models.Model):
    """Track new/unknown items found during extraction for highlighting."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    crew_sheet = models.OneToOneField(
        CrewSheet, on_delete=models.CASCADE, related_name='highlights')

    # New/unknown items found in extraction
    # Names not in common_crew_names
    new_crew_names = models.JSONField(default=list)
    # Cost centers not in common_cost_centers
    new_cost_centers = models.JSONField(default=list)
    new_tasks = models.JSONField(default=list)  # Tasks not in common_tasks

    # Additional context for highlights
    # Store positions, confidence, etc.
    highlight_metadata = models.JSONField(default=dict)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class PromptVersion(models.Model):
    """Track different prompt versions for A/B testing."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    version_name = models.CharField(max_length=100)
    prompt_content = models.TextField()

    # Performance metrics
    usage_count = models.IntegerField(default=0)
    success_rate = models.FloatField(default=0.0)
    avg_confidence = models.FloatField(default=0.0)
    avg_edit_ratio = models.FloatField(default=0.0)

    # Versioning
    based_on_insights = models.JSONField(default=dict)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-success_rate', '-created_at']
