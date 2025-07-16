from django.shortcuts import render
from django.utils import timezone
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser

from .models import CrewSheet
from .serializers import CrewSheetSerializer, CrewSheetUploadSerializer, CrewSheetListSerializer

# Create your views here.

class CrewSheetViewSet(viewsets.ModelViewSet):
    """
    ViewSet for CrewSheet model that handles all CRUD operations
    and additional actions for processing crew sheets.
    """
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    
    def get_queryset(self):
        """Return only crew sheets belonging to the current user."""
        return CrewSheet.objects.filter(user=self.request.user).order_by('-date_uploaded')
    
    def get_serializer_class(self):
        """Return different serializers based on the action."""
        if self.action == 'create':
            return CrewSheetUploadSerializer
        elif self.action == 'list':
            return CrewSheetListSerializer
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
        
        # Update status to processing
        crew_sheet.status = 'processing'
        crew_sheet.save()
        
        # Trigger the processing task (to be implemented later)
        # process_crew_sheet.delay(crew_sheet.id)
        
        return Response({'status': 'processing started'}, status=status.HTTP_202_ACCEPTED)
