"""
Timetabling Algorithm Service Module
Extracted and simplified from timetabling.ipynb
"""

import pandas as pd
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Dict, List, Tuple, Set, Optional
from application import db
from application.models import (
    Coach, Branch, Level, CoachBranch, CoachOffday, CoachPreference,
    PopularTimeslots, EnrollmentCounts, BranchConfig, CoachAvailability
)


class TimetablingService:
    """Service for generating timetables based on database data"""
    
    def __init__(self):
        self.class_capacities = {
            'Tots': 7, 'Jolly': 8, 'Bubbly': 8, 'Lively': 8, 'Flexi': 8,
            'L1': 8, 'L2': 9, 'L3': 10, 'L4': 10, 'Advance': 10, 'Free': 10
        }
        self.class_durations = {
            'Tots': 60, 'Jolly': 60, 'Bubbly': 60, 'Lively': 60, 'Flexi': 60,
            'L1': 90, 'L2': 90, 'L3': 90, 'L4': 90, 'Advance': 90, 'Free': 90
        }
        self.operating_hours = {
            'TUE': [('15:00', '19:00')],
            'WED': [('10:00', '12:00'), ('14:00', '19:00')],
            'THU': [('10:00', '12:00'), ('14:00', '19:00')],
            'FRI': [('10:00', '12:00'), ('14:00', '19:00')],
            'SAT': [('08:30', '18:30')],
            'SUN': [('08:30', '18:30')]
        }
        self.weekdays = ['TUE', 'WED', 'THU', 'FRI']
        self.level_hierarchy = ['Tots', 'Jolly', 'Bubbly', 'Lively', 'Flexi', 'L1', 'L2', 'L3', 'L4', 'Advance', 'Free']
    
    def generate_timetable(self) -> Dict:
        """Main method to generate timetable from database data"""
        try:
            # Load data from database
            coaches_data = self._load_coaches_from_db()
            requirements_data = self._load_requirements_from_db()
            popular_timeslots = self._load_popular_timeslots_from_db()
            
            # Generate timeslots
            timeslots_data = self._generate_timeslots()
            
            # Generate feasible assignments
            feasible_assignments = self._generate_feasible_assignments(
                coaches_data, requirements_data, timeslots_data, popular_timeslots
            )
            
            # Create optimized schedule
            schedule = self._create_optimized_schedule(feasible_assignments)
            
            return schedule
            
        except Exception as e:
            print(f"Error generating timetable: {e}")
            return self._get_fallback_schedule()
    
    def _load_coaches_from_db(self) -> Dict:
        """Load coach data from database"""
        coaches_data = {}
        
        coaches = Coach.query.all()
        for coach in coaches:
            # Get assigned branches
            branches = [cb.branch.abbrv for cb in coach.assigned_branches]
            
            # Get qualifications (levels they can teach)
            qualifications = [cp.level.name for cp in coach.preferred_levels]
            
            # Initialize availability as all available by default
            availability = {}
            day_names = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN']
            for day_name in day_names:
                availability[day_name] = {'am': True, 'pm': True}
            
            # Update availability from CoachOffday 
            # Note: offday.day is stored as string day name, offday.am indicates AM/PM period
            for offday in coach.offdays:
                day_name = offday.day  # Already a string like 'MON', 'TUE', etc.
                period = 'am' if offday.am else 'pm'
                if day_name in availability:
                    availability[day_name][period] = False  # False means not available
            
            coaches_data[coach.id] = {
                'id': coach.id,
                'name': coach.name,
                'status': coach.status,
                'position': coach.position,
                'branches': branches,
                'qualifications': qualifications,
                'availability': availability
            }
        
        return coaches_data
    
    def _load_requirements_from_db(self) -> List[Dict]:
        """Load enrollment requirements from database"""
        requirements = []
        
        enrollments = EnrollmentCounts.query.all()
        for enrollment in enrollments:
            requirements.append({
                'branch': enrollment.branch,
                'level': enrollment.level_category_base,
                'students': enrollment.count,
                'capacity': self.class_capacities.get(enrollment.level_category_base, 8),
                'duration': self.class_durations.get(enrollment.level_category_base, 60)
            })
        
        return requirements
    
    def _load_popular_timeslots_from_db(self) -> Set[Tuple]:
        """Load popular timeslots from database"""
        popular_slots = set()
        
        timeslots = PopularTimeslots.query.all()
        for timeslot in timeslots:
            popular_slots.add((timeslot.level, timeslot.day, timeslot.time_slot))
        
        return popular_slots
    
    def _generate_timeslots(self) -> List[Dict]:
        """Generate all valid timeslots based on operating hours"""
        timeslots = []
        
        for level in self.class_capacities.keys():
            duration = self.class_durations[level]
            
            for day, periods in self.operating_hours.items():
                for period_start, period_end in periods:
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
                            
                            timeslots.append({
                                'level': level,
                                'day': day,
                                'start_time': slot_start,
                                'end_time': slot_end,
                                'duration': duration,
                                'period': period,
                                'time_slot_str': time_slot_str
                            })
                        
                        current += timedelta(minutes=30)
        
        return timeslots
    
    def _generate_feasible_assignments(self, coaches_data, requirements_data, 
                                     timeslots_data, popular_timeslots) -> List[Dict]:
        """Generate feasible assignments based on constraints"""
        assignments = []
        assignment_id = 0
        
        for requirement in requirements_data:
            req_branch = requirement['branch']
            req_level = requirement['level']
            req_duration = requirement['duration']
            
            # Find qualified coaches
            qualified_coaches = []
            for coach_id, coach in coaches_data.items():
                if (req_level in coach['qualifications'] and 
                    req_branch in coach['branches']):
                    qualified_coaches.append(coach_id)
            
            # Find matching timeslots
            matching_timeslots = [
                ts for ts in timeslots_data 
                if ts['level'] == req_level and ts['duration'] == req_duration
            ]
            
            # Create assignments
            for coach_id in qualified_coaches:
                coach = coaches_data[coach_id]
                
                for timeslot in matching_timeslots:
                    day = timeslot['day']
                    period = timeslot['period']
                    
                    # Check coach availability
                    if coach['availability'][day][period]:
                        # Check if popular
                        is_popular = (req_level, day, timeslot['time_slot_str']) in popular_timeslots
                        
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
                            'is_popular': is_popular,
                            'capacity': requirement['capacity'],
                            'students_available': requirement['students']
                        })
                        assignment_id += 1
        
        return assignments
    
    def _create_optimized_schedule(self, feasible_assignments) -> Dict:
        """Create optimized schedule from feasible assignments"""
        schedule = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
        
        # Sort assignments by priority: popular first, then by coach status
        status_priority = {
            'Full time': 1, 'Senior Coach': 2, 'Junior Coach': 3, 
            'Admin cum coach': 4, 'Part time': 5, 'Branch Manager': 6
        }
        
        sorted_assignments = sorted(feasible_assignments, key=lambda x: (
            not x['is_popular'],  # Popular first
            status_priority.get(x['coach_status'], 7),  # Then by status
            x['coach_id']  # Then by coach ID for consistency
        ))
        
        used_slots = set()  # Track (coach_id, day, start_time)
        
        # Map day names to match frontend expectations
        day_mapping = {
            'TUE': 'Tuesday', 'WED': 'Wednesday', 'THU': 'Thursday',
            'FRI': 'Friday', 'SAT': 'Saturday', 'SUN': 'Sunday', 'MON': 'Monday'
        }
        
        for assignment in sorted_assignments:
            slot_key = (assignment['coach_id'], assignment['day'], assignment['start_time'])
            
            if slot_key not in used_slots:
                frontend_day = day_mapping.get(assignment['day'], assignment['day'])
                schedule[assignment['branch']][frontend_day][assignment['coach_name']].append({
                    'name': assignment['level'],
                    'start_time': assignment['start_time'].replace(':', ''),
                    'duration': assignment['duration'] // 30  # Convert to 30-min slots
                })
                used_slots.add(slot_key)
        
        # Convert to format expected by frontend
        result = {}
        for branch, branch_schedule in schedule.items():
            result[branch] = {
                'coaches': list(set(coach for day_schedule in branch_schedule.values() 
                               for coach in day_schedule.keys())),
                'schedule': dict(branch_schedule)
            }
        
        return result
    
    def _get_fallback_schedule(self) -> Dict:
        """Return fallback schedule in case of errors"""
        return {
            'CCK': {
                'coaches': ['Sample Coach'],
                'schedule': {
                    'Tuesday': {
                        'Sample Coach': [
                            {'name': 'L1', 'start_time': '1530', 'duration': 3}
                        ]
                    }
                }
            }
        }