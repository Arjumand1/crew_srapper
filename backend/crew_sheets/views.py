from django.utils import timezone
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from .models import CrewSheet, ExtractionSession, SheetTemplate, SmartReviewQueue, CompanyLearningProfile
from .serializers import (
    CrewSheetSerializer,
    CrewSheetCreateSerializer,
    CrewSheetListSerializer,
    CrewSheetUpdateSerializer,
    SheetTemplateSerializer,
)
from .services import (
    CrewSheetProcessor,
    TemplateMatchingService,
    EnhancedExtractionService,
    SmartReviewQueueService
)
from .analytics import UserBehaviorAnalytics, LearningSystem, ContinuousLearner, ExtractionLogger
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

    @action(detail=False, methods=['get'])
    def template_list(self, request):
        """Get list of available templates."""
        try:
            templates = SheetTemplate.objects.all()
            return Response([template.name for template in templates])
        except Exception as e:
            return Response({
                'error': f'Failed to get templates: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'])
    def template_match(self, request):
        """Match a crew sheet to a template."""
        crew_sheet_id = request.data.get('crew_sheet_id')
        template_name = request.data.get('template_name')

        if not crew_sheet_id or not template_name:
            return Response({
                'error': 'crew_sheet_id and template_name are required'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            crew_sheet = CrewSheet.objects.get(id=crew_sheet_id)
            template = SheetTemplate.objects.get(name=template_name)

            result = TemplateMatchingService.match_template(
                crew_sheet, template)

            return Response({
                'match_score': result['match_score'],
                'matched_fields': result['matched_fields']
            })

        except CrewSheet.DoesNotExist:
            return Response({
                'error': 'Crew sheet not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except SheetTemplate.DoesNotExist:
            return Response({
                'error': 'Template not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'error': f'Failed to match template: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'])
    def smart_review_queue(self, request):
        """Get the smart review queue."""
        try:
            queue = SmartReviewQueue.objects.all()
            return Response([item.crew_sheet_id for item in queue])
        except Exception as e:
            return Response({
                'error': f'Failed to get smart review queue: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'])
    def enhanced_extraction(self, request):
        """Perform enhanced extraction on a crew sheet."""
        crew_sheet_id = request.data.get('crew_sheet_id')

        if not crew_sheet_id:
            return Response({
                'error': 'crew_sheet_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            crew_sheet = CrewSheet.objects.get(id=crew_sheet_id)

            result = EnhancedExtractionService.enhanced_extraction(crew_sheet)

            return Response({
                'extracted_data': result['extracted_data'],
                'confidence_score': result['confidence_score']
            })

        except CrewSheet.DoesNotExist:
            return Response({
                'error': 'Crew sheet not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'error': f'Failed to perform enhanced extraction: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'])
    def template_suggestions(self, request):
        """Get template suggestions for user."""
        try:
            suggestions = TemplateMatchingService.suggest_template(
                request.user)
            return Response({'suggestions': suggestions})
        except Exception as e:
            return Response({
                'error': f'Failed to get template suggestions: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'])
    def create_template(self, request):
        """Create a new template from a successful extraction."""
        crew_sheet_id = request.data.get('crew_sheet_id')
        template_name = request.data.get('template_name')
        template_type = request.data.get('template_type', 'mixed')
        description = request.data.get('description', '')
        company = request.data.get('company', '')

        if not crew_sheet_id or not template_name:
            return Response({
                'error': 'crew_sheet_id and template_name are required'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            crew_sheet = self.get_queryset().get(id=crew_sheet_id)

            template = TemplateMatchingService.create_template_from_sheet(
                user=request.user,
                crew_sheet=crew_sheet,
                template_name=template_name,
                template_type=template_type,
                description=description,
                company=company
            )

            return Response({
                'template_id': str(template.id),
                'name': template.name,
                'template_type': template.template_type,
                'success_rate': template.success_rate,
                'expected_fields': template.expected_fields
            }, status=status.HTTP_201_CREATED)

        except CrewSheet.DoesNotExist:
            return Response({
                'error': 'Crew sheet not found or access denied'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'error': f'Failed to create template: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'])
    def process_with_template(self, request, pk=None):
        """Process a crew sheet using a specific template."""
        crew_sheet = self.get_object()
        template_id = request.data.get('template_id')

        if crew_sheet.status != 'pending':
            return Response({
                'error': f'Cannot process crew sheet with status: {crew_sheet.status}'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Use enhanced extraction service with template
            result = EnhancedExtractionService.extract_with_intelligence(
                crew_sheet=crew_sheet,
                template_id=template_id,
                use_rag=True
            )

            if result.get('valid'):
                # Update crew sheet with results
                crew_sheet.status = 'completed'
                crew_sheet.extracted_data = result
                crew_sheet.confidence_score = result.get(
                    'confidence_score', 0.8)
                crew_sheet.date_processed = timezone.now()

                # Run quality assessment
                learning_result = LearningSystem.process_extraction(
                    crew_sheet, result)
                crew_sheet.needs_review = learning_result.get(
                    'needs_review', False)
                crew_sheet.save()

                return Response({
                    'id': crew_sheet.id,
                    'status': crew_sheet.status,
                    'extracted_data': result,
                    'confidence_score': crew_sheet.confidence_score,
                    'needs_review': crew_sheet.needs_review,
                    'learning_metrics': learning_result,
                    'date_processed': crew_sheet.date_processed,
                })
            else:
                crew_sheet.status = 'failed'
                crew_sheet.error_message = result.get(
                    'error_message', 'Enhanced extraction failed')
                crew_sheet.save()

                return Response({
                    'error': result.get('error_message', 'Processing failed'),
                    'id': crew_sheet.id,
                    'status': crew_sheet.status,
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        except Exception as e:
            crew_sheet.status = 'failed'
            crew_sheet.error_message = str(e)
            crew_sheet.save()

            return Response({
                'error': f'Enhanced processing failed: {str(e)}',
                'id': crew_sheet.id,
                'status': crew_sheet.status,
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'])
    def review_queue(self, request):
        """Get sheets in the smart review queue."""
        try:
            if not request.user.is_staff:
                # Regular users see only their own sheets in queue
                queue_items = SmartReviewQueue.objects.filter(
                    crew_sheet__user=request.user,
                    status='pending'
                ).select_related('crew_sheet')
            else:
                # Staff can see all queued items
                queue_items = SmartReviewQueue.objects.filter(
                    status='pending'
                ).select_related('crew_sheet')

            queue_data = []
            for item in queue_items:
                queue_data.append({
                    'crew_sheet_id': str(item.crew_sheet.id),
                    'crew_sheet_name': item.crew_sheet.name,
                    'priority_score': item.priority_score,
                    'review_reason': item.review_reason,
                    'flagged_issues': item.flagged_issues,
                    'suggested_actions': item.suggested_actions,
                    'confidence_score': item.crew_sheet.confidence_score,
                    'created_at': item.created_at,
                })

            return Response({
                'queue_items': queue_data,
                'total_count': len(queue_data)
            })

        except Exception as e:
            return Response({
                'error': f'Failed to get review queue: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'])
    def learning_insights(self, request):
        """Get learning insights and correction patterns."""
        try:
            # Get user-specific insights
            user_insights = UserBehaviorAnalytics.get_user_insights(
                request.user)

            # Get correction patterns (if staff)
            correction_insights = {}
            if request.user.is_staff:
                correction_insights = ContinuousLearner.analyze_corrections(
                    days_back=30)

            # Get company learning profile
            company_profile = None
            try:
                profile = CompanyLearningProfile.objects.get(user=request.user)
                company_profile = {
                    'company_name': profile.company_name,
                    'common_cost_centers': profile.common_cost_centers,
                    'common_tasks': profile.common_tasks,
                    'common_crew_names': profile.common_crew_names,
                    'typical_headers': profile.typical_headers,
                    'sheets_processed': profile.sheets_processed,
                    'accuracy_improvement': profile.accuracy_improvement,
                }
            except CompanyLearningProfile.DoesNotExist:
                pass

            return Response({
                'user_insights': user_insights,
                'correction_patterns': correction_insights,
                'company_profile': company_profile,
                'templates_available': request.user.sheettemplate_set.filter(is_active=True).count()
            })

        except Exception as e:
            return Response({
                'error': f'Failed to get learning insights: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get', 'post', 'put', 'patch'])
    def company_learning_profile(self, request):
        """Get or update company learning profile with cost centers, tasks, and headers."""
        if request.method == 'GET':
            try:
                profile, created = CompanyLearningProfile.objects.get_or_create(
                    user=request.user,
                    defaults={
                        'company_name': f"{request.user.username}'s Company",
                        'common_cost_centers': [],
                        'common_tasks': [],
                        'common_crew_names': [],
                        'typical_headers': ["EMPLOYEE NAME", "HOURS", "TASK", "COST CENTER"],
                        'sheets_processed': 0,
                        'accuracy_improvement': 0.0
                    }
                )

                return Response({
                    'id': str(profile.id),
                    'company_name': profile.company_name,
                    'common_cost_centers': profile.common_cost_centers,
                    'common_tasks': profile.common_tasks,
                    'common_crew_names': profile.common_crew_names,
                    'typical_headers': profile.typical_headers,
                    'sheets_processed': profile.sheets_processed,
                    'accuracy_improvement': profile.accuracy_improvement,
                    'created_at': profile.created_at,
                    'updated_at': profile.updated_at,
                })
            except Exception as e:
                return Response({
                    'error': f'Failed to get company learning profile: {str(e)}'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        elif request.method in ['POST', 'PUT', 'PATCH']:
            try:
                profile, created = CompanyLearningProfile.objects.get_or_create(
                    user=request.user,
                    defaults={
                        'company_name': f"{request.user.username}'s Company",
                        'common_cost_centers': [],
                        'common_tasks': [],
                        'common_crew_names': [],
                        'typical_headers': ["EMPLOYEE NAME", "HOURS", "TASK", "COST CENTER"],
                        'sheets_processed': 0,
                        'accuracy_improvement': 0.0
                    }
                )

                # Update fields from request data
                if 'company_name' in request.data:
                    profile.company_name = request.data['company_name']

                if 'common_cost_centers' in request.data:
                    profile.common_cost_centers = request.data['common_cost_centers']

                if 'common_tasks' in request.data:
                    profile.common_tasks = request.data['common_tasks']

                if 'typical_headers' in request.data:
                    # Ensure EMPLOYEE NAME header is always included
                    headers = request.data['typical_headers']
                    if "EMPLOYEE NAME" not in headers:
                        headers.append("EMPLOYEE NAME")
                    profile.typical_headers = headers

                profile.save()

                return Response({
                    'id': str(profile.id),
                    'company_name': profile.company_name,
                    'common_cost_centers': profile.common_cost_centers,
                    'common_tasks': profile.common_tasks,
                    'common_crew_names': profile.common_crew_names,
                    'typical_headers': profile.typical_headers,
                    'sheets_processed': profile.sheets_processed,
                    'accuracy_improvement': profile.accuracy_improvement,
                    'created_at': profile.created_at,
                    'updated_at': profile.updated_at,
                })
            except Exception as e:
                return Response({
                    'error': f'Failed to update company learning profile: {str(e)}'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'])
    def add_cost_center(self, request):
        """Add a cost center to the company learning profile."""
        try:
            # Get or create profile
            profile, created = CompanyLearningProfile.objects.get_or_create(
                user=request.user,
                defaults={
                    'company_name': f"{request.user.username}'s Company",
                    'common_cost_centers': [],
                    'common_tasks': [],
                    'typical_headers': ["EMPLOYEE NAME", "HOURS", "TASK", "COST CENTER"],
                    'sheets_processed': 0,
                    'accuracy_improvement': 0.0
                }
            )

            # Add cost center if not already in list
            cost_center = request.data.get('cost_center', '')
            if cost_center and cost_center not in profile.common_cost_centers:
                profile.common_cost_centers.append(cost_center)
                profile.save()

            return Response({
                'success': True,
                'common_cost_centers': profile.common_cost_centers
            })
        except Exception as e:
            return Response({
                'error': f'Failed to add cost center: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'])
    def add_task(self, request):
        """Add a task to the company learning profile."""
        try:
            # Get or create profile
            profile, created = CompanyLearningProfile.objects.get_or_create(
                user=request.user,
                defaults={
                    'company_name': f"{request.user.username}'s Company",
                    'common_tasks': [],
                    'common_cost_centers': [],
                    'typical_headers': ["EMPLOYEE NAME", "HOURS", "TASK", "COST CENTER"],
                    'sheets_processed': 0,
                    'accuracy_improvement': 0.0
                }
            )

            # Add task if not already in list
            task = request.data.get('task', '')
            if task and task not in profile.common_tasks:
                profile.common_tasks.append(task)
                profile.save()

            return Response({
                'success': True,
                'common_tasks': profile.common_tasks
            })
        except Exception as e:
            return Response({
                'error': f'Failed to add task: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'])
    def remove_cost_center(self, request):
        """Remove a cost center from the company learning profile."""
        try:
            # Get profile
            profile = CompanyLearningProfile.objects.get(user=request.user)

            # Remove cost center if in list
            cost_center = request.data.get('cost_center', '')
            if cost_center and cost_center in profile.common_cost_centers:
                profile.common_cost_centers.remove(cost_center)
                profile.save()

            return Response({
                'success': True,
                'common_cost_centers': profile.common_cost_centers
            })
        except CompanyLearningProfile.DoesNotExist:
            return Response({
                'error': 'Company learning profile not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'error': f'Failed to remove cost center: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'])
    def remove_task(self, request):
        """Remove a task from the company learning profile."""
        try:
            # Get profile
            profile = CompanyLearningProfile.objects.get(user=request.user)

            # Remove task if in list
            task = request.data.get('task', '')
            if task and task in profile.common_tasks:
                profile.common_tasks.remove(task)
                profile.save()

            return Response({
                'success': True,
                'common_tasks': profile.common_tasks
            })
        except CompanyLearningProfile.DoesNotExist:
            return Response({
                'error': 'Company learning profile not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'error': f'Failed to remove task: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'])
    def add_crew_member(self, request):
        """Add a crew member to the company learning profile."""
        try:
            from .crew_matching_service import CrewManagementService

            crew_name = request.data.get('crew_name', '').strip()
            if not crew_name:
                return Response({
                    'error': 'crew_name is required'
                }, status=status.HTTP_400_BAD_REQUEST)

            result = CrewManagementService.add_crew_member(
                request.user, crew_name)

            if result['success']:
                return Response({
                    'success': True,
                    'name': result['name']
                })
            else:
                return Response({
                    'error': result['error']
                }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({
                'error': f'Failed to add crew member: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'])
    def remove_crew_member(self, request):
        """Remove a crew member from the company learning profile."""
        try:
            from .crew_matching_service import CrewManagementService

            crew_name = request.data.get('crew_name', '').strip()
            if not crew_name:
                return Response({
                    'error': 'crew_name is required'
                }, status=status.HTTP_400_BAD_REQUEST)

            result = CrewManagementService.remove_crew_member(
                request.user, crew_name)

            if result['success']:
                return Response({
                    'success': True,
                    'name': result['name']
                })
            else:
                return Response({
                    'error': result['error']
                }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({
                'error': f'Failed to remove crew member: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TemplateViewSet(viewsets.ModelViewSet):
    """ViewSet for sheet template CRUD operations."""

    serializer_class = SheetTemplateSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_queryset(self):
        """Filter templates by user unless staff."""
        if self.request.user.is_staff:
            return SheetTemplate.objects.all()
        return SheetTemplate.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        """Associate template with current user."""
        serializer.save(user=self.request.user)
