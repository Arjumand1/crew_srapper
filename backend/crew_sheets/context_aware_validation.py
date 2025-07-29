"""
Context-Aware Validation System
Fine-tunes accuracy through intelligent validation based on context and patterns
"""
import re
import logging
from typing import Dict, List, Optional, Any
from datetime import timedelta
from django.utils import timezone
from .models import CrewSheet, SheetTemplate, CompanyLearningProfile, UserEdit

logger = logging.getLogger(__name__)


class ContextAwareValidator:
    """Advanced validation system that understands context and patterns."""

    # Context validation rules
    TIME_PATTERNS = {
        # 12-hour format
        'standard_time': re.compile(r'^([0-9]|1[0-2]):[0-5][0-9]$'),
        # 24-hour format
        'military_time': re.compile(r'^([01]?[0-9]|2[0-3]):[0-5][0-9]$'),
        'simple_hour': re.compile(r'^([0-9]|1[0-2])$'),  # Just hour
        # Decimal format
        'decimal_time': re.compile(r'^([0-9]|1[0-9]|2[0-3])\.[0-9]{1,2}$')
    }

    NUMERIC_PATTERNS = {
        # 0-24 hours
        'hours': re.compile(r'^([0-9]|1[0-9]|2[0-4])(\.[0-9]{1,2})?$'),
        'pieces': re.compile(r'^[0-9]{1,6}$'),  # Piece count
        'decimal': re.compile(r'^[0-9]+(\.[0-9]{1,2})?$')  # General decimal
    }

    @staticmethod
    def validate_extraction_with_context(
        extraction_result: Dict[str, Any],
        crew_sheet: Optional['CrewSheet'] = None,
        template: Optional['SheetTemplate'] = None,
        company_profile: Optional['CompanyLearningProfile'] = None
    ) -> Dict[str, Any]:
        """
        Perform context-aware validation of extraction results.

        Returns:
            Validation result with corrections and confidence adjustments
        """
        logger.info("Starting context-aware validation")

        validation_result = {
            'original_confidence': extraction_result.get('confidence_score', 0.8),
            'adjusted_confidence': 0.0,
            'validation_corrections': [],
            'context_insights': [],
            'accuracy_improvements': [],
            'validation_warnings': [],
            'field_validations': {}
        }

        try:
            employees = extraction_result.get('employees', [])
            headers = extraction_result.get('table_headers', [])

            if not employees or not headers:
                validation_result['adjusted_confidence'] = validation_result['original_confidence']
                return validation_result

            # 1. Time sequence validation
            time_validation = ContextAwareValidator._validate_time_sequences(
                employees, headers, company_profile
            )
            validation_result['field_validations']['time_sequences'] = time_validation

            # 2. Mathematical consistency validation
            math_validation = ContextAwareValidator._validate_mathematical_consistency(
                employees, headers
            )
            validation_result['field_validations']['mathematical_consistency'] = math_validation

            # 3. Cross-field relationship validation
            relationship_validation = ContextAwareValidator._validate_field_relationships(
                employees, headers, template
            )
            validation_result['field_validations']['field_relationships'] = relationship_validation

            # 4. Pattern consistency validation
            pattern_validation = ContextAwareValidator._validate_pattern_consistency(
                employees, headers, crew_sheet
            )
            validation_result['field_validations']['pattern_consistency'] = pattern_validation

            # 5. Company-specific validation
            if company_profile:
                company_validation = ContextAwareValidator._validate_company_patterns(
                    employees, headers, company_profile
                )
                validation_result['field_validations']['company_patterns'] = company_validation

            # 6. Template conformity validation
            if template:
                template_validation = ContextAwareValidator._validate_template_conformity(
                    employees, headers, template
                )
                validation_result['field_validations']['template_conformity'] = template_validation

            # Aggregate validation results
            validation_result = ContextAwareValidator._aggregate_validation_results(
                validation_result, extraction_result
            )

        except Exception as e:
            logger.error(f"Context-aware validation failed: {str(e)}")
            validation_result['error'] = str(e)
            validation_result['adjusted_confidence'] = validation_result['original_confidence']

        return validation_result

    @staticmethod
    def _validate_time_sequences(
        employees: List[Dict],
        headers: List[str],
        company_profile: Optional['CompanyLearningProfile']
    ) -> Dict[str, Any]:
        """Validate time sequences for logical consistency."""
        time_validation = {
            'valid_sequences': 0,
            'invalid_sequences': 0,
            'corrections_suggested': [],
            'patterns_detected': [],
            'confidence_impact': 0.0
        }

        try:
            # Identify time fields
            time_fields = [h for h in headers if any(
                keyword in h.upper() for keyword in ['START', 'BREAK', 'LUNCH', 'END', 'STOP']
            )]

            if len(time_fields) < 2:
                return time_validation

            # Sort time fields by typical sequence
            time_field_order = ContextAwareValidator._get_time_field_order(
                time_fields)

            for employee in employees:
                employee_times = []
                for field in time_field_order:
                    time_str = str(employee.get(field, '')).strip()
                    if time_str and time_str != '✓':
                        parsed_time = ContextAwareValidator._parse_time_value(
                            time_str)
                        if parsed_time:
                            employee_times.append(
                                (field, parsed_time, time_str))

                # Validate sequence
                if len(employee_times) >= 2:
                    sequence_valid = True
                    for i in range(1, len(employee_times)):
                        if employee_times[i][1] <= employee_times[i-1][1]:
                            sequence_valid = False
                            time_validation['corrections_suggested'].append({
                                'employee': employee.get('name', 'Unknown'),
                                'issue': f"Time sequence error: {employee_times[i-1][0]} ({employee_times[i-1][2]}) should be before {employee_times[i][0]} ({employee_times[i][2]})",
                                'suggested_fix': 'Review time values for logical sequence'
                            })

                    if sequence_valid:
                        time_validation['valid_sequences'] += 1
                    else:
                        time_validation['invalid_sequences'] += 1

            # Calculate confidence impact
            total_sequences = time_validation['valid_sequences'] + \
                time_validation['invalid_sequences']
            if total_sequences > 0:
                sequence_accuracy = time_validation['valid_sequences'] / \
                    total_sequences
                time_validation['confidence_impact'] = (
                    sequence_accuracy - 0.8) * 0.2  # Adjust by up to ±0.2

                if sequence_accuracy > 0.9:
                    time_validation['patterns_detected'].append(
                        'Excellent time sequence consistency')
                elif sequence_accuracy < 0.7:
                    time_validation['patterns_detected'].append(
                        'Frequent time sequence errors detected')

        except Exception as e:
            logger.warning(f"Time sequence validation failed: {str(e)}")

        return time_validation

    @staticmethod
    def _get_time_field_order(time_fields: List[str]) -> List[str]:
        """Get time fields in logical chronological order."""
        # Define typical order patterns
        order_patterns = [
            'START', 'BREAK1', 'LUNCH', 'BREAK2', 'END', 'STOP'
        ]

        ordered_fields = []

        for pattern in order_patterns:
            matching_fields = [f for f in time_fields if pattern in f.upper()]
            # Sort by sub-patterns (OUT before IN)
            matching_fields.sort(key=lambda x: ('OUT' in x.upper(), x))
            ordered_fields.extend(matching_fields)

        # Add any remaining fields
        remaining_fields = [f for f in time_fields if f not in ordered_fields]
        ordered_fields.extend(sorted(remaining_fields))

        return ordered_fields

    @staticmethod
    def _parse_time_value(time_str: str) -> Optional[int]:
        """Parse time string to minutes since midnight for comparison."""
        try:
            # Handle different time formats
            if ':' in time_str:
                parts = time_str.split(':')
                if len(parts) == 2:
                    hours = int(parts[0])
                    minutes = int(parts[1])
                    return hours * 60 + minutes
            elif '.' in time_str:
                # Decimal hours format
                decimal_hours = float(time_str)
                return int(decimal_hours * 60)
            else:
                # Just hours
                hours = int(time_str)
                return hours * 60
        except (ValueError, IndexError):
            return None

    @staticmethod
    def _validate_mathematical_consistency(
        employees: List[Dict],
        headers: List[str]
    ) -> Dict[str, Any]:
        """Validate mathematical relationships and totals."""
        math_validation = {
            'total_checks': 0,
            'valid_calculations': 0,
            'calculation_errors': [],
            'confidence_impact': 0.0,
            'suggestions': []
        }

        try:
            # Look for total fields
            total_fields = [h for h in headers if 'TOTAL' in h.upper()]
            hour_fields = [h for h in headers if any(
                keyword in h.upper() for keyword in ['HRS', 'HOURS', 'WORK']
            ) and 'TOTAL' not in h.upper()]

            for employee in employees:
                for total_field in total_fields:
                    total_value_str = str(
                        employee.get(total_field, '')).strip()
                    if total_value_str and total_value_str != '✓':
                        try:
                            expected_total = float(
                                total_value_str.replace(',', ''))

                            # Calculate sum from related fields
                            calculated_total = 0.0
                            contributing_fields = []

                            for hour_field in hour_fields:
                                value_str = str(employee.get(
                                    hour_field, '')).strip()
                                if value_str and value_str != '✓':
                                    try:
                                        value = float(
                                            value_str.replace(',', ''))
                                        calculated_total += value
                                        contributing_fields.append(hour_field)
                                    except ValueError:
                                        continue

                            if contributing_fields:
                                math_validation['total_checks'] += 1

                                # Allow small rounding differences
                                difference = abs(
                                    expected_total - calculated_total)
                                if difference <= 0.1:  # Within 0.1 hours
                                    math_validation['valid_calculations'] += 1
                                else:
                                    math_validation['calculation_errors'].append({
                                        'employee': employee.get('name', 'Unknown'),
                                        'total_field': total_field,
                                        'expected': expected_total,
                                        'calculated': calculated_total,
                                        'difference': difference,
                                        'contributing_fields': contributing_fields
                                    })

                        except ValueError:
                            continue

            # Calculate confidence impact
            if math_validation['total_checks'] > 0:
                accuracy = math_validation['valid_calculations'] / \
                    math_validation['total_checks']
                math_validation['confidence_impact'] = (accuracy - 0.8) * 0.15

                if accuracy > 0.95:
                    math_validation['suggestions'].append(
                        'Excellent mathematical consistency')
                elif accuracy < 0.8:
                    math_validation['suggestions'].append(
                        'Review total calculations - frequent discrepancies detected')

        except Exception as e:
            logger.warning(f"Mathematical validation failed: {str(e)}")

        return math_validation

    @staticmethod
    def _validate_field_relationships(
        employees: List[Dict],
        headers: List[str],
        template: Optional['SheetTemplate']
    ) -> Dict[str, Any]:
        """Validate relationships between related fields."""
        relationship_validation = {
            'relationships_checked': 0,
            'valid_relationships': 0,
            'relationship_issues': [],
            'confidence_impact': 0.0
        }

        try:
            # Check for hierarchical field relationships
            hierarchical_groups = {}

            for header in headers:
                if '_' in header:
                    parts = header.split('_')
                    if len(parts) >= 3:  # COST_CENTER_TASK_TYPE format
                        # Everything except the last part
                        group_key = '_'.join(parts[:-1])
                        if group_key not in hierarchical_groups:
                            hierarchical_groups[group_key] = []
                        hierarchical_groups[group_key].append(header)

            # Validate hierarchical relationships
            for group_key, group_fields in hierarchical_groups.items():
                if len(group_fields) >= 2:  # Need at least 2 fields to validate relationship
                    hrs_fields = [f for f in group_fields if any(
                        keyword in f.upper() for keyword in ['HRS', 'HOURS']
                    )]
                    pcs_fields = [f for f in group_fields if any(
                        keyword in f.upper() for keyword in ['PCS', 'PIECE']
                    )]

                    # Check for complementary relationships (if hours > 0, pieces should be > 0)
                    for employee in employees:
                        has_hours = False
                        has_pieces = False

                        for hrs_field in hrs_fields:
                            hrs_value = str(employee.get(
                                hrs_field, '')).strip()
                            if hrs_value and hrs_value != '✓':
                                try:
                                    if float(hrs_value.replace(',', '')) > 0:
                                        has_hours = True
                                        break
                                except ValueError:
                                    pass

                        for pcs_field in pcs_fields:
                            pcs_value = str(employee.get(
                                pcs_field, '')).strip()
                            if pcs_value and pcs_value != '✓':
                                try:
                                    if float(pcs_value.replace(',', '')) > 0:
                                        has_pieces = True
                                        break
                                except ValueError:
                                    pass

                        relationship_validation['relationships_checked'] += 1

                        # Both or neither should typically have values
                        if (has_hours and has_pieces) or (not has_hours and not has_pieces):
                            relationship_validation['valid_relationships'] += 1
                        else:
                            relationship_validation['relationship_issues'].append({
                                'employee': employee.get('name', 'Unknown'),
                                'group': group_key,
                                'issue': f"Inconsistent data: has_hours={has_hours}, has_pieces={has_pieces}",
                                'suggestion': 'Check for missing hours or piece work data'
                            })

            # Calculate confidence impact
            if relationship_validation['relationships_checked'] > 0:
                accuracy = relationship_validation['valid_relationships'] / \
                    relationship_validation['relationships_checked']
                relationship_validation['confidence_impact'] = (
                    accuracy - 0.7) * 0.1

        except Exception as e:
            logger.warning(f"Field relationship validation failed: {str(e)}")

        return relationship_validation

    @staticmethod
    def _validate_pattern_consistency(
        employees: List[Dict],
        headers: List[str],
        crew_sheet: Optional['CrewSheet']
    ) -> Dict[str, Any]:
        """Validate pattern consistency based on historical data."""
        pattern_validation = {
            'patterns_analyzed': 0,
            'consistent_patterns': 0,
            'pattern_anomalies': [],
            'confidence_impact': 0.0
        }

        try:
            if not crew_sheet:
                return pattern_validation

            # Get user's recent patterns
            user = crew_sheet.user
            recent_sheets = CrewSheet.objects.filter(
                user=user,
                status='completed',
                date_processed__gte=timezone.now() - timedelta(days=30)
            ).exclude(id=crew_sheet.id)[:10]

            if not recent_sheets:
                return pattern_validation

            # Analyze typical employee count patterns
            employee_counts = []
            for sheet in recent_sheets:
                if sheet.extracted_data and 'employees' in sheet.extracted_data:
                    employee_counts.append(
                        len(sheet.extracted_data['employees']))

            if employee_counts:
                avg_employee_count = sum(
                    employee_counts) / len(employee_counts)
                current_employee_count = len(employees)

                pattern_validation['patterns_analyzed'] += 1

                # Check if current count is within reasonable range
                if abs(current_employee_count - avg_employee_count) <= max(2, avg_employee_count * 0.3):
                    pattern_validation['consistent_patterns'] += 1
                else:
                    pattern_validation['pattern_anomalies'].append({
                        'type': 'employee_count_anomaly',
                        'current_count': current_employee_count,
                        'typical_count': round(avg_employee_count, 1),
                        'suggestion': 'Verify employee count - unusual for this user'
                    })

            # Analyze typical header patterns
            header_patterns = {}
            for sheet in recent_sheets:
                if sheet.extracted_data and 'table_headers' in sheet.extracted_data:
                    sheet_headers = set(sheet.extracted_data['table_headers'])
                    for header in sheet_headers:
                        header_patterns[header] = header_patterns.get(
                            header, 0) + 1

            if header_patterns:
                common_headers = {
                    h for h, c in header_patterns.items() if c >= len(recent_sheets) * 0.5}
                current_headers = set(headers)

                pattern_validation['patterns_analyzed'] += 1

                missing_common = common_headers - current_headers
                if len(missing_common) <= 2:  # Allow some variation
                    pattern_validation['consistent_patterns'] += 1
                else:
                    pattern_validation['pattern_anomalies'].append({
                        'type': 'header_pattern_anomaly',
                        'missing_common_headers': list(missing_common),
                        'suggestion': 'Some typically present headers are missing'
                    })

            # Calculate confidence impact
            if pattern_validation['patterns_analyzed'] > 0:
                consistency = pattern_validation['consistent_patterns'] / \
                    pattern_validation['patterns_analyzed']
                pattern_validation['confidence_impact'] = (
                    consistency - 0.7) * 0.1

        except Exception as e:
            logger.warning(f"Pattern consistency validation failed: {str(e)}")

        return pattern_validation

    @staticmethod
    def _validate_company_patterns(
        employees: List[Dict],
        headers: List[str],
        company_profile: 'CompanyLearningProfile'
    ) -> Dict[str, Any]:
        """Validate against known company patterns."""
        company_validation = {
            'validations_performed': 0,
            'pattern_matches': 0,
            'pattern_mismatches': [],
            'confidence_impact': 0.0,
            'suggestions': []
        }

        try:
            # Validate cost centers
            if company_profile.common_cost_centers:
                detected_cost_centers = set()
                for header in headers:
                    if '_' in header:
                        parts = header.split('_')
                        if len(parts) >= 2 and parts[0].isalnum():
                            detected_cost_centers.add(parts[0])

                company_validation['validations_performed'] += 1

                known_centers = set(company_profile.common_cost_centers)
                matching_centers = detected_cost_centers & known_centers
                unknown_centers = detected_cost_centers - known_centers

                if len(matching_centers) >= len(detected_cost_centers) * 0.7:  # 70% match
                    company_validation['pattern_matches'] += 1
                else:
                    company_validation['pattern_mismatches'].append({
                        'type': 'cost_center_mismatch',
                        'unknown_centers': list(unknown_centers),
                        'suggestion': 'Review cost center codes - some are not in company profile'
                    })

                if unknown_centers:
                    company_validation['suggestions'].append(
                        f"Consider adding {list(unknown_centers)} to company cost centers"
                    )

            # Validate tasks
            if company_profile.common_tasks:
                detected_tasks = set()
                for header in headers:
                    if '_' in header:
                        parts = header.split('_')
                        if len(parts) >= 3:
                            detected_tasks.add(parts[1])

                if detected_tasks:
                    company_validation['validations_performed'] += 1

                    known_tasks = set(company_profile.common_tasks)
                    matching_tasks = detected_tasks & known_tasks

                    if len(matching_tasks) >= len(detected_tasks) * 0.6:  # 60% match for tasks
                        company_validation['pattern_matches'] += 1
                    else:
                        unknown_tasks = detected_tasks - known_tasks
                        company_validation['pattern_mismatches'].append({
                            'type': 'task_mismatch',
                            'unknown_tasks': list(unknown_tasks),
                            'suggestion': 'Review task codes - some are not in company profile'
                        })

            # Calculate confidence impact
            if company_validation['validations_performed'] > 0:
                match_rate = company_validation['pattern_matches'] / \
                    company_validation['validations_performed']
                company_validation['confidence_impact'] = (
                    match_rate - 0.5) * 0.15

        except Exception as e:
            logger.warning(f"Company pattern validation failed: {str(e)}")

        return company_validation

    @staticmethod
    def _validate_template_conformity(
        employees: List[Dict],
        headers: List[str],
        template: 'SheetTemplate'
    ) -> Dict[str, Any]:
        """Validate conformity to template expectations."""
        template_validation = {
            'expected_fields_found': 0,
            'unexpected_fields': [],
            'missing_fields': [],
            'conformity_score': 0.0,
            'confidence_impact': 0.0
        }

        try:
            if not template.expected_fields:
                return template_validation

            expected_fields = set(template.expected_fields)
            current_fields = set(headers)

            found_fields = expected_fields & current_fields
            missing_fields = expected_fields - current_fields
            unexpected_fields = current_fields - expected_fields

            template_validation['expected_fields_found'] = len(found_fields)
            template_validation['missing_fields'] = list(missing_fields)
            template_validation['unexpected_fields'] = list(unexpected_fields)

            # Calculate conformity score
            if expected_fields:
                template_validation['conformity_score'] = len(
                    found_fields) / len(expected_fields)

            # Confidence impact based on conformity
            template_validation['confidence_impact'] = (
                template_validation['conformity_score'] - 0.7) * 0.2

        except Exception as e:
            logger.warning(f"Template conformity validation failed: {str(e)}")

        return template_validation

    @staticmethod
    def _aggregate_validation_results(
        validation_result: Dict[str, Any],
        extraction_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Aggregate all validation results into final assessment."""

        # Calculate overall confidence adjustment
        total_impact = 0.0
        impact_count = 0

        for field_validation in validation_result['field_validations'].values():
            if 'confidence_impact' in field_validation:
                total_impact += field_validation['confidence_impact']
                impact_count += 1

        # Average the impacts
        if impact_count > 0:
            average_impact = total_impact / impact_count
        else:
            average_impact = 0.0

        # Apply the adjustment
        original_confidence = validation_result['original_confidence']
        adjusted_confidence = max(
            0.1, min(1.0, original_confidence + average_impact))
        validation_result['adjusted_confidence'] = adjusted_confidence

        # Generate overall insights
        if adjusted_confidence > original_confidence + 0.05:
            validation_result['context_insights'].append(
                f"Context validation increased confidence by {adjusted_confidence - original_confidence:.1%}"
            )
        elif adjusted_confidence < original_confidence - 0.05:
            validation_result['context_insights'].append(
                f"Context validation identified issues, reducing confidence by {original_confidence - adjusted_confidence:.1%}"
            )

        # Generate accuracy improvements
        for field_name, field_validation in validation_result['field_validations'].items():
            if field_validation.get('corrections_suggested'):
                validation_result['accuracy_improvements'].extend(
                    field_validation['corrections_suggested']
                )

            if field_validation.get('suggestions'):
                validation_result['accuracy_improvements'].extend([
                    {'type': 'suggestion', 'message': suggestion}
                    for suggestion in field_validation['suggestions']
                ])

        return validation_result


class ValidationLearningSystem:
    """Learning system for validation rules based on user corrections."""

    @staticmethod
    def learn_from_corrections(user_edits: List['UserEdit']) -> Dict[str, Any]:
        """Learn validation patterns from user corrections."""
        learning_insights = {
            'patterns_learned': 0,
            'validation_rules_updated': [],
            'accuracy_patterns': {},
            'field_specific_rules': {}
        }

        try:
            # Group edits by field
            field_edits = {}
            for edit in user_edits:
                if edit.field_name not in field_edits:
                    field_edits[edit.field_name] = []
                field_edits[edit.field_name].append(edit)

            # Analyze patterns for each field
            for field_name, edits in field_edits.items():
                if len(edits) >= 3:  # Need sufficient data
                    field_patterns = ValidationLearningSystem._analyze_field_correction_patterns(
                        field_name, edits
                    )

                    if field_patterns:
                        learning_insights['field_specific_rules'][field_name] = field_patterns
                        learning_insights['patterns_learned'] += 1

        except Exception as e:
            logger.warning(f"Validation learning failed: {str(e)}")

        return learning_insights

    @staticmethod
    def _analyze_field_correction_patterns(
        field_name: str,
        edits: List['UserEdit']
    ) -> Dict[str, Any]:
        """Analyze correction patterns for a specific field."""

        patterns = {
            'common_corrections': {},
            'format_preferences': {},
            'validation_rules': []
        }

        # Track common correction patterns
        for edit in edits:
            correction_pattern = f"{edit.original_value} → {edit.new_value}"
            patterns['common_corrections'][correction_pattern] = \
                patterns['common_corrections'].get(correction_pattern, 0) + 1

        # Identify format preferences
        corrected_values = [edit.new_value for edit in edits if edit.new_value]

        if any(keyword in field_name.upper() for keyword in ['START', 'BREAK', 'LUNCH', 'END']):
            # Time field analysis
            time_formats = {'colon': 0, 'decimal': 0, 'simple': 0}
            for value in corrected_values:
                if ':' in value:
                    time_formats['colon'] += 1
                elif '.' in value:
                    time_formats['decimal'] += 1
                else:
                    time_formats['simple'] += 1

            preferred_format = max(time_formats, key=time_formats.get)
            patterns['format_preferences']['time_format'] = preferred_format

            # Generate validation rule
            if preferred_format == 'colon':
                patterns['validation_rules'].append(
                    f"Prefer HH:MM format for {field_name}"
                )

        return patterns
