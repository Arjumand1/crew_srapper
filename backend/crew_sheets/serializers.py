from rest_framework import serializers
from .models import CrewSheet, ExtractionSession, UserEdit, QualityAssessment, SheetTemplate


class CrewSheetSerializer(serializers.ModelSerializer):
    """Serializer for crew sheets, including all fields."""

    # Add computed fields for learning metrics
    field_confidences = serializers.SerializerMethodField()
    quality_assessment = serializers.SerializerMethodField()

    class Meta:
        model = CrewSheet
        fields = '__all__'
        read_only_fields = ('id', 'user', 'date_uploaded', 'status',
                            'date_processed', 'error_message', 'confidence_score',
                            'quality_score', 'needs_review')

    def get_field_confidences(self, obj):
        """Get field confidence scores for the crew sheet."""
        if hasattr(obj, 'field_confidences'):
            confidences = obj.field_confidences.filter(
                overall_confidence__lt=0.7)
            return [{
                'field_name': fc.field_name,
                'employee_index': fc.employee_index,
                'overall_confidence': fc.overall_confidence,
                'is_uncertain': fc.is_uncertain,
                'needs_review': fc.needs_review
            } for fc in confidences]
        return []

    def get_quality_assessment(self, obj):
        """Get the latest quality assessment."""
        if hasattr(obj, 'quality_assessments') and obj.quality_assessments.exists():
            qa = obj.quality_assessments.first()
            return {
                'extraction_accuracy': qa.extraction_accuracy,
                'data_completeness': qa.data_completeness,
                'format_consistency': qa.format_consistency,
                'issues_detected': qa.issues_detected
            }
        return None


class CrewSheetCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating new crew sheets."""

    class Meta:
        model = CrewSheet
        fields = ('id', 'name', 'image')
        read_only_fields = ('id',)


class CrewSheetUploadSerializer(serializers.ModelSerializer):
    """Serializer for uploading new crew sheets (legacy - use CrewSheetCreateSerializer)."""

    class Meta:
        model = CrewSheet
        fields = ('id', 'name', 'image')


class CrewSheetListSerializer(serializers.ModelSerializer):
    """Serializer for listing crew sheets with minimal fields."""

    # Add learning metrics for list view
    confidence_indicator = serializers.SerializerMethodField()
    needs_attention = serializers.SerializerMethodField()

    class Meta:
        model = CrewSheet
        fields = ('id', 'name', 'date_uploaded', 'status', 'image',
                  'confidence_score', 'needs_review', 'confidence_indicator',
                  'needs_attention')

    def get_confidence_indicator(self, obj):
        """Get confidence level indicator."""
        if obj.confidence_score >= 0.8:
            return 'high'
        elif obj.confidence_score >= 0.6:
            return 'medium'
        else:
            return 'low'

    def get_needs_attention(self, obj):
        """Check if sheet needs user attention."""
        return obj.needs_review or obj.status == 'failed'


class CrewSheetUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating crew sheet data."""

    class Meta:
        model = CrewSheet
        fields = ('extracted_data',)


class ExtractionSessionSerializer(serializers.ModelSerializer):
    """Serializer for extraction sessions."""

    class Meta:
        model = ExtractionSession
        fields = ('id', 'crew_sheet', 'started_at', 'ended_at',
                  'duration_seconds', 'outcome', 'fields_edited',
                  'edit_count', 'time_to_first_edit')
        read_only_fields = ('id', 'started_at', 'ended_at', 'duration_seconds')


class UserEditSerializer(serializers.ModelSerializer):
    """Serializer for user edits."""

    class Meta:
        model = UserEdit
        fields = ('id', 'session', 'field_name', 'employee_index',
                  'original_value', 'new_value', 'edit_type',
                  'edit_time_seconds', 'timestamp')
        read_only_fields = ('id', 'timestamp')


class QualityAssessmentSerializer(serializers.ModelSerializer):
    """Serializer for quality assessments."""

    class Meta:
        model = QualityAssessment
        fields = ('id', 'crew_sheet', 'extraction_accuracy',
                  'data_completeness', 'format_consistency',
                  'issues_detected', 'validation_errors',
                  'assessed_at', 'assessment_version')
        read_only_fields = ('id', 'assessed_at')


class SheetTemplateSerializer(serializers.ModelSerializer):
    """Serializer for sheet templates."""

    class Meta:
        model = SheetTemplate
        fields = ('id', 'name', 'description', 'company', 'template_image',
                  'header_structure', 'expected_fields', 'template_type',
                  'usage_count', 'success_rate', 'created_at', 'updated_at',
                  'is_active')
        read_only_fields = ('id', 'created_at', 'updated_at', 'usage_count',
                            'success_rate')
        extra_kwargs = {
            'header_structure': {'required': False, 'allow_null': True},
            'expected_fields': {'required': False, 'allow_null': True}
        }
