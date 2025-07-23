from django.contrib import admin
from .models import (
    CrewSheet, ExtractionSession, FieldConfidence, UserEdit,
    QualityAssessment, UserProfile, ExtractionLog
)

# Register your models here.


@admin.register(CrewSheet)
class CrewSheetAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'status', 'confidence_score', 'needs_review', 'date_uploaded')
    list_filter = ('status', 'needs_review', 'date_uploaded')
    search_fields = ('name', 'user__email', 'user__username')
    readonly_fields = ('id', 'date_uploaded', 'date_processed')
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'name', 'user', 'image')
        }),
        ('Processing Information', {
            'fields': ('status', 'date_uploaded', 'date_processed', 'error_message')
        }),
        ('Quality Metrics', {
            'fields': ('confidence_score', 'quality_score', 'needs_review')
        }),
        ('Extracted Data', {
            'fields': ('extracted_data',)
        }),
    )


@admin.register(ExtractionSession)
class ExtractionSessionAdmin(admin.ModelAdmin):
    list_display = ('crew_sheet', 'user', 'outcome', 'edit_count', 'duration_seconds', 'started_at')
    list_filter = ('outcome', 'started_at', 'ended_at')
    search_fields = ('crew_sheet__name', 'user__username')
    readonly_fields = ('id', 'started_at', 'duration_seconds')
    
    fieldsets = (
        ('Session Info', {
            'fields': ('id', 'crew_sheet', 'user')
        }),
        ('Timing', {
            'fields': ('started_at', 'ended_at', 'duration_seconds', 'time_to_first_edit')
        }),
        ('Behavior Metrics', {
            'fields': ('outcome', 'edit_count', 'fields_edited')
        }),
    )


@admin.register(FieldConfidence)
class FieldConfidenceAdmin(admin.ModelAdmin):
    list_display = ('crew_sheet', 'field_name', 'employee_index', 'overall_confidence', 'needs_review', 'is_uncertain')
    list_filter = ('needs_review', 'is_uncertain', 'created_at')
    search_fields = ('crew_sheet__name', 'field_name')
    readonly_fields = ('id', 'created_at')
    
    fieldsets = (
        ('Field Info', {
            'fields': ('id', 'crew_sheet', 'field_name', 'employee_index')
        }),
        ('Confidence Metrics', {
            'fields': ('ocr_confidence', 'structure_confidence', 'data_consistency_score', 'historical_accuracy', 'overall_confidence')
        }),
        ('Quality Flags', {
            'fields': ('is_uncertain', 'needs_review', 'created_at')
        }),
    )


@admin.register(UserEdit)
class UserEditAdmin(admin.ModelAdmin):
    list_display = ('session', 'field_name', 'employee_index', 'edit_type', 'edit_time_seconds', 'timestamp')
    list_filter = ('edit_type', 'timestamp')
    search_fields = ('session__crew_sheet__name', 'field_name', 'original_value', 'new_value')
    readonly_fields = ('id', 'timestamp')
    
    fieldsets = (
        ('Edit Info', {
            'fields': ('id', 'session', 'field_name', 'employee_index', 'edit_type')
        }),
        ('Values', {
            'fields': ('original_value', 'new_value')
        }),
        ('Metrics', {
            'fields': ('edit_time_seconds', 'timestamp')
        }),
    )


@admin.register(QualityAssessment)
class QualityAssessmentAdmin(admin.ModelAdmin):
    list_display = ('crew_sheet', 'extraction_accuracy', 'data_completeness', 'format_consistency', 'assessed_at')
    list_filter = ('assessed_at', 'assessment_version')
    search_fields = ('crew_sheet__name',)
    readonly_fields = ('id', 'assessed_at')
    
    fieldsets = (
        ('Assessment Info', {
            'fields': ('id', 'crew_sheet', 'assessed_at', 'assessment_version')
        }),
        ('Quality Scores', {
            'fields': ('extraction_accuracy', 'data_completeness', 'format_consistency')
        }),
        ('Issues', {
            'fields': ('issues_detected', 'validation_errors')
        }),
    )


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'total_sheets_processed', 'total_edits_made', 'avg_session_duration', 'abandonment_rate')
    list_filter = ('created_at', 'updated_at')
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('id', 'created_at', 'updated_at')
    
    fieldsets = (
        ('User Info', {
            'fields': ('id', 'user', 'created_at', 'updated_at')
        }),
        ('Company Patterns', {
            'fields': ('common_cost_centers', 'common_tasks', 'typical_headers')
        }),
        ('Edit Patterns', {
            'fields': ('frequently_edited_fields', 'avg_session_duration', 'abandonment_rate')
        }),
        ('Learning Metrics', {
            'fields': ('total_sheets_processed', 'total_edits_made', 'accuracy_improvement')
        }),
    )


@admin.register(ExtractionLog)
class ExtractionLogAdmin(admin.ModelAdmin):
    list_display = ('crew_sheet', 'extraction_time_seconds', 'api_cost_estimate', 'edit_ratio', 'user_satisfaction_score', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('crew_sheet__name',)
    readonly_fields = ('id', 'created_at')
    
    fieldsets = (
        ('Log Info', {
            'fields': ('id', 'crew_sheet', 'created_at')
        }),
        ('Extraction Data', {
            'fields': ('raw_extraction', 'processed_extraction', 'final_data')
        }),
        ('Performance Metrics', {
            'fields': ('extraction_time_seconds', 'api_cost_estimate', 'token_usage')
        }),
        ('Learning Signals', {
            'fields': ('user_satisfaction_score', 'edit_ratio')
        }),
    )