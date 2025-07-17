from rest_framework import serializers
from .models import CrewSheet


class CrewSheetSerializer(serializers.ModelSerializer):
    """Serializer for crew sheets, including all fields."""

    class Meta:
        model = CrewSheet
        fields = '__all__'
        read_only_fields = ('id', 'user', 'date_uploaded',
                            'status', 'date_processed', 'error_message')


class CrewSheetUploadSerializer(serializers.ModelSerializer):
    """Serializer for uploading new crew sheets."""

    class Meta:
        model = CrewSheet
        fields = ('id', 'name', 'image')


class CrewSheetListSerializer(serializers.ModelSerializer):
    """Serializer for listing crew sheets with minimal fields."""

    class Meta:
        model = CrewSheet
        fields = ('id', 'name', 'date_uploaded', 'status', 'image')


class CrewSheetUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating crew sheet data."""

    class Meta:
        model = CrewSheet
        fields = ('extracted_data',)
