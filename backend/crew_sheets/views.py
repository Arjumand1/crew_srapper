from django.shortcuts import render
from django.utils import timezone
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from .models import CrewSheet
from .serializers import (
    CrewSheetSerializer,
    CrewSheetUploadSerializer,
    CrewSheetListSerializer,
    CrewSheetUpdateSerializer,
)
from .services import CrewSheetProcessor

# Create your views here.


class CrewSheetViewSet(viewsets.ModelViewSet):
    """
    ViewSet for CrewSheet model that handles all CRUD operations
    and additional actions for processing crew sheets.
    """
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_queryset(self):
        """Return only crew sheets belonging to the current user."""
        return CrewSheet.objects.filter(user=self.request.user).order_by('-date_uploaded')

    def get_serializer_class(self):
        """Return different serializers based on the action."""
        if self.action == 'create':
            return CrewSheetUploadSerializer
        elif self.action == 'list':
            return CrewSheetListSerializer
        elif self.action in ['update', 'partial_update']:
            return CrewSheetUpdateSerializer
        return CrewSheetSerializer

    def perform_create(self, serializer):
        """Assign current user when creating a new crew sheet."""
        serializer.save(user=self.request.user, status='pending')

    @action(detail=True, methods=['post'])
    def process(self, request, pk=None):
        """
        Process the crew sheet image and extract data.
        This endpoint will be called after upload to start processing.
        """
        crew_sheet = self.get_object()

        # Allow processing only if in pending or failed state
        if crew_sheet.status not in ['pending', 'failed']:
            return Response(
                {'detail': f'Cannot process crew sheet in {crew_sheet.status} state'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Update status to processing
        crew_sheet.status = 'processing'
        crew_sheet.save()

        # Process the crew sheet directly
        # In production, this would be handled by a task queue like Celery
        success = CrewSheetProcessor.process_crew_sheet(crew_sheet.id)

        if success:
            # Fetch the updated crew sheet to return the latest data
            updated_crew_sheet = self.get_object()
            serializer = self.get_serializer(updated_crew_sheet)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            # Get the updated sheet with error info
            crew_sheet.refresh_from_db()
            error_message = crew_sheet.error_message or "Unknown error occurred during processing"

            # Return error details for debugging
            return Response({
                'status': 'processing failed',
                'error': error_message,
                'sheet_id': str(crew_sheet.id),
                'debug_info': {
                    'status': crew_sheet.status,
                    'date_processed': crew_sheet.date_processed,
                }
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
