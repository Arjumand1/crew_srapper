"""
Crew Matching and Highlighting Service
Matches extracted names, cost centers, and tasks against known lists and highlights new entries
"""
import logging
import re
from typing import Dict, List, Set, Tuple, Optional, Any
from difflib import SequenceMatcher
from .models import CompanyLearningProfile, ExtractionHighlights, CrewSheet

logger = logging.getLogger(__name__)


class CrewMatchingService:
    """Service for matching extracted data against known crew/company lists."""
    
    # Similarity threshold for fuzzy matching
    SIMILARITY_THRESHOLD = 0.8
    NAME_SIMILARITY_THRESHOLD = 0.85  # Higher threshold for names
    
    @staticmethod
    def match_and_highlight_extraction(
        crew_sheet: CrewSheet,
        extraction_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Match extraction results against known lists and create highlights for new items.
        
        Args:
            crew_sheet: CrewSheet instance
            extraction_result: Raw extraction result from AI
            
        Returns:
            Enhanced extraction result with highlighting information
        """
        logger.info(f"Starting crew matching for sheet {crew_sheet.id}")
        
        try:
            # Get company learning profile
            company_profile = CrewMatchingService._get_or_create_company_profile(crew_sheet.user)
            
            # Initialize highlighting data
            highlighting_data = {
                'new_crew_names': [],
                'new_cost_centers': [],
                'new_tasks': [],
                'matched_crew_names': [],
                'matched_cost_centers': [],
                'matched_tasks': [],
                'fuzzy_matches': {},
                'highlight_metadata': {}
            }
            
            employees = extraction_result.get('employees', [])
            headers = extraction_result.get('table_headers', [])
            
            if not employees:
                return CrewMatchingService._finalize_matching_result(
                    extraction_result, highlighting_data, crew_sheet
                )
            
            # 1. Match crew member names
            crew_matching_result = CrewMatchingService._match_crew_names(
                employees, company_profile.common_crew_names
            )
            highlighting_data.update(crew_matching_result)
            
            # 2. Match cost centers from headers
            cost_center_result = CrewMatchingService._match_cost_centers(
                headers, company_profile.common_cost_centers
            )
            highlighting_data.update(cost_center_result)
            
            # 3. Match tasks from headers
            task_result = CrewMatchingService._match_tasks(
                headers, company_profile.common_tasks
            )
            highlighting_data.update(task_result)
            
            # 4. Update company profile with new discoveries
            CrewMatchingService._update_company_profile_with_discoveries(
                company_profile, highlighting_data
            )
            
            # 5. Create or update highlights record
            CrewMatchingService._create_extraction_highlights(crew_sheet, highlighting_data)
            
            # 6. Enhance extraction result with matching information
            enhanced_result = CrewMatchingService._finalize_matching_result(
                extraction_result, highlighting_data, crew_sheet
            )
            
            logger.info(f"Crew matching completed: {len(highlighting_data['new_crew_names'])} new names, "
                       f"{len(highlighting_data['new_cost_centers'])} new cost centers, "
                       f"{len(highlighting_data['new_tasks'])} new tasks")
            
            return enhanced_result
            
        except Exception as e:
            logger.error(f"Crew matching failed: {str(e)}")
            # Return original result if matching fails
            extraction_result['crew_matching_error'] = str(e)
            return extraction_result
    
    @staticmethod
    def _get_or_create_company_profile(user) -> CompanyLearningProfile:
        """Get or create company learning profile for user."""
        try:
            return CompanyLearningProfile.objects.get(user=user)
        except CompanyLearningProfile.DoesNotExist:
            return CompanyLearningProfile.objects.create(
                user=user,
                company_name=user.username,
                common_crew_names=[],
                common_cost_centers=[],
                common_tasks=[]
            )
    
    @staticmethod
    def _match_crew_names(
        employees: List[Dict], 
        known_names: List[str]
    ) -> Dict[str, Any]:
        """Match extracted employee names against known crew names."""
        result = {
            'new_crew_names': [],
            'matched_crew_names': [],
            'fuzzy_crew_matches': {},
            'crew_name_metadata': {}
        }
        
        if not known_names:
            # If no known names, all extracted names are new
            for i, employee in enumerate(employees):
                name = employee.get('name', '').strip()
                if name and len(name) > 1:
                    result['new_crew_names'].append({
                        'name': name,
                        'employee_index': i,
                        'confidence': 'new',
                        'similarity_score': 0.0
                    })
            return result
        
        known_names_lower = [name.lower() for name in known_names]
        
        for i, employee in enumerate(employees):
            extracted_name = employee.get('name', '').strip()
            if not extracted_name or len(extracted_name) <= 1:
                continue
            
            # Try exact match (case insensitive)
            exact_match = CrewMatchingService._find_exact_match(
                extracted_name.lower(), known_names_lower
            )
            
            if exact_match:
                result['matched_crew_names'].append({
                    'extracted_name': extracted_name,
                    'matched_name': known_names[exact_match],
                    'employee_index': i,
                    'match_type': 'exact'
                })
            else:
                # Try fuzzy matching
                best_match, similarity = CrewMatchingService._find_best_fuzzy_match(
                    extracted_name, known_names, CrewMatchingService.NAME_SIMILARITY_THRESHOLD
                )
                
                if best_match:
                    result['fuzzy_crew_matches'][extracted_name] = {
                        'matched_name': best_match,
                        'similarity_score': similarity,
                        'employee_index': i,
                        'needs_confirmation': True
                    }
                    result['matched_crew_names'].append({
                        'extracted_name': extracted_name,
                        'matched_name': best_match,
                        'employee_index': i,
                        'match_type': 'fuzzy',
                        'similarity_score': similarity
                    })
                else:
                    # No match found - this is a new name
                    result['new_crew_names'].append({
                        'name': extracted_name,
                        'employee_index': i,
                        'confidence': 'new',
                        'similarity_score': 0.0,
                        'suggestions': CrewMatchingService._get_name_suggestions(
                            extracted_name, known_names
                        )
                    })
        
        return result
    
    @staticmethod
    def _match_cost_centers(
        headers: List[str], 
        known_cost_centers: List[str]
    ) -> Dict[str, Any]:
        """Match cost centers extracted from headers against known list."""
        result = {
            'new_cost_centers': [],
            'matched_cost_centers': [],
            'fuzzy_cost_center_matches': {}
        }
        
        # Extract cost centers from headers (assuming COST_CENTER_TASK_TYPE format)
        extracted_cost_centers = set()
        for header in headers:
            if '_' in header:
                parts = header.split('_')
                if len(parts) >= 2 and parts[0].isalnum():
                    extracted_cost_centers.add(parts[0])
        
        if not extracted_cost_centers:
            return result
        
        if not known_cost_centers:
            # All extracted cost centers are new
            result['new_cost_centers'] = [
                {
                    'cost_center': cc,
                    'confidence': 'new',
                    'headers': [h for h in headers if h.startswith(cc + '_')]
                }
                for cc in extracted_cost_centers
            ]
            return result
        
        known_cost_centers_lower = [cc.lower() for cc in known_cost_centers]
        
        for cost_center in extracted_cost_centers:
            # Try exact match
            exact_match = CrewMatchingService._find_exact_match(
                cost_center.lower(), known_cost_centers_lower
            )
            
            if exact_match:
                result['matched_cost_centers'].append({
                    'extracted_cost_center': cost_center,
                    'matched_cost_center': known_cost_centers[exact_match],
                    'match_type': 'exact',
                    'headers': [h for h in headers if h.startswith(cost_center + '_')]
                })
            else:
                # Try fuzzy matching
                best_match, similarity = CrewMatchingService._find_best_fuzzy_match(
                    cost_center, known_cost_centers, CrewMatchingService.SIMILARITY_THRESHOLD
                )
                
                if best_match:
                    result['fuzzy_cost_center_matches'][cost_center] = {
                        'matched_cost_center': best_match,
                        'similarity_score': similarity,
                        'needs_confirmation': True
                    }
                    result['matched_cost_centers'].append({
                        'extracted_cost_center': cost_center,
                        'matched_cost_center': best_match,
                        'match_type': 'fuzzy',
                        'similarity_score': similarity,
                        'headers': [h for h in headers if h.startswith(cost_center + '_')]
                    })
                else:
                    # New cost center
                    result['new_cost_centers'].append({
                        'cost_center': cost_center,
                        'confidence': 'new',
                        'headers': [h for h in headers if h.startswith(cost_center + '_')],
                        'suggestions': CrewMatchingService._get_suggestions(
                            cost_center, known_cost_centers
                        )
                    })
        
        return result
    
    @staticmethod
    def _match_tasks(
        headers: List[str], 
        known_tasks: List[str]
    ) -> Dict[str, Any]:
        """Match tasks extracted from headers against known list."""
        result = {
            'new_tasks': [],
            'matched_tasks': [],
            'fuzzy_task_matches': {}
        }
        
        # Extract tasks from headers (assuming COST_CENTER_TASK_TYPE format)
        extracted_tasks = set()
        for header in headers:
            if '_' in header:
                parts = header.split('_')
                if len(parts) >= 3:  # Need at least COST_TASK_TYPE
                    extracted_tasks.add(parts[1])
        
        if not extracted_tasks:
            return result
        
        if not known_tasks:
            # All extracted tasks are new
            result['new_tasks'] = [
                {
                    'task': task,
                    'confidence': 'new',
                    'headers': [h for h in headers if f'_{task}_' in h]
                }
                for task in extracted_tasks
            ]
            return result
        
        known_tasks_lower = [task.lower() for task in known_tasks]
        
        for task in extracted_tasks:
            # Try exact match
            exact_match = CrewMatchingService._find_exact_match(
                task.lower(), known_tasks_lower
            )
            
            if exact_match:
                result['matched_tasks'].append({
                    'extracted_task': task,
                    'matched_task': known_tasks[exact_match],
                    'match_type': 'exact',
                    'headers': [h for h in headers if f'_{task}_' in h]
                })
            else:
                # Try fuzzy matching
                best_match, similarity = CrewMatchingService._find_best_fuzzy_match(
                    task, known_tasks, CrewMatchingService.SIMILARITY_THRESHOLD
                )
                
                if best_match:
                    result['fuzzy_task_matches'][task] = {
                        'matched_task': best_match,
                        'similarity_score': similarity,
                        'needs_confirmation': True
                    }
                    result['matched_tasks'].append({
                        'extracted_task': task,
                        'matched_task': best_match,
                        'match_type': 'fuzzy',
                        'similarity_score': similarity,
                        'headers': [h for h in headers if f'_{task}_' in h]
                    })
                else:
                    # New task
                    result['new_tasks'].append({
                        'task': task,
                        'confidence': 'new',
                        'headers': [h for h in headers if f'_{task}_' in h],
                        'suggestions': CrewMatchingService._get_suggestions(
                            task, known_tasks
                        )
                    })
        
        return result
    
    @staticmethod
    def _find_exact_match(target: str, candidates: List[str]) -> Optional[int]:
        """Find exact match in candidates list, return index."""
        try:
            return candidates.index(target)
        except ValueError:
            return None
    
    @staticmethod
    def _find_best_fuzzy_match(
        target: str, 
        candidates: List[str], 
        threshold: float
    ) -> Tuple[Optional[str], float]:
        """Find best fuzzy match above threshold."""
        best_match = None
        best_similarity = 0.0
        
        for candidate in candidates:
            similarity = SequenceMatcher(None, target.lower(), candidate.lower()).ratio()
            if similarity > best_similarity and similarity >= threshold:
                best_similarity = similarity
                best_match = candidate
        
        return best_match, best_similarity
    
    @staticmethod
    def _get_name_suggestions(name: str, known_names: List[str], limit: int = 3) -> List[Dict]:
        """Get suggestions for similar names."""
        suggestions = []
        
        for known_name in known_names:
            similarity = SequenceMatcher(None, name.lower(), known_name.lower()).ratio()
            if similarity > 0.5:  # Lower threshold for suggestions
                suggestions.append({
                    'name': known_name,
                    'similarity': similarity
                })
        
        # Sort by similarity and return top suggestions
        suggestions.sort(key=lambda x: x['similarity'], reverse=True)
        return suggestions[:limit]
    
    @staticmethod
    def _get_suggestions(item: str, known_items: List[str], limit: int = 3) -> List[Dict]:
        """Get suggestions for similar items."""
        suggestions = []
        
        for known_item in known_items:
            similarity = SequenceMatcher(None, item.lower(), known_item.lower()).ratio()
            if similarity > 0.4:  # Lower threshold for suggestions
                suggestions.append({
                    'item': known_item,
                    'similarity': similarity
                })
        
        # Sort by similarity and return top suggestions
        suggestions.sort(key=lambda x: x['similarity'], reverse=True)
        return suggestions[:limit]
    
    @staticmethod
    def _update_company_profile_with_discoveries(
        company_profile: CompanyLearningProfile,
        highlighting_data: Dict[str, Any]
    ) -> None:
        """Update company profile with newly discovered items (optional auto-learning)."""
        try:
            # Note: We might want to make this optional or require user confirmation
            # For now, we'll just log the discoveries without auto-adding
            
            new_names = [item['name'] for item in highlighting_data.get('new_crew_names', [])]
            new_cost_centers = [item['cost_center'] for item in highlighting_data.get('new_cost_centers', [])]
            new_tasks = [item['task'] for item in highlighting_data.get('new_tasks', [])]
            
            if new_names or new_cost_centers or new_tasks:
                logger.info(f"Discovered new items for company {company_profile.company_name}: "
                           f"Names: {new_names}, Cost Centers: {new_cost_centers}, Tasks: {new_tasks}")
                
                # We could add them to the profile here, but it's better to let users confirm
                # company_profile.common_crew_names.extend(new_names)
                # company_profile.common_cost_centers.extend(new_cost_centers)
                # company_profile.common_tasks.extend(new_tasks)
                # company_profile.save()
        
        except Exception as e:
            logger.warning(f"Failed to update company profile: {str(e)}")
    
    @staticmethod
    def _create_extraction_highlights(
        crew_sheet: CrewSheet, 
        highlighting_data: Dict[str, Any]
    ) -> None:
        """Create or update ExtractionHighlights record."""
        try:
            highlights, created = ExtractionHighlights.objects.update_or_create(
                crew_sheet=crew_sheet,
                defaults={
                    'new_crew_names': highlighting_data.get('new_crew_names', []),
                    'new_cost_centers': highlighting_data.get('new_cost_centers', []),
                    'new_tasks': highlighting_data.get('new_tasks', []),
                    'highlight_metadata': {
                        'matched_crew_names': highlighting_data.get('matched_crew_names', []),
                        'matched_cost_centers': highlighting_data.get('matched_cost_centers', []),
                        'matched_tasks': highlighting_data.get('matched_tasks', []),
                        'fuzzy_matches': {
                            'crew': highlighting_data.get('fuzzy_crew_matches', {}),
                            'cost_centers': highlighting_data.get('fuzzy_cost_center_matches', {}),
                            'tasks': highlighting_data.get('fuzzy_task_matches', {})
                        }
                    }
                }
            )
            
            logger.info(f"{'Created' if created else 'Updated'} highlights for crew sheet {crew_sheet.id}")
            
        except Exception as e:
            logger.error(f"Failed to create extraction highlights: {str(e)}")
    
    @staticmethod
    def _finalize_matching_result(
        extraction_result: Dict[str, Any],
        highlighting_data: Dict[str, Any],
        crew_sheet: CrewSheet
    ) -> Dict[str, Any]:
        """Finalize the matching result with all highlighting information."""
        
        # Add crew matching information to the result
        extraction_result['crew_matching'] = {
            'has_highlights': bool(
                highlighting_data.get('new_crew_names') or 
                highlighting_data.get('new_cost_centers') or 
                highlighting_data.get('new_tasks')
            ),
            'summary': {
                'new_crew_names_count': len(highlighting_data.get('new_crew_names', [])),
                'new_cost_centers_count': len(highlighting_data.get('new_cost_centers', [])),
                'new_tasks_count': len(highlighting_data.get('new_tasks', [])),
                'matched_crew_names_count': len(highlighting_data.get('matched_crew_names', [])),
                'matched_cost_centers_count': len(highlighting_data.get('matched_cost_centers', [])),
                'matched_tasks_count': len(highlighting_data.get('matched_tasks', []))
            },
            'highlights': {
                'new_crew_names': highlighting_data.get('new_crew_names', []),
                'new_cost_centers': highlighting_data.get('new_cost_centers', []),
                'new_tasks': highlighting_data.get('new_tasks', [])
            },
            'matches': {
                'crew_names': highlighting_data.get('matched_crew_names', []),
                'cost_centers': highlighting_data.get('matched_cost_centers', []),
                'tasks': highlighting_data.get('matched_tasks', [])
            },
            'fuzzy_matches': {
                'crew_names': highlighting_data.get('fuzzy_crew_matches', {}),
                'cost_centers': highlighting_data.get('fuzzy_cost_center_matches', {}),
                'tasks': highlighting_data.get('fuzzy_task_matches', {})
            }
        }
        
        # Add highlighting flags to individual employees for frontend highlighting
        employees = extraction_result.get('employees', [])
        for employee in employees:
            employee_name = employee.get('name', '').strip()
            
            # Check if this employee name is new
            is_new_name = any(
                item['name'] == employee_name 
                for item in highlighting_data.get('new_crew_names', [])
            )
            
            if is_new_name:
                employee['_highlight_new_name'] = True
            
            # Check for fuzzy matches
            if employee_name in highlighting_data.get('fuzzy_crew_matches', {}):
                employee['_highlight_fuzzy_match'] = True
                employee['_fuzzy_match_info'] = highlighting_data['fuzzy_crew_matches'][employee_name]
        
        # Add highlighting flags to headers for cost centers and tasks
        headers = extraction_result.get('table_headers', [])
        highlighted_headers = []
        
        new_cost_centers = [item['cost_center'] for item in highlighting_data.get('new_cost_centers', [])]
        new_tasks = [item['task'] for item in highlighting_data.get('new_tasks', [])]
        
        for header in headers:
            header_info = {'name': header}
            
            # Check if header contains new cost center
            for cost_center in new_cost_centers:
                if header.startswith(cost_center + '_'):
                    header_info['_highlight_new_cost_center'] = True
                    header_info['_new_cost_center'] = cost_center
                    break
            
            # Check if header contains new task
            for task in new_tasks:
                if f'_{task}_' in header:
                    header_info['_highlight_new_task'] = True
                    header_info['_new_task'] = task
                    break
            
            highlighted_headers.append(header_info)
        
        extraction_result['table_headers_with_highlights'] = highlighted_headers
        
        return extraction_result


class CrewManagementService:
    """Service for managing crew member names in company profiles."""
    
    @staticmethod
    def add_crew_member(user, crew_name: str) -> Dict[str, Any]:
        """Add a crew member to the user's company profile."""
        try:
            company_profile = CrewMatchingService._get_or_create_company_profile(user)
            
            # Clean and validate the name
            clean_name = crew_name.strip()
            if len(clean_name) < 2:
                return {'success': False, 'error': 'Name too short'}
            
            # Check if already exists (case insensitive)
            existing_names_lower = [name.lower() for name in company_profile.common_crew_names]
            if clean_name.lower() in existing_names_lower:
                return {'success': False, 'error': 'Name already exists'}
            
            # Add the name
            company_profile.common_crew_names.append(clean_name)
            company_profile.save()
            
            logger.info(f"Added crew member '{clean_name}' for user {user.id}")
            return {'success': True, 'name': clean_name}
            
        except Exception as e:
            logger.error(f"Failed to add crew member: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def remove_crew_member(user, crew_name: str) -> Dict[str, Any]:
        """Remove a crew member from the user's company profile."""
        try:
            company_profile = CrewMatchingService._get_or_create_company_profile(user)
            
            if crew_name in company_profile.common_crew_names:
                company_profile.common_crew_names.remove(crew_name)
                company_profile.save()
                
                logger.info(f"Removed crew member '{crew_name}' for user {user.id}")
                return {'success': True, 'name': crew_name}
            else:
                return {'success': False, 'error': 'Name not found'}
                
        except Exception as e:
            logger.error(f"Failed to remove crew member: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def update_crew_member(user, old_name: str, new_name: str) -> Dict[str, Any]:
        """Update a crew member name in the user's company profile."""
        try:
            company_profile = CrewMatchingService._get_or_create_company_profile(user)
            
            if old_name not in company_profile.common_crew_names:
                return {'success': False, 'error': 'Original name not found'}
            
            # Clean and validate the new name
            clean_new_name = new_name.strip()
            if len(clean_new_name) < 2:
                return {'success': False, 'error': 'New name too short'}
            
            # Check if new name already exists
            existing_names_lower = [name.lower() for name in company_profile.common_crew_names]
            if clean_new_name.lower() in existing_names_lower:
                return {'success': False, 'error': 'New name already exists'}
            
            # Update the name
            index = company_profile.common_crew_names.index(old_name)
            company_profile.common_crew_names[index] = clean_new_name
            company_profile.save()
            
            logger.info(f"Updated crew member '{old_name}' to '{clean_new_name}' for user {user.id}")
            return {'success': True, 'old_name': old_name, 'new_name': clean_new_name}
            
        except Exception as e:
            logger.error(f"Failed to update crew member: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def get_crew_list(user) -> List[str]:
        """Get the list of crew members for a user."""
        try:
            company_profile = CrewMatchingService._get_or_create_company_profile(user)
            return company_profile.common_crew_names
        except Exception as e:
            logger.error(f"Failed to get crew list: {str(e)}")
            return []