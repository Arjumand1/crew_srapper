"""
Management command for generating analytics reports and testing the learning system.
"""
import json
from datetime import timedelta
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.db.models import Avg, Count
from crew_sheets.models import (
    CrewSheet, ExtractionSession, UserEdit, QualityAssessment, 
    UserProfile, ExtractionLog
)
from crew_sheets.analytics import LearningSystem, UserBehaviorAnalytics


class Command(BaseCommand):
    help = 'Generate analytics reports for the crew sheet extraction system'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Number of days to analyze (default: 30)',
        )
        parser.add_argument(
            '--format',
            choices=['json', 'table'],
            default='table',
            help='Output format (default: table)',
        )
        parser.add_argument(
            '--report-type',
            choices=['summary', 'quality', 'behavior', 'suggestions', 'all'],
            default='summary',
            help='Type of report to generate (default: summary)',
        )
        parser.add_argument(
            '--user-id',
            type=int,
            help='Generate report for specific user ID',
        )

    def handle(self, *args, **options):
        days = options['days']
        format_type = options['format']
        report_type = options['report_type']
        user_id = options.get('user_id')

        self.stdout.write(
            self.style.SUCCESS(f'Generating {report_type} report for last {days} days...')
        )

        try:
            if report_type == 'all':
                self.generate_all_reports(days, format_type, user_id)
            elif report_type == 'summary':
                self.generate_summary_report(days, format_type)
            elif report_type == 'quality':
                self.generate_quality_report(days, format_type)
            elif report_type == 'behavior':
                self.generate_behavior_report(days, format_type, user_id)
            elif report_type == 'suggestions':
                self.generate_suggestions_report(format_type)

        except Exception as e:
            raise CommandError(f'Error generating report: {str(e)}')

        self.stdout.write(self.style.SUCCESS('Report generation completed!'))

    def generate_all_reports(self, days, format_type, user_id):
        """Generate all available reports."""
        self.generate_summary_report(days, format_type)
        self.stdout.write('\n' + '='*80 + '\n')
        self.generate_quality_report(days, format_type)
        self.stdout.write('\n' + '='*80 + '\n')
        self.generate_behavior_report(days, format_type, user_id)
        self.stdout.write('\n' + '='*80 + '\n')
        self.generate_suggestions_report(format_type)

    def generate_summary_report(self, days, format_type):
        """Generate overall system summary report."""
        cutoff_date = timezone.now() - timedelta(days=days)
        recent_sheets = CrewSheet.objects.filter(date_uploaded__gte=cutoff_date)

        summary = {
            'period': f'Last {days} days',
            'total_sheets_uploaded': recent_sheets.count(),
            'completed_sheets': recent_sheets.filter(status='completed').count(),
            'failed_sheets': recent_sheets.filter(status='failed').count(),
            'processing_sheets': recent_sheets.filter(status='processing').count(),
            'pending_sheets': recent_sheets.filter(status='pending').count(),
            'avg_confidence_score': recent_sheets.aggregate(
                avg=Avg('confidence_score')
            )['avg'] or 0.0,
            'sheets_needing_review': recent_sheets.filter(needs_review=True).count(),
            'unique_users': recent_sheets.values('user').distinct().count(),
        }

        # Add success rate
        total_processed = summary['completed_sheets'] + summary['failed_sheets']
        summary['success_rate'] = (
            summary['completed_sheets'] / max(total_processed, 1) * 100
        )

        self.output_data('System Summary', summary, format_type)

    def generate_quality_report(self, days, format_type):
        """Generate quality metrics report."""
        cutoff_date = timezone.now() - timedelta(days=days)
        
        recent_assessments = QualityAssessment.objects.filter(
            assessed_at__gte=cutoff_date
        )

        if not recent_assessments.exists():
            self.stdout.write(self.style.WARNING('No quality assessments found for this period'))
            return

        quality_metrics = {
            'period': f'Last {days} days',
            'total_assessments': recent_assessments.count(),
            'avg_extraction_accuracy': recent_assessments.aggregate(
                avg=Avg('extraction_accuracy')
            )['avg'] or 0.0,
            'avg_data_completeness': recent_assessments.aggregate(
                avg=Avg('data_completeness')
            )['avg'] or 0.0,
            'avg_format_consistency': recent_assessments.aggregate(
                avg=Avg('format_consistency')
            )['avg'] or 0.0,
        }

        # Get most common issues
        all_issues = []
        for assessment in recent_assessments:
            all_issues.extend(assessment.issues_detected)

        issue_counts = {}
        for issue in all_issues:
            issue_counts[issue] = issue_counts.get(issue, 0) + 1

        quality_metrics['most_common_issues'] = dict(
            sorted(issue_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        )

        self.output_data('Quality Metrics', quality_metrics, format_type)

    def generate_behavior_report(self, days, format_type, user_id):
        """Generate user behavior analytics report."""
        cutoff_date = timezone.now() - timedelta(days=days)
        
        sessions_query = ExtractionSession.objects.filter(started_at__gte=cutoff_date)
        if user_id:
            sessions_query = sessions_query.filter(user_id=user_id)

        sessions = sessions_query

        if not sessions.exists():
            self.stdout.write(self.style.WARNING('No user sessions found for this period'))
            return

        behavior_metrics = {
            'period': f'Last {days} days',
            'total_sessions': sessions.count(),
            'completed_sessions': sessions.filter(outcome='saved').count(),
            'exported_sessions': sessions.filter(outcome='exported').count(),
            'abandoned_sessions': sessions.filter(outcome='abandoned').count(),
            'avg_session_duration': sessions.aggregate(
                avg=Avg('duration_seconds')
            )['avg'] or 0.0,
            'avg_edits_per_session': sessions.aggregate(
                avg=Avg('edit_count')
            )['avg'] or 0.0,
        }

        # Calculate abandonment rate
        total_ended_sessions = sessions.exclude(outcome__isnull=True).count()
        behavior_metrics['abandonment_rate'] = (
            behavior_metrics['abandoned_sessions'] / max(total_ended_sessions, 1) * 100
        )

        # Get most edited fields
        recent_edits = UserEdit.objects.filter(
            session__in=sessions
        ).values('field_name').annotate(
            edit_count=Count('id')
        ).order_by('-edit_count')[:10]

        behavior_metrics['most_edited_fields'] = list(recent_edits)

        # User-specific insights if user_id provided
        if user_id:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            try:
                user = User.objects.get(id=user_id)
                user_insights = UserBehaviorAnalytics.get_user_insights(user)
                behavior_metrics['user_specific'] = user_insights
            except User.DoesNotExist:
                behavior_metrics['user_specific'] = {'error': 'User not found'}

        self.output_data('User Behavior Analytics', behavior_metrics, format_type)

    def generate_suggestions_report(self, format_type):
        """Generate improvement suggestions report."""
        try:
            suggestions = LearningSystem.get_improvement_suggestions()
            self.output_data('Improvement Suggestions', suggestions, format_type)
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error generating suggestions: {str(e)}')
            )

    def output_data(self, title, data, format_type):
        """Output data in specified format."""
        self.stdout.write(f'\n{self.style.HTTP_INFO(title)}')
        self.stdout.write('=' * len(title))

        if format_type == 'json':
            self.stdout.write(json.dumps(data, indent=2, default=str))
        else:
            self.format_table_output(data)

    def format_table_output(self, data, indent=0):
        """Format data as a readable table."""
        indent_str = '  ' * indent
        
        for key, value in data.items():
            if isinstance(value, dict):
                self.stdout.write(f'{indent_str}{key}:')
                self.format_table_output(value, indent + 1)
            elif isinstance(value, list):
                self.stdout.write(f'{indent_str}{key}:')
                for i, item in enumerate(value):
                    if isinstance(item, dict):
                        self.stdout.write(f'{indent_str}  [{i}]:')
                        self.format_table_output(item, indent + 2)
                    else:
                        self.stdout.write(f'{indent_str}  - {item}')
            else:
                # Format numbers nicely
                if isinstance(value, float):
                    if 'rate' in key.lower() or 'score' in key.lower():
                        formatted_value = f'{value:.2%}' if 'rate' in key.lower() else f'{value:.3f}'
                    else:
                        formatted_value = f'{value:.2f}'
                else:
                    formatted_value = str(value)
                
                self.stdout.write(f'{indent_str}{key}: {formatted_value}')

    def test_learning_system(self):
        """Test the learning system with sample data."""
        self.stdout.write(self.style.SUCCESS('Testing Learning System...'))
        
        # Test quality validation
        sample_extraction = {
            'employees': [
                {'name': 'John Doe', 'START_IN': '6:00', 'TOTAL_HRS': '8'},
                {'name': 'Jane Smith', 'START_IN': '7:00', 'TOTAL_HRS': '7.5'}
            ],
            'table_headers': ['EMPLOYEE_NAME', 'START_IN', 'TOTAL_HRS']
        }
        
        from crew_sheets.analytics import QualityValidator
        confidence, issues = QualityValidator.validate_extraction(sample_extraction)
        
        self.stdout.write(f'Sample extraction confidence: {confidence:.3f}')
        if issues:
            self.stdout.write('Issues found:')
            for issue in issues:
                self.stdout.write(f'  - {issue}')
        else:
            self.stdout.write('No issues found!')

        self.stdout.write(self.style.SUCCESS('Learning system test completed!'))