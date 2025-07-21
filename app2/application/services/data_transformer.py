"""
Data transformation utilities to convert database models and CSV exports 
into the format expected by the Enhanced Strict Constraint Scheduler.
"""
import pandas as pd
import os
from typing import Dict, List, Any
from collections import defaultdict
from application.models import Coach, Branch, Level, CoachBranch, CoachOffday, CoachPreference
from application import db


class DataTransformer:
    """
    Transforms database data and CSV exports into the format required by
    the Enhanced Strict Constraint Scheduler algorithm.
    """
    
    def __init__(self, data_dir: str = None):
        """Initialize the data transformer."""
        self.data_dir = data_dir
        
        # Level mappings and configurations
        self.LEVEL_MAPPING = {
            'BearyTots': 'Tots', 'Bearytots': 'Tots',
            'Level 1': 'L1', 'Level 2': 'L2', 'Level 3': 'L3', 'Level 4': 'L4',
            'Adv': 'Advance', 'Advanced': 'Advance'
        }
        
        self.CLASS_CAPACITIES = {
            'Tots': 7, 'Jolly': 8, 'Bubbly': 8, 'Lively': 8, 'Flexi': 8, 'L1': 8,
            'L2': 9, 'L3': 10, 'L4': 10, 'Advance': 10, 'Free': 10
        }
        
        self.CLASS_DURATIONS = {
            'Tots': 60, 'Jolly': 60, 'Bubbly': 60, 'Lively': 60, 'Flexi': 60,
            'L1': 90, 'L2': 90, 'L3': 90, 'L4': 90, 'Advance': 90, 'Free': 90
        }
        
        self.BRANCH_LIMITS = {'BB': 4, 'CCK': 4, 'CH': 5, 'HG': 4, 'KT': 4, 'PR': 6}
        
        # Popular time slots
        self.POPULAR_TIMESLOTS = {
            'weekday': ['15:30', '16:00', '16:30', '17:00', '17:30'],
            'weekend': ['09:00', '09:30', '10:00', '10:30', '11:00', '14:00', '14:30', '15:00', '15:30']
        }
    
    def transform_from_database(self) -> Dict[str, Any]:
        """
        Transform data directly from database models into enhanced algorithm format.
        
        Returns:
            Dict containing all required data for the enhanced scheduler
        """
        print("Transforming data from database models...")
        
        # Get all data from database
        coaches = db.session.query(Coach).all()
        branches = db.session.query(Branch).all()
        levels = db.session.query(Level).all()
        
        # Transform coaches data
        coaches_data = self._transform_coaches_data(coaches)
        
        # Transform enrollment data (generate sample data based on levels and branches)
        enrollment_dict = self._generate_enrollment_data(branches, levels)
        
        # Transform availability data
        availability_data = self._transform_availability_data(coaches)
        
        # Create enhanced data structure
        enhanced_data = {
            'enrollment_dict': enrollment_dict,
            'coaches_data': coaches_data,
            'availability_data': availability_data,
            'feasible_assignments': self._generate_feasible_assignments(coaches_data, enrollment_dict),
            'class_capacities': self.CLASS_CAPACITIES,
            'branch_limits': self.BRANCH_LIMITS,
            'popular_timeslots': self.POPULAR_TIMESLOTS,
            'operating_hours': {
                'weekday': {'start': '15:30', 'end': '21:00'},
                'weekend': {'start': '09:00', 'end': '18:00'}
            }
        }
        
        print(f"Transformed data: {len(coaches_data)} coaches, {len(enrollment_dict)} branches")
        return enhanced_data
    
    def transform_from_csv(self) -> Dict[str, Any]:
        """
        Transform data from CSV files into enhanced algorithm format.
        
        Returns:
            Dict containing all required data for the enhanced scheduler
        """
        if not self.data_dir or not os.path.exists(self.data_dir):
            raise ValueError(f"Invalid data directory: {self.data_dir}")
        
        print(f"Transforming data from CSV files in {self.data_dir}...")
        
        # Load CSV files
        coaches_df = self._load_csv_safe('coaches_df.csv')
        availability_df = self._load_csv_safe('availability_df.csv') 
        enrollment_df = self._load_csv_safe('enrollment_counts.csv')
        branch_config_df = self._load_csv_safe('branch_config.csv')
        
        # Transform data
        coaches_data = self._transform_coaches_from_csv(coaches_df)
        enrollment_dict = self._transform_enrollment_from_csv(enrollment_df)
        availability_data = self._transform_availability_from_csv(availability_df)
        branch_limits = self._transform_branch_limits_from_csv(branch_config_df)
        
        # Create enhanced data structure
        enhanced_data = {
            'enrollment_dict': enrollment_dict,
            'coaches_data': coaches_data,
            'availability_data': availability_data,
            'feasible_assignments': self._generate_feasible_assignments(coaches_data, enrollment_dict),
            'class_capacities': self.CLASS_CAPACITIES,
            'branch_limits': branch_limits,
            'popular_timeslots': self.POPULAR_TIMESLOTS,
            'operating_hours': {
                'weekday': {'start': '15:30', 'end': '21:00'},
                'weekend': {'start': '09:00', 'end': '18:00'}
            }
        }
        
        print(f"Transformed CSV data: {len(coaches_data)} coaches, {len(enrollment_dict)} branches")
        return enhanced_data
    
    def _transform_coaches_data(self, coaches: List[Coach]) -> List[Dict[str, Any]]:
        """Transform coach database models to enhanced format."""
        coaches_data = []
        
        for coach in coaches:
            # Get assigned branches
            assigned_branches = [cb.branch.abbrv for cb in coach.assigned_branches]
            primary_branch = assigned_branches[0] if assigned_branches else ''
            
            # Get level preferences
            preferred_levels = {cp.level.name for cp in coach.preferred_levels}
            
            # Create coach data structure  
            coach_data = {
                'coach_id': coach.id,
                'coach_name': coach.name,
                'residential_area': coach.residential_area,
                'assigned_branch': primary_branch,
                'position': coach.position,
                'status': 'Active' if coach.status in ['Full time', 'Part time'] else 'Inactive',  # Normalize status
                'assigned_branches': assigned_branches,
                
                # Level qualifications as boolean columns
                'BearyTots': 'Tots' in preferred_levels,
                'Jolly': 'Jolly' in preferred_levels,
                'Bubbly': 'Bubbly' in preferred_levels,
                'Lively': 'Lively' in preferred_levels,
                'Flexi': 'Flexi' in preferred_levels,
                'Level_1': 'L1' in preferred_levels,
                'Level_2': 'L2' in preferred_levels,
                'Level_3': 'L3' in preferred_levels,
                'Level_4': 'L4' in preferred_levels,
                'Advance': 'Advance' in preferred_levels,
                'Free': 'Free' in preferred_levels,
                
                # Additional metadata
                'workload_limit': self._get_workload_limit(coach.position),
                'off_days': self._get_coach_off_days(coach)
            }
            
            coaches_data.append(coach_data)
        
        return coaches_data
    
    def _transform_availability_data(self, coaches: List[Coach]) -> Dict[str, Dict[str, Dict[str, bool]]]:
        """Transform coach availability from database models."""
        availability_data = {}
        
        days_mapping = {0: 'MON', 1: 'TUE', 2: 'WED', 3: 'THU', 4: 'FRI', 5: 'SAT', 6: 'SUN'}
        
        for coach in coaches:
            coach_name = coach.name
            availability_data[coach_name] = {}
            
            # Get off days for this coach
            off_days = {(od.day, od.am) for od in coach.offdays}
            
            # Create availability for each day
            for day_num, day_name in days_mapping.items():
                availability_data[coach_name][day_name] = {
                    'AM': (day_num, True) not in off_days,
                    'PM': (day_num, False) not in off_days
                }
        
        return availability_data
    
    def _generate_enrollment_data(self, branches: List[Branch], levels: List[Level]) -> Dict[str, Dict[str, int]]:
        """Generate sample enrollment data based on branches and levels."""
        enrollment_dict = {}
        
        # Sample enrollment counts per level (these would come from real enrollment data)
        sample_counts = {
            'Tots': 15, 'Jolly': 25, 'Bubbly': 40, 'Lively': 35, 'Flexi': 45,
            'L1': 60, 'L2': 50, 'L3': 30, 'L4': 20, 'Advance': 10, 'Free': 8
        }
        
        for branch in branches:
            enrollment_dict[branch.abbrv] = {}
            
            for level in levels:
                level_name = level.name
                base_count = sample_counts.get(level_name, 20)
                
                # Add some variation per branch (consistent using hash)
                import random
                random.seed(hash(f"{branch.abbrv}_{level_name}"))
                count = max(1, base_count + random.randint(-10, 10))
                
                enrollment_dict[branch.abbrv][level_name] = count
        
        return enrollment_dict
    
    def _transform_coaches_from_csv(self, coaches_df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Transform coaches data from CSV format."""
        if coaches_df is None or coaches_df.empty:
            return []
        
        coaches_data = []
        
        for _, row in coaches_df.iterrows():
            # Get status and normalize it
            raw_status = row.get('status', 'Full time')
            # Convert employment status to active/inactive status
            status = 'Active' if raw_status in ['Full time', 'Part time'] else 'Inactive'
            
            coach_data = {
                'coach_id': row.get('coach_id'),
                'coach_name': row.get('coach_name'),
                'residential_area': row.get('residential_area', ''),
                'assigned_branch': row.get('assigned_branch', ''),
                'position': row.get('position', 'Full Time'),
                'status': status,  # Use normalized status
                
                # Level qualifications
                'BearyTots': bool(row.get('BearyTots', False)),
                'Jolly': bool(row.get('Jolly', False)),
                'Bubbly': bool(row.get('Bubbly', False)),
                'Lively': bool(row.get('Lively', False)),
                'Flexi': bool(row.get('Flexi', False)),
                'Level_1': bool(row.get('Level_1', False)),
                'Level_2': bool(row.get('Level_2', False)),
                'Level_3': bool(row.get('Level_3', False)),
                'Level_4': bool(row.get('Level_4', False)),
                'Advance': bool(row.get('Advance', False)),
                'Free': bool(row.get('Free', False)),
                
                'workload_limit': self._get_workload_limit(row.get('position', 'Full Time'))
            }
            
            # Ensure coaches have at least some qualifications
            has_qualifications = any([
                coach_data['BearyTots'], coach_data['Jolly'], coach_data['Bubbly'],
                coach_data['Lively'], coach_data['Flexi'], coach_data['Level_1'],
                coach_data['Level_2'], coach_data['Level_3'], coach_data['Level_4'],
                coach_data['Advance'], coach_data['Free']
            ])
            
            # If no qualifications, set some default ones
            if not has_qualifications:
                coach_data['Level_1'] = True
                coach_data['Level_2'] = True
                coach_data['Jolly'] = True
                coach_data['Bubbly'] = True
            
            # Ensure coaches have an assigned branch
            if not coach_data['assigned_branch']:
                # Assign to a default branch or skip
                available_branches = ['BB', 'CCK', 'CH', 'HG', 'KT', 'PR']
                coach_data['assigned_branch'] = available_branches[len(coaches_data) % len(available_branches)]
            
            coaches_data.append(coach_data)
        
        return coaches_data
    
    def _transform_enrollment_from_csv(self, enrollment_df: pd.DataFrame) -> Dict[str, Dict[str, int]]:
        """Transform enrollment data from CSV format."""
        if enrollment_df is None or enrollment_df.empty:
            return {}
        
        enrollment_dict = defaultdict(dict)
        
        for _, row in enrollment_df.iterrows():
            branch = row.get('Branch')
            level = row.get('Level Category Base')
            count = int(row.get('Count', 0))
            
            if branch and level:
                enrollment_dict[branch][level] = count
        
        return dict(enrollment_dict)
    
    def _transform_availability_from_csv(self, availability_df: pd.DataFrame) -> Dict[str, Dict[str, Dict[str, bool]]]:
        """Transform availability data from CSV format."""
        if availability_df is None or availability_df.empty:
            return {}
        
        availability_data = defaultdict(lambda: defaultdict(dict))
        
        for _, row in availability_df.iterrows():
            coach_name = row.get('coach_name')
            day = row.get('day')
            period = row.get('period')
            available = bool(row.get('available', True))
            
            if coach_name and day and period:
                availability_data[coach_name][day][period] = available
        
        return dict(availability_data)
    
    def _transform_branch_limits_from_csv(self, branch_config_df: pd.DataFrame) -> Dict[str, int]:
        """Transform branch limits from CSV format."""
        if branch_config_df is None or branch_config_df.empty:
            return self.BRANCH_LIMITS
        
        branch_limits = {}
        
        for _, row in branch_config_df.iterrows():
            branch = row.get('branch')
            limit = int(row.get('max_classes_per_slot', 4))
            
            if branch:
                branch_limits[branch] = limit
        
        return branch_limits
    
    def _generate_feasible_assignments(self, coaches_data: List[Dict[str, Any]], 
                                     enrollment_dict: Dict[str, Dict[str, int]]) -> List[Dict[str, Any]]:
        """Generate all feasible coach-branch-level-time assignments."""
        feasible_assignments = []
        
        for coach_data in coaches_data:
            coach_id = coach_data.get('coach_id')
            coach_name = coach_data.get('coach_name')
            assigned_branch = coach_data.get('assigned_branch')
            status = coach_data.get('status', 'Active')
            
            # Skip inactive coaches
            if status != 'Active':
                continue
            
            # Get qualified levels
            qualified_levels = self._get_qualified_levels_from_data(coach_data)
            
            # Get branch enrollment data
            branch_enrollments = enrollment_dict.get(assigned_branch, {})
            
            # Generate assignments for each qualified level with enrollment
            for level in qualified_levels:
                if level in branch_enrollments and branch_enrollments[level] > 0:
                    enrollment_count = branch_enrollments[level]
                    
                    # Create assignment record
                    assignment = {
                        'coach_id': coach_id,
                        'coach_name': coach_name,
                        'branch': assigned_branch,
                        'level': level,
                        'enrollment': enrollment_count,
                        'duration': self.CLASS_DURATIONS.get(level, 90),
                        'capacity': self.CLASS_CAPACITIES.get(level, 8)
                    }
                    
                    feasible_assignments.append(assignment)
        
        return feasible_assignments
    
    def _get_qualified_levels_from_data(self, coach_data: Dict[str, Any]) -> List[str]:
        """Extract qualified levels from coach data."""
        qualified_levels = []
        
        level_mappings = {
            'BearyTots': 'Tots', 'Jolly': 'Jolly', 'Bubbly': 'Bubbly',
            'Lively': 'Lively', 'Flexi': 'Flexi', 'Level_1': 'L1',
            'Level_2': 'L2', 'Level_3': 'L3', 'Level_4': 'L4',
            'Advance': 'Advance', 'Free': 'Free'
        }
        
        for col, level in level_mappings.items():
            if coach_data.get(col, False):
                qualified_levels.append(level)
        
        # Default qualifications if none specified
        if not qualified_levels:
            qualified_levels = ['L1', 'L2', 'Jolly', 'Bubbly']
        
        return qualified_levels
    
    def _get_workload_limit(self, position: str) -> Dict[str, int]:
        """Get workload limits based on position."""
        limits = {
            'Full Time': {'weekly': 25, 'weekend_daily': 5, 'weekday_daily': 3},
            'Part Time': {'weekly': 15, 'weekend_daily': 5, 'weekday_daily': 3},
            'Manager': {'weekly': 3, 'weekend_daily': 2, 'weekday_daily': 2}
        }
        
        return limits.get(position, limits['Full Time'])
    
    def _get_coach_off_days(self, coach: Coach) -> List[Dict[str, Any]]:
        """Get coach off days information."""
        off_days = []
        
        days_mapping = {0: 'MON', 1: 'TUE', 2: 'WED', 3: 'THU', 4: 'FRI', 5: 'SAT', 6: 'SUN'}
        
        for off_day in coach.offdays:
            off_days.append({
                'day': days_mapping.get(off_day.day, 'UNKNOWN'),
                'period': 'AM' if off_day.am else 'PM',
                'reason': off_day.reason
            })
        
        return off_days
    
    def _load_csv_safe(self, filename: str) -> pd.DataFrame:
        """Safely load a CSV file, return None if not found."""
        filepath = os.path.join(self.data_dir, filename)
        
        try:
            if os.path.exists(filepath):
                return pd.read_csv(filepath)
            else:
                print(f"Warning: CSV file not found: {filepath}")
                return None
        except Exception as e:
            print(f"Error loading CSV file {filepath}: {e}")
            return None
    
    def validate_enhanced_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate the transformed data structure."""
        validation = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'summary': {}
        }
        
        # Check required keys
        required_keys = ['enrollment_dict', 'coaches_data', 'class_capacities', 'branch_limits']
        for key in required_keys:
            if key not in data:
                validation['errors'].append(f"Missing required key: {key}")
                validation['valid'] = False
        
        # Validate coaches data
        coaches_data = data.get('coaches_data', [])
        if not coaches_data:
            validation['errors'].append("No coaches data found")
            validation['valid'] = False
        
        # Validate enrollment data
        enrollment_dict = data.get('enrollment_dict', {})
        if not enrollment_dict:
            validation['warnings'].append("No enrollment data found")
        
        # Generate summary
        validation['summary'] = {
            'total_coaches': len(coaches_data),
            'active_coaches': len([c for c in coaches_data if c.get('status') == 'Active']),
            'branches_with_enrollment': len(enrollment_dict),
            'total_enrollments': sum(sum(levels.values()) for levels in enrollment_dict.values()),
            'feasible_assignments': len(data.get('feasible_assignments', []))
        }
        
        return validation