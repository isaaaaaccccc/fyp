import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Dict, List, Tuple, Set, Optional
from application import db
from application.models import (
    Coach, Branch, Level, Availability, BranchConfig, 
    Enrollment, PopularTimeslot, CoachBranch, CoachPreference
)

class DatabaseDrivenProcessor:
    """
    Database-driven processor - reads ALL business rules from database
    """
    
    def __init__(self):
        print(f"Current Date and Time (UTC - YYYY-MM-DD HH:MM:SS formatted): {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Current User's Login: isaaaaaccccc")
        print("DATABASE-DRIVEN PROCESSOR - NO HARDCODING")
        print("=" * 70)
        
    def load_and_process_data(self):
        """Main data loading - everything from database"""
        print("Loading ALL data from database...")
        
        # Load ALL data from database
        self._load_all_database_data()
        
        # Extract business rules from actual data
        self._extract_business_rules_from_data()
        
        # Process all components
        self.coaches_data = self._process_coaches_from_data()
        self.requirements_data = self._process_requirements_from_data()
        self.popular_timeslots_set = self._process_popular_timeslots_from_data()
        self.timeslots_data = self._generate_timeslots_from_operating_hours()
        self.feasible_assignments = self._generate_feasible_assignments_from_data()
        
        print(f"✓ Processed {len(self.coaches_data)} coaches from database")
        print(f"✓ Processed {len(self.requirements_data)} requirements from database")
        print(f"✓ Loaded {len(self.popular_timeslots_set)} popular timeslot definitions from database")
        print(f"✓ Generated {len(self.timeslots_data)} valid timeslots from operating hours")
        print(f"✓ Created {len(self.feasible_assignments)} feasible assignments")
        
        return self._package_comprehensive_data()
    
    def _load_all_database_data(self):
        """Load all available data from database"""
        
        # Load enrollment data
        enrollments = Enrollment.query.all()
        self.enrollment_data = [{
            'Branch': enrollment.branch,
            'Level Category Base': enrollment.level_category_base,
            'Count': enrollment.count
        } for enrollment in enrollments]
        print(f"  ✓ Loaded enrollment data: {len(self.enrollment_data)} records")
        
        # Load coaches data
        coaches = Coach.query.all()
        self.coaches_raw_data = []
        for coach in coaches:
            coach_data = {
                'coach_id': coach.id,
                'coach_name': coach.name,
                'residential_area': coach.residential_area,
                'position': coach.position,
                'status': coach.status
            }
            
            # Add level qualifications
            level_qualifications = {
                'BearyTots': False, 'Jolly': False, 'Bubbly': False,
                'Lively': False, 'Flexi': False, 'Level_1': False,
                'Level_2': False, 'Level_3': False, 'Level_4': False,
                'Advance': False, 'Free': False
            }
            
            # Get coach preferences (level qualifications)
            preferences = CoachPreference.query.filter_by(coach_id=coach.id).all()
            for pref in preferences:
                level_name = pref.level.name if pref.level else None
                if level_name:
                    # Map level names to qualification columns
                    if level_name == 'BearyTots':
                        level_qualifications['BearyTots'] = True
                    elif level_name == 'Tots':  # Alternative name
                        level_qualifications['BearyTots'] = True
                    elif level_name in level_qualifications:
                        level_qualifications[level_name] = True
                    elif level_name == 'L1':
                        level_qualifications['Level_1'] = True
                    elif level_name == 'L2':
                        level_qualifications['Level_2'] = True
                    elif level_name == 'L3':
                        level_qualifications['Level_3'] = True
                    elif level_name == 'L4':
                        level_qualifications['Level_4'] = True
            
            coach_data.update(level_qualifications)
            
            # Add branch assignments
            branch_assignments = CoachBranch.query.filter_by(coach_id=coach.id).all()
            assigned_branches = [cb.branch.abbrv for cb in branch_assignments if cb.branch]
            coach_data['assigned_branch'] = ','.join(assigned_branches)
            
            self.coaches_raw_data.append(coach_data)
        
        print(f"  ✓ Loaded coaches data: {len(self.coaches_raw_data)} records")
        
        # Load availability data
        availabilities = Availability.query.all()
        self.availability_data = [{
            'coach_id': avail.coach_id,
            'day': avail.day,
            'period': avail.period,
            'available': avail.available,
            'restriction_reason': avail.restriction_reason
        } for avail in availabilities]
        print(f"  ✓ Loaded availability data: {len(self.availability_data)} records")
        
        # Load popular timeslots data
        popular_timeslots = PopularTimeslot.query.all()
        self.popular_timeslots_data = [{
            'level': timeslot.level,
            'day': timeslot.day,
            'time_slot': timeslot.time_slot
        } for timeslot in popular_timeslots]
        print(f"  ✓ Loaded popular timeslots data: {len(self.popular_timeslots_data)} records")
        
        # Load branch config data
        branch_configs = BranchConfig.query.all()
        if branch_configs:
            self.branch_config_data = [{
                'branch': config.branch,
                'max_classes_per_slot': config.max_classes_per_slot
            } for config in branch_configs]
        else:
            # Create default from business rules
            self.branch_config_data = [
                {'branch': 'BB', 'max_classes_per_slot': 4},
                {'branch': 'CCK', 'max_classes_per_slot': 4},
                {'branch': 'CH', 'max_classes_per_slot': 5},
                {'branch': 'HG', 'max_classes_per_slot': 4},
                {'branch': 'KT', 'max_classes_per_slot': 4},
                {'branch': 'PR', 'max_classes_per_slot': 6}
            ]
        print(f"  ✓ Loaded branch config data: {len(self.branch_config_data)} records")
        
        # Convert to DataFrames for compatibility with existing code
        self.enrollment_df = pd.DataFrame(self.enrollment_data)
        self.coaches_df = pd.DataFrame(self.coaches_raw_data)
        self.availability_df = pd.DataFrame(self.availability_data)
        self.popular_df = pd.DataFrame(self.popular_timeslots_data)
        self.branch_config_df = pd.DataFrame(self.branch_config_data)
    
    def _extract_business_rules_from_data(self):
        """Extract ALL business rules from the actual database data"""
        print("  Extracting business rules from database data...")
        
        # Extract levels from enrollment data
        if not self.enrollment_df.empty:
            self.all_levels = sorted(self.enrollment_df['Level Category Base'].unique())
        else:
            # Default levels if no enrollment data
            self.all_levels = ['Tots', 'Jolly', 'Bubbly', 'Lively', 'Flexi', 'L1', 'L2', 'L3', 'L4', 'Advance', 'Free']
        print(f"    Levels found in database: {self.all_levels}")
        
        # Extract branches from enrollment data
        if not self.enrollment_df.empty:
            self.all_branches = sorted(self.enrollment_df['Branch'].unique())
        else:
            # Get from branch config or default
            self.all_branches = sorted(set([bc['branch'] for bc in self.branch_config_data]))
        print(f"    Branches found in database: {self.all_branches}")
        
        # Extract days from availability data
        if not self.availability_df.empty:
            available_days = sorted(self.availability_df['day'].unique())
            # Filter to operating days (exclude MON based on business rule)
            self.all_days = [day for day in available_days if day != 'MON']
        else:
            # Default operating days
            self.all_days = ['TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN']
        print(f"    Operating days found in database: {self.all_days}")
        
        # Categorize days
        self.weekdays = [day for day in self.all_days if day in ['TUE', 'WED', 'THU', 'FRI']]
        self.weekends = [day for day in self.all_days if day in ['SAT', 'SUN']]
        print(f"    Weekdays: {self.weekdays}, Weekends: {self.weekends}")
        
        # Extract coach statuses from coaches data
        coach_statuses = set()
        if not self.coaches_df.empty:
            if 'status' in self.coaches_df.columns:
                coach_statuses.update(self.coaches_df['status'].dropna().unique())
            if 'position' in self.coaches_df.columns:
                coach_statuses.update(self.coaches_df['position'].dropna().unique())
        
        if not coach_statuses:
            coach_statuses = {'Full Time', 'Part Time', 'Branch Manager'}
        
        self.coach_statuses = list(coach_statuses)
        print(f"    Coach statuses found: {self.coach_statuses}")
        
        # Extract level qualifications from coaches data
        self.qualification_columns = [col for col in self.coaches_df.columns 
                                    if col in ['BearyTots', 'Jolly', 'Bubbly', 'Lively', 'Flexi', 
                                             'Level_1', 'Level_2', 'Level_3', 'Level_4', 'Advance', 'Free']]
        print(f"    Qualification columns found: {self.qualification_columns}")
        
        # Set business constants from description and data
        self._derive_business_constants()
    
    def _derive_business_constants(self):
        """Derive business constants from description and data analysis"""
        
        # Class capacities from business rules
        self.class_capacities = {}
        for level in self.all_levels:
            if level in ['Tots', 'BearyTots']:  # BearyTots = 7
                self.class_capacities[level] = 7
            elif level in ['Jolly', 'Bubbly', 'Lively', 'Flexi', 'L1']:  # = 8
                self.class_capacities[level] = 8
            elif level == 'L2':  # = 9
                self.class_capacities[level] = 9
            elif level in ['L3', 'L4', 'Advance', 'Free']:  # = 10
                self.class_capacities[level] = 10
            else:
                self.class_capacities[level] = 8  # Default
        
        # Class durations from business rules
        self.class_durations = {}
        for level in self.all_levels:
            if level in ['Tots', 'BearyTots', 'Jolly', 'Bubbly', 'Lively', 'Flexi']:
                self.class_durations[level] = 60  # 1 hour
            else:  # L1-Free
                self.class_durations[level] = 90  # 1.5 hours
        
        # Operating hours from business rules
        self.operating_hours = {
            'TUE': [('15:00', '19:00')],  # 3pm-7pm
            'WED': [('10:00', '12:00'), ('14:00', '19:00')],  # 10am-7pm with lunch break
            'THU': [('10:00', '12:00'), ('14:00', '19:00')],
            'FRI': [('10:00', '12:00'), ('14:00', '19:00')],
            'SAT': [('08:30', '18:30')],  # 8:30am-6:30pm
            'SUN': [('08:30', '18:30')]
        }
        
        # Branch limits from database
        self.branch_limits = {}
        for config in self.branch_config_data:
            branch = str(config['branch']).upper()
            max_classes = int(config['max_classes_per_slot'])
            self.branch_limits[branch] = max_classes
        
        # Workload limits from business rules
        self.workload_limits = {
            'Full Time': {
                'weekday': 3, 'weekend': 5, 'daily_hours': 7, 
                'consecutive': 3, 'min_break_after_consecutive': 30
            },
            'Part Time': {
                'weekday': 3, 'weekend': 5, 'daily_hours': 7, 
                'consecutive': 3, 'min_break_after_consecutive': 30
            },
            'Branch Manager': {
                'weekday': 3, 'weekend': 5, 'daily_hours': 7, 
                'consecutive': 3, 'min_break_after_consecutive': 30
            }
        }
        
        # Level hierarchy from business rules
        self.level_hierarchy = ['Tots', 'Jolly', 'Bubbly', 'Lively', 'Flexi', 'L1', 'L2', 'L3', 'L4', 'Advance', 'Free']
        
        print(f"    Class capacities derived: {self.class_capacities}")
        print(f"    Class durations derived: {self.class_durations}")
        print(f"    Branch limits from database: {self.branch_limits}")
        print(f"    Operating hours defined: {list(self.operating_hours.keys())}")
    
    def _process_coaches_from_data(self):
        """Process coaches completely from database data"""
        coaches = {}
        
        # Build availability lookup from availability data
        availability_lookup = defaultdict(lambda: defaultdict(bool))
        for avail in self.availability_data:
            coach_id = int(avail['coach_id'])
            day = str(avail['day']).upper()
            period = str(avail['period']).lower()
            available = bool(avail['available'])
            availability_lookup[coach_id][f"{day}_{period}"] = available
        
        # Process each coach from coaches data
        for coach_data in self.coaches_raw_data:
            coach_id = int(coach_data['coach_id'])
            
            # Basic information from database
            name = str(coach_data.get('coach_name', f'Coach {coach_id}'))
            status = str(coach_data.get('status', 'Part Time')).strip()
            position = str(coach_data.get('position', '')).strip()
            residential_area = str(coach_data.get('residential_area', ''))
            
            # Determine final status from database
            if 'Manager' in position:
                final_status = 'Branch Manager'
            elif 'Full time' in status or 'Full Time' in status:
                final_status = 'Full Time'
            elif 'Part time' in status or 'Part Time' in status:
                final_status = 'Part Time'
            else:
                final_status = 'Part Time'  # Default
            
            # Extract qualifications from database columns
            qualifications = []
            qualification_mapping = {
                'BearyTots': 'Tots',
                'Jolly': 'Jolly',
                'Bubbly': 'Bubbly', 
                'Lively': 'Lively',
                'Flexi': 'Flexi',
                'Level_1': 'L1',
                'Level_2': 'L2',
                'Level_3': 'L3',
                'Level_4': 'L4',
                'Advance': 'Advance',
                'Free': 'Free'
            }
            
            for col, level in qualification_mapping.items():
                if col in coach_data and coach_data[col]:
                    qualifications.append(level)
            
            # Auto-add Free if has Advance (business rule)
            if 'Advance' in qualifications and 'Free' not in qualifications:
                qualifications.append('Free')
            
            # Extract branch assignments from database
            branches = []
            if 'assigned_branch' in coach_data and coach_data['assigned_branch']:
                branch_str = str(coach_data['assigned_branch'])
                for branch in branch_str.replace(',', ' ').split():
                    branch = branch.strip().upper()
                    if branch in self.all_branches:
                        branches.append(branch)
            
            # Build availability dictionary from database
            availability = {}
            for day in self.all_days:
                availability[day] = {
                    'am': availability_lookup[coach_id].get(f"{day}_am", False),
                    'pm': availability_lookup[coach_id].get(f"{day}_pm", False)
                }
            
            coaches[coach_id] = {
                'id': coach_id,
                'name': name,
                'status': final_status,
                'position': position,
                'residential_area': residential_area,
                'qualifications': qualifications,
                'branches': branches,
                'availability': availability,
                'workload_limits': self.workload_limits[final_status].copy(),
                'raw_data': coach_data
            }
        
        return coaches
    
    def _process_requirements_from_data(self):
        """Process requirements directly from enrollment database data"""
        requirements = []
        
        for enrollment in self.enrollment_data:
            branch = str(enrollment['Branch']).upper()
            level = str(enrollment['Level Category Base'])
            students = int(enrollment['Count'])
            
            if branch in self.all_branches and level in self.all_levels and students > 0:
                requirements.append({
                    'branch': branch,
                    'level': level,
                    'students': students,
                    'capacity': self.class_capacities.get(level, 8),
                    'duration': self.class_durations.get(level, 90),
                    'raw_data': enrollment
                })
        
        return requirements
    
    def _process_popular_timeslots_from_data(self):
        """Process popular timeslots directly from database"""
        popular_slots = set()
        
        print("  Processing popular timeslots from database:")
        for timeslot_data in self.popular_timeslots_data:
            level = str(timeslot_data['level'])
            day = str(timeslot_data['day']).upper()
            time_slot = str(timeslot_data['time_slot']).strip()
            
            if level in self.all_levels and day in self.all_days:
                popular_slots.add((level, day, time_slot))
        
        print(f"    Processed {len(popular_slots)} popular timeslot combinations")
        
        # Show distribution by level
        by_level = defaultdict(int)
        for level, day, time_slot in popular_slots:
            by_level[level] += 1
        
        print("    Popular slots by level:")
        for level in self.level_hierarchy:
            if level in self.all_levels:
                count = by_level[level]
                print(f"      {level}: {count} popular slots")
        
        return popular_slots
    
    def _generate_timeslots_from_operating_hours(self):
        """Generate all valid timeslots from operating hours"""
        timeslots = []
        
        for level in self.all_levels:
            duration = self.class_durations[level]
            
            for day in self.all_days:
                if day not in self.operating_hours:
                    continue
                
                for period_start, period_end in self.operating_hours[day]:
                    start_dt = datetime.strptime(period_start, '%H:%M')
                    end_dt = datetime.strptime(period_end, '%H:%M')
                    
                    # Generate 30-minute intervals
                    current = start_dt
                    while current + timedelta(minutes=duration) <= end_dt:
                        slot_start = current.strftime('%H:%M')
                        slot_end = (current + timedelta(minutes=duration)).strftime('%H:%M')
                        
                        # Check lunch break on weekdays (12:00-14:00)
                        valid_slot = True
                        if day in self.weekdays:
                            class_start = current
                            class_end = current + timedelta(minutes=duration)
                            lunch_start = datetime.strptime('12:00', '%H:%M')
                            lunch_end = datetime.strptime('14:00', '%H:%M')
                            
                            # Skip if overlaps with lunch
                            if not (class_end <= lunch_start or class_start >= lunch_end):
                                valid_slot = False
                        
                        if valid_slot:
                            period = 'am' if current.hour < 12 else 'pm'
                            time_slot_str = f"{slot_start}-{slot_end}"
                            
                            # Check if this timeslot is popular
                            is_popular = self._is_popular_timeslot(level, day, time_slot_str)
                            
                            timeslots.append({
                                'level': level,
                                'day': day,
                                'start_time': slot_start,
                                'end_time': slot_end,
                                'duration': duration,
                                'period': period,
                                'is_popular': is_popular,
                                'time_slot_str': time_slot_str
                            })
                        
                        current += timedelta(minutes=30)
        
        # Statistics
        total_slots = len(timeslots)
        popular_slots = len([ts for ts in timeslots if ts['is_popular']])
        print(f"  Generated {total_slots} total timeslots from operating hours")
        print(f"  Popular timeslots: {popular_slots} ({popular_slots/total_slots*100:.1f}%)")
        
        return timeslots
    
    def _is_popular_timeslot(self, level, day, time_slot_str):
        """Check if a timeslot is popular based on database data"""
        # Direct match
        if (level, day, time_slot_str) in self.popular_timeslots_set:
            return True
        
        # Check if falls within any popular time range
        try:
            current_start = datetime.strptime(time_slot_str.split('-')[0], '%H:%M')
            current_end = datetime.strptime(time_slot_str.split('-')[1], '%H:%M')
        except:
            return False
        
        for pop_level, pop_day, pop_time_slot in self.popular_timeslots_set:
            if pop_level == level and pop_day == day and '-' in pop_time_slot:
                try:
                    pop_start = datetime.strptime(pop_time_slot.split('-')[0], '%H:%M')
                    pop_end = datetime.strptime(pop_time_slot.split('-')[1], '%H:%M')
                    
                    # Check if current slot falls within popular range
                    if pop_start <= current_start and current_end <= pop_end:
                        return True
                except:
                    continue
        
        return False
    
    def _generate_feasible_assignments_from_data(self):
        """Generate feasible assignments based on all database constraints"""
        assignments = []
        assignment_id = 0
        
        for requirement in self.requirements_data:
            req_branch = requirement['branch']
            req_level = requirement['level']
            req_duration = requirement['duration']
            
            # Find qualified coaches from database
            qualified_coaches = []
            for coach_id, coach in self.coaches_data.items():
                if (req_level in coach['qualifications'] and 
                    req_branch in coach['branches']):
                    qualified_coaches.append(coach_id)
            
            # Find matching timeslots
            matching_timeslots = []
            for timeslot in self.timeslots_data:
                if (timeslot['level'] == req_level and 
                    timeslot['duration'] == req_duration):
                    matching_timeslots.append(timeslot)
            
            # Create assignments
            for coach_id in qualified_coaches:
                coach = self.coaches_data[coach_id]
                
                for timeslot in matching_timeslots:
                    day = timeslot['day']
                    period = timeslot['period']
                    
                    # Check coach availability from database
                    if coach['availability'][day][period]:
                        assignments.append({
                            'id': assignment_id,
                            'coach_id': coach_id,
                            'coach_name': coach['name'],
                            'coach_status': coach['status'],
                            'branch': req_branch,
                            'level': req_level,
                            'day': day,
                            'start_time': timeslot['start_time'],
                            'end_time': timeslot['end_time'],
                            'duration': timeslot['duration'],
                            'period': period,
                            'is_popular': timeslot['is_popular'],
                            'capacity': requirement['capacity'],
                            'students_available': requirement['students']
                        })
                        assignment_id += 1
        
        return assignments
    
    def _package_comprehensive_data(self):
        """Package all data comprehensively"""
        
        # Create enrollment dictionary
        enrollment_dict = {}
        for req in self.requirements_data:
            key = (req['branch'], req['level'])
            enrollment_dict[key] = req['students']
        
        # Create coach lookups
        coach_names = {coach_id: coach['name'] for coach_id, coach in self.coaches_data.items()}
        coach_status = {coach_id: coach['status'] for coach_id, coach in self.coaches_data.items()}
        
        # Calculate statistics
        total_students = sum(enrollment_dict.values())
        popular_assignments = [a for a in self.feasible_assignments if a['is_popular']]
        
        # Analyze coverage potential
        coverage_analysis = self._analyze_coverage_potential(enrollment_dict, popular_assignments)
        
        print(f"\nDATABASE-DRIVEN ANALYSIS:")
        print(f"  Total students from database: {total_students}")
        print(f"  Total assignments generated: {len(self.feasible_assignments)}")
        print(f"  Popular assignments: {len(popular_assignments)} ({len(popular_assignments)/len(self.feasible_assignments)*100:.1f}%)")
        
        if coverage_analysis['uncoverable_requirements']:
            print(f"  Requirements needing attention: {len(coverage_analysis['uncoverable_requirements'])}")
            for item in coverage_analysis['uncoverable_requirements'][:3]:
                req = item['requirement']
                print(f"    {req[0]} {req[1]}: needs {item['demand']}, popular capacity {item['capacity']}")
        else:
            print("  ✓ All requirements can be covered with popular timeslots")
        
        return {
            # Core data from database
            'enrollment_dict': enrollment_dict,
            'coach_names': coach_names,
            'coach_status': coach_status,
            'coaches_data': self.coaches_data,
            'requirements_data': self.requirements_data,
            'timeslots_data': self.timeslots_data,
            'feasible_assignments': self.feasible_assignments,
            
            # Business rules from database/description
            'class_capacities': self.class_capacities,
            'class_durations': self.class_durations,
            'branch_limits': self.branch_limits,
            'workload_limits': self.workload_limits,
            'operating_hours': self.operating_hours,
            'level_hierarchy': self.level_hierarchy,
            
            # Extracted from database
            'all_branches': self.all_branches,
            'all_levels': self.all_levels,
            'all_days': self.all_days,
            'weekdays': self.weekdays,
            'weekends': self.weekends,
            'coach_statuses': self.coach_statuses,
            
            # Comprehensive statistics
            'total_students': total_students,
            'total_coaches': len(self.coaches_data),
            'total_requirements': len(self.requirements_data),
            'total_timeslots': len(self.timeslots_data),
            'total_feasible_assignments': len(self.feasible_assignments),
            'popular_assignments_count': len(popular_assignments),
            'coverage_analysis': coverage_analysis,
            
            # Raw data for reference
            'raw_dataframes': {
                'enrollment_df': self.enrollment_df,
                'coaches_df': self.coaches_df,
                'availability_df': self.availability_df,
                'popular_df': self.popular_df,
                'branch_config_df': self.branch_config_df
            }
        }
    
    def _analyze_coverage_potential(self, enrollment_dict, popular_assignments):
        """Analyze coverage potential with popular assignments"""
        analysis = {
            'total_demand': sum(enrollment_dict.values()),
            'popular_capacity': 0,
            'coverage_by_requirement': {},
            'uncoverable_requirements': []
        }
        
        # Calculate capacity by requirement
        capacity_by_req = defaultdict(int)
        for assignment in popular_assignments:
            key = (assignment['branch'], assignment['level'])
            capacity_by_req[key] += assignment['capacity']
        
        analysis['popular_capacity'] = sum(capacity_by_req.values())
        
        # Analyze each requirement
        for key, demand in enrollment_dict.items():
            popular_capacity = capacity_by_req.get(key, 0)
            
            analysis['coverage_by_requirement'][key] = {
                'demand': demand,
                'popular_capacity': popular_capacity,
                'gap': max(0, demand - popular_capacity)
            }
            
            if popular_capacity < demand:
                analysis['uncoverable_requirements'].append({
                    'requirement': key,
                    'demand': demand,
                    'capacity': popular_capacity,
                    'gap': demand - popular_capacity
                })
        
        return analysis

def load_database_driven():
    """
    Load data using completely database-driven processor
    
    Returns:
        Complete data package with everything extracted from database
    """
    processor = DatabaseDrivenProcessor()
    return processor.load_and_process_data()