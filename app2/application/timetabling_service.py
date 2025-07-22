"""
Timetabling Algorithm Service Module
Enhanced with strict constraint scheduler and database persistence
"""

import pandas as pd
import json
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Dict, List, Tuple, Set, Optional
from application import db
from application.models import (
    Coach, Branch, Level, CoachBranch, CoachOffday, CoachPreference,
    PopularTimeslots, EnrollmentCounts, BranchConfig, CoachAvailability,
    Timetable, TimetableAssignment, TimetableStatistics
)
from application.enhanced_scheduler import EnhancedStrictConstraintScheduler


class TimetablingService:
    """Service for generating and managing timetables using enhanced algorithms"""
    
    def __init__(self):
        self.scheduler = EnhancedStrictConstraintScheduler()
    
    def generate_timetable(self, save_to_db: bool = False, timetable_name: str = None) -> Dict:
        """Main method to generate timetable using enhanced algorithm"""
        try:
            # Load data from database
            coaches_data = self._load_coaches_from_db()
            requirements_data = self._load_requirements_from_db()
            popular_timeslots = self._load_popular_timeslots_from_db()
            branch_configs = self._load_branch_configs_from_db()
            
            print(f"Loaded {len(coaches_data)} coaches, {len(requirements_data)} requirements")
            
            # Generate schedule using enhanced algorithm
            schedule = self.scheduler.generate_schedule(
                coaches_data, requirements_data, popular_timeslots, branch_configs
            )
            
            # Save to database if requested
            if save_to_db:
                timetable_id = self.save_timetable_to_db(schedule, timetable_name)
                schedule['timetable_id'] = timetable_id
            
            # Add statistics to response
            stats = self.scheduler.get_statistics()
            if stats:
                schedule['statistics'] = {
                    'total_assignments': stats.total_assignments,
                    'coverage_percentage': round(stats.coverage_percentage, 2),
                    'popular_slot_coverage': round(stats.popular_slot_coverage, 2),
                    'constraint_violations': stats.constraint_violations,
                    'coach_utilization': {k: round(v, 2) for k, v in stats.coach_utilization.items()},
                    'branch_distribution': stats.branch_distribution,
                    'level_distribution': stats.level_distribution
                }
                
                violations = self.scheduler.get_constraint_violations()
                if violations:
                    schedule['warnings'] = violations
            
            return schedule
            
        except Exception as e:
            print(f"Error in enhanced timetabling: {e}")
            return self._get_fallback_schedule()
    
    def save_timetable_to_db(self, schedule_data: Dict, name: str = None) -> int:
        """Save generated timetable to database"""
        if not name:
            name = f"Generated Schedule {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        
        # Create timetable record
        stats = self.scheduler.get_statistics()
        timetable = Timetable(
            name=name,
            description=f"Enhanced algorithm schedule with {stats.total_assignments if stats else 0} assignments",
            total_assignments=stats.total_assignments if stats else 0,
            coverage_percentage=stats.coverage_percentage if stats else 0,
            popular_slot_coverage=stats.popular_slot_coverage if stats else 0,
            constraint_violations=stats.constraint_violations if stats else 0
        )
        
        db.session.add(timetable)
        db.session.flush()  # Get the ID
        
        # Create assignment records
        for branch, branch_data in schedule_data.items():
            if branch in ['statistics', 'warnings', 'timetable_id']:
                continue
                
            schedule = branch_data.get('schedule', {})
            for day, day_schedule in schedule.items():
                # Map day names back to abbreviations
                day_abbrev = self._map_day_name_to_abbrev(day)
                
                for coach_name, classes in day_schedule.items():
                    # Find coach ID
                    coach = Coach.query.filter_by(name=coach_name).first()
                    if not coach:
                        continue
                    
                    for class_info in classes:
                        # Convert start_time back to HH:MM format
                        start_time_str = class_info['start_time']
                        if len(start_time_str) == 4:
                            start_time = f"{start_time_str[:2]}:{start_time_str[2:]}"
                        else:
                            start_time = start_time_str
                        
                        # Calculate end time
                        start_dt = datetime.strptime(start_time, '%H:%M')
                        duration_minutes = class_info['duration'] * 30  # Convert slots to minutes
                        end_dt = start_dt + timedelta(minutes=duration_minutes)
                        end_time = end_dt.strftime('%H:%M')
                        
                        assignment = TimetableAssignment(
                            timetable_id=timetable.id,
                            coach_id=coach.id,
                            branch=branch,
                            level=class_info['name'],
                            day=day_abbrev,
                            start_time=start_time,
                            end_time=end_time,
                            duration=duration_minutes,
                            students_count=class_info.get('students', 0),
                            is_popular=class_info.get('is_popular', False),
                            priority_score=class_info.get('priority_score', 0.0)
                        )
                        db.session.add(assignment)
        
        # Save detailed statistics
        if stats:
            statistics = TimetableStatistics(
                timetable_id=timetable.id,
                coach_utilization=json.dumps(stats.coach_utilization),
                branch_distribution=json.dumps(stats.branch_distribution),
                level_distribution=json.dumps(stats.level_distribution),
                constraint_violations_detail=json.dumps(self.scheduler.get_constraint_violations())
            )
            db.session.add(statistics)
        
        db.session.commit()
        return timetable.id
    
    def load_timetable_from_db(self, timetable_id: int) -> Dict:
        """Load a saved timetable from database"""
        timetable = Timetable.query.get(timetable_id)
        if not timetable:
            return {}
        
        # Build schedule structure
        schedule = defaultdict(lambda: {'coaches': set(), 'schedule': defaultdict(lambda: defaultdict(list))})
        
        for assignment in timetable.assignments:
            branch = assignment.branch
            day = self._map_day_abbrev_to_name(assignment.day)
            coach_name = assignment.coach.name
            
            schedule[branch]['coaches'].add(coach_name)
            
            # Convert back to frontend format
            start_time_formatted = assignment.start_time.replace(':', '')
            duration_slots = assignment.duration // 30
            
            schedule[branch]['schedule'][day][coach_name].append({
                'name': assignment.level,
                'start_time': start_time_formatted,
                'duration': duration_slots,
                'students': assignment.students_count,
                'is_popular': assignment.is_popular
            })
        
        # Convert coaches sets to sorted lists
        result = {}
        for branch, branch_data in schedule.items():
            result[branch] = {
                'coaches': sorted(list(branch_data['coaches'])),
                'schedule': dict(branch_data['schedule'])
            }
        
        # Add metadata
        result['timetable_id'] = timetable.id
        result['timetable_name'] = timetable.name
        result['date_created'] = timetable.date_created.isoformat()
        
        return result
    
    def list_saved_timetables(self) -> List[Dict]:
        """Get list of all saved timetables"""
        timetables = Timetable.query.order_by(Timetable.date_created.desc()).all()
        return [{
            'id': t.id,
            'name': t.name,
            'description': t.description,
            'date_created': t.date_created.isoformat(),
            'date_updated': t.date_updated.isoformat(),
            'is_active': t.is_active,
            'total_assignments': t.total_assignments,
            'coverage_percentage': t.coverage_percentage,
            'algorithm_version': t.algorithm_version
        } for t in timetables]
    
    def delete_timetable(self, timetable_id: int) -> bool:
        """Delete a saved timetable"""
        timetable = Timetable.query.get(timetable_id)
        if timetable:
            db.session.delete(timetable)
            db.session.commit()
            return True
        return False
    
    def set_active_timetable(self, timetable_id: int) -> bool:
        """Set a timetable as the active one"""
        # Deactivate all timetables
        Timetable.query.update({'is_active': False})
        
        # Activate the specified one
        timetable = Timetable.query.get(timetable_id)
        if timetable:
            timetable.is_active = True
            db.session.commit()
            return True
        return False
    
    def _map_day_name_to_abbrev(self, day_name: str) -> str:
        """Map frontend day names to database abbreviations"""
        mapping = {
            'Monday': 'MON', 'Tuesday': 'TUE', 'Wednesday': 'WED',
            'Thursday': 'THU', 'Friday': 'FRI', 'Saturday': 'SAT', 'Sunday': 'SUN'
        }
        return mapping.get(day_name, day_name)
    
    def _map_day_abbrev_to_name(self, day_abbrev: str) -> str:
        """Map database abbreviations to frontend day names"""
        mapping = {
            'MON': 'Monday', 'TUE': 'Tuesday', 'WED': 'Wednesday',
            'THU': 'Thursday', 'FRI': 'Friday', 'SAT': 'Saturday', 'SUN': 'Sunday'
        }
        return mapping.get(day_abbrev, day_abbrev)
    
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
            for offday in coach.offdays:
                day_name = offday.day
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
            class_capacities = {
                'Tots': 7, 'Jolly': 8, 'Bubbly': 8, 'Lively': 8, 'Flexi': 8,
                'L1': 8, 'L2': 9, 'L3': 10, 'L4': 10, 'Advance': 10, 'Free': 10
            }
            class_durations = {
                'Tots': 60, 'Jolly': 60, 'Bubbly': 60, 'Lively': 60, 'Flexi': 60,
                'L1': 90, 'L2': 90, 'L3': 90, 'L4': 90, 'Advance': 90, 'Free': 90
            }
            
            requirements.append({
                'branch': enrollment.branch,
                'level': enrollment.level_category_base,
                'students': enrollment.count,
                'capacity': class_capacities.get(enrollment.level_category_base, 8),
                'duration': class_durations.get(enrollment.level_category_base, 60)
            })
        
        return requirements
    
    def _load_popular_timeslots_from_db(self) -> Set[Tuple]:
        """Load popular timeslots from database"""
        popular_slots = set()
        
        timeslots = PopularTimeslots.query.all()
        for timeslot in timeslots:
            popular_slots.add((timeslot.level, timeslot.day, timeslot.time_slot))
        
        return popular_slots
    
    def _load_branch_configs_from_db(self) -> Dict:
        """Load branch configurations from database"""
        configs = {}
        
        branch_configs = BranchConfig.query.all()
        for config in branch_configs:
            configs[config.branch] = {
                'max_classes_per_slot': config.max_classes_per_slot
            }
        
        return configs
    
    def _get_fallback_schedule(self) -> Dict:
        """Return fallback schedule in case of errors"""
        return {
            'error': 'Enhanced scheduling algorithm encountered an error',
            'BB': {
                'coaches': ['Sample Coach'],
                'schedule': {
                    'Tuesday': {
                        'Sample Coach': [
                            {'name': 'L1', 'start_time': '1530', 'duration': 3, 'students': 8, 'is_popular': False}
                        ]
                    }
                }
            }
        }