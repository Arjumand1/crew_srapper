from django.utils import timezone
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from .models import CrewSheet, ExtractionSession
from .serializers import (
    CrewSheetSerializer,
    CrewSheetCreateSerializer,
    CrewSheetListSerializer,
    CrewSheetUpdateSerializer,
)
from .services import CrewSheetProcessor
from .analytics import UserBehaviorAnalytics, LearningSystem
from django.db.models import Avg
from datetime import timedelta

# Create your views here.


class CrewSheetViewSet(viewsets.ModelViewSet):
    """ViewSet for crew sheet operations with learning system integration."""

    serializer_class = CrewSheetSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_queryset(self):
        """Filter crew sheets by user unless staff."""
        if self.request.user.is_staff:
            return CrewSheet.objects.all()
        return CrewSheet.objects.filter(user=self.request.user)

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'create':
            return CrewSheetCreateSerializer
        elif self.action == 'list':
            return CrewSheetListSerializer
        elif self.action in ['update', 'partial_update']:
            return CrewSheetUpdateSerializer
        return CrewSheetSerializer

    def create(self, request, *args, **kwargs):
        """Create a new crew sheet (upload only, no processing)."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        crew_sheet = serializer.save(user=request.user)

        # Just return the uploaded sheet info - no processing
        return Response({
            'id': crew_sheet.id,
            'name': crew_sheet.name,
            'status': crew_sheet.status,  # Will be 'pending'
            'date_uploaded': crew_sheet.date_uploaded,
            'date_processed': crew_sheet.date_processed,  # Will be null
            'extracted_data': crew_sheet.extracted_data,  # Will be null
            'confidence_score': crew_sheet.confidence_score,  # Will be 0.0
            'needs_review': crew_sheet.needs_review,  # Will be False
            'image': request.build_absolute_uri(crew_sheet.image.url) if crew_sheet.image else None,
        }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def process(self, request, pk=None):
        """Process a pending crew sheet."""
        crew_sheet = self.get_object()

        if crew_sheet.status != 'pending':
            return Response({
                'error': f'Cannot process crew sheet with status: {crew_sheet.status}'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            result = CrewSheetProcessor.process_crew_sheet_with_learning(
                crew_sheet)

            if result.get('valid', False):
                return Response({
                    'id': crew_sheet.id,
                    'status': crew_sheet.status,
                    'extracted_data': result['extracted_data'],
                    'learning_metrics': result['learning_metrics'],
                    'date_processed': crew_sheet.date_processed,
                })
            else:
                return Response({
                    'error': result.get('error_message', 'Processing failed'),
                    'id': crew_sheet.id,
                    'status': crew_sheet.status,
                    'date_processed': crew_sheet.date_processed,
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        except Exception as e:
            return Response({
                'error': f'Processing failed: {str(e)}',
                'id': crew_sheet.id,
                'status': crew_sheet.status,
                'date_processed': crew_sheet.date_processed,
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'])
    def start_session(self, request, pk=None):
        """Start a user editing session for behavior tracking."""
        crew_sheet = self.get_object()

        try:
            session = UserBehaviorAnalytics.start_session(
                crew_sheet, request.user)

            return Response({
                'session_id': session.id,
                'crew_sheet_id': crew_sheet.id,
                'started_at': session.started_at,
                'confidence_score': crew_sheet.confidence_score,
                'needs_review': crew_sheet.needs_review
            })

        except Exception as e:
            return Response({
                'error': f'Failed to start session: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'])
    def end_session(self, request):
        """End a user editing session."""
        session_id = request.data.get('session_id')
        outcome = request.data.get('outcome', 'saved')

        if not session_id:
            return Response({
                'error': 'session_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            session = ExtractionSession.objects.get(
                id=session_id, user=request.user)
            UserBehaviorAnalytics.end_session(session, outcome)

            return Response({
                'session_id': session.id,
                'ended_at': session.ended_at,
                'duration_seconds': session.duration_seconds,
                'outcome': session.outcome,
                'edit_count': session.edit_count
            })

        except ExtractionSession.DoesNotExist:
            return Response({
                'error': 'Session not found or access denied'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'error': f'Failed to end session: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'])
    def track_edit(self, request):
        """Track a user edit for learning purposes."""
        session_id = request.data.get('session_id')
        field_name = request.data.get('field_name')
        original_value = request.data.get('original_value', '')
        new_value = request.data.get('new_value', '')
        employee_index = request.data.get('employee_index')
        edit_type = request.data.get('edit_type', 'field_edit')
        edit_time_seconds = request.data.get('edit_time_seconds')

        if not session_id or not field_name:
            return Response({
                'error': 'session_id and field_name are required'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            session = ExtractionSession.objects.get(
                id=session_id, user=request.user)

            edit = UserBehaviorAnalytics.track_edit(
                session=session,
                field_name=field_name,
                original_value=original_value,
                new_value=new_value,
                employee_index=employee_index,
                edit_type=edit_type,
                edit_time_seconds=edit_time_seconds
            )

            return Response({
                'edit_id': edit.id,
                'session_id': session.id,
                'field_name': field_name,
                'timestamp': edit.timestamp,
                'edit_time_seconds': edit_time_seconds
            })

        except ExtractionSession.DoesNotExist:
            return Response({
                'error': 'Session not found or access denied'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'error': f'Failed to track edit: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['put'])
    def save_edits(self, request, pk=None):
        """Save user edits and update learning system."""
        crew_sheet = self.get_object()
        session_id = request.data.get('session_id')
        extracted_data = request.data.get('extracted_data')

        if not extracted_data:
            return Response({
                'error': 'extracted_data is required'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Update the crew sheet with edited data
            crew_sheet.extracted_data = extracted_data
            crew_sheet.save()

            # Update extraction log with final data if session provided
            if session_id:
                try:
                    session = ExtractionSession.objects.get(
                        id=session_id, user=request.user)
                    # Update the extraction log with final user-edited data
                    if hasattr(crew_sheet, 'extraction_logs') and crew_sheet.extraction_logs.exists():
                        latest_log = crew_sheet.extraction_logs.first()
                        latest_log.final_data = extracted_data
                        latest_log.edit_ratio = session.edit_count / \
                            max(len(extracted_data.get('employees', [])), 1)
                        latest_log.save()
                except ExtractionSession.DoesNotExist:
                    pass  # Continue without session tracking

            return Response({
                'message': 'Edits saved successfully',
                'crew_sheet_id': crew_sheet.id,
                'updated_at': timezone.now()
            })

        except Exception as e:
            return Response({
                'error': f'Failed to save edits: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'])
    def user_insights(self, request):
        """Get user behavior insights."""
        try:
            insights = UserBehaviorAnalytics.get_user_insights(request.user)
            return Response(insights)
        except Exception as e:
            return Response({
                'error': f'Failed to get insights: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'])
    def improvement_suggestions(self, request):
        """Get system improvement suggestions (staff only)."""
        if not request.user.is_staff:
            return Response({
                'error': 'Staff access required'
            }, status=status.HTTP_403_FORBIDDEN)

        try:
            suggestions = LearningSystem.get_improvement_suggestions()
            return Response(suggestions)
        except Exception as e:
            return Response({
                'error': f'Failed to get suggestions: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'])
    def quality_metrics(self, request):
        """Get overall quality metrics (staff only)."""
        if not request.user.is_staff:
            return Response({
                'error': 'Staff access required'
            }, status=status.HTTP_403_FORBIDDEN)

        try:
            # Get metrics for the last 30 days
            recent_sheets = CrewSheet.objects.filter(
                date_processed__gte=timezone.now() - timedelta(days=30)
            )

            metrics = {
                'total_sheets_processed': recent_sheets.count(),
                'avg_confidence_score': recent_sheets.aggregate(
                    avg_confidence=Avg('confidence_score')
                )['avg_confidence'] or 0.0,
                'sheets_needing_review': recent_sheets.filter(needs_review=True).count(),
                'processing_success_rate': recent_sheets.filter(status='completed').count() / max(recent_sheets.count(), 1),
                'sheets_by_status': {
                    'completed': recent_sheets.filter(status='completed').count(),
                    'failed': recent_sheets.filter(status='failed').count(),
                    'processing': recent_sheets.filter(status='processing').count(),
                    'pending': recent_sheets.filter(status='pending').count(),
                }
            }

            return Response(metrics)

        except Exception as e:
            return Response({
                'error': f'Failed to get quality metrics: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
