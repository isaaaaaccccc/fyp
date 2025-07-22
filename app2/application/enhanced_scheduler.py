"""
Enhanced Strict Constraint Scheduler
Advanced timetabling algorithm with multi-phase optimization and strict constraint validation
"""

import pandas as pd
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from typing import Dict, List, Tuple, Set, Optional, NamedTuple
import random
import copy

class Assignment(NamedTuple):
    """Represents a class assignment"""
    coach_id: int
    coach_name: str
    branch: str
    level: str
    day: str
    start_time: str
    end_time: str
    duration: int
    students_count: int
    is_popular: bool
    priority_score: float

class ScheduleStats(NamedTuple):
    """Statistics for generated schedule"""
    total_assignments: int
    coverage_percentage: float
    coach_utilization: Dict[str, float]
    popular_slot_coverage: float
    constraint_violations: int
    branch_distribution: Dict[str, int]
    level_distribution: Dict[str, int]

class EnhancedStrictConstraintScheduler:
    """
    Advanced timetabling scheduler with strict constraints and multi-phase optimization
    """
    
    def __init__(self):
        # Class configurations
        self.class_capacities = {
            'Tots': 7, 'Jolly': 8, 'Bubbly': 8, 'Lively': 8, 'Flexi': 8,
            'L1': 8, 'L2': 9, 'L3': 10, 'L4': 10, 'Advance': 10, 'Free': 10
        }
        self.class_durations = {
            'Tots': 60, 'Jolly': 60, 'Bubbly': 60, 'Lively': 60, 'Flexi': 60,
            'L1': 90, 'L2': 90, 'L3': 90, 'L4': 90, 'Advance': 90, 'Free': 90
        }
        
        # Operating hours by day
        self.operating_hours = {
            'TUE': [('15:00', '19:00')],
            'WED': [('10:00', '12:00'), ('14:00', '19:00')],
            'THU': [('10:00', '12:00'), ('14:00', '19:00')],
            'FRI': [('10:00', '12:00'), ('14:00', '19:00')],
            'SAT': [('08:30', '18:30')],
            'SUN': [('08:30', '18:30')]
        }
        
        # Constraint parameters
        self.max_classes_per_coach_per_day = 6
        self.max_consecutive_hours = 4
        self.min_break_between_classes = 30  # minutes
        self.lunch_break = ('12:00', '14:00')  # Weekdays only
        
        # Level hierarchy for merging
        self.level_hierarchy = ['Tots', 'Jolly', 'Bubbly', 'Lively', 'Flexi', 'L1', 'L2', 'L3', 'L4', 'Advance', 'Free']
        self.mergeable_levels = {
            'Tots': ['Tots'],
            'Jolly': ['Jolly', 'Bubbly'],
            'Bubbly': ['Jolly', 'Bubbly'], 
            'Lively': ['Lively', 'Flexi'],
            'Flexi': ['Lively', 'Flexi'],
            'L1': ['L1', 'L2'],
            'L2': ['L1', 'L2'],
            'L3': ['L3', 'L4'],
            'L4': ['L3', 'L4'],
            'Advance': ['Advance', 'Free'],
            'Free': ['Advance', 'Free']
        }
        
        # Statistics tracking
        self.stats = None
        self.constraint_violations = []
        
    def generate_schedule(self, coaches_data: Dict, requirements_data: List[Dict], 
                         popular_timeslots: Set[Tuple], branch_configs: Dict) -> Dict:
        """
        Main method to generate optimized schedule with strict constraints
        """
        print("Starting Enhanced Strict Constraint Scheduling...")
        
        # Phase 1: Generate all feasible assignments
        feasible_assignments = self._generate_feasible_assignments(
            coaches_data, requirements_data, popular_timeslots, branch_configs
        )
        print(f"Generated {len(feasible_assignments)} feasible assignments")
        
        # Phase 2: Priority-based initial assignment
        initial_schedule = self._create_initial_schedule(feasible_assignments)
        print(f"Created initial schedule with {len(initial_schedule)} assignments")
        
        # Phase 3: Constraint validation and conflict resolution
        validated_schedule = self._validate_and_resolve_conflicts(initial_schedule)
        print(f"Validated schedule with {len(validated_schedule)} assignments")
        
        # Phase 4: Optimization and level merging
        optimized_schedule = self._optimize_schedule(validated_schedule, requirements_data)
        print(f"Optimized schedule with {len(optimized_schedule)} assignments")
        
        # Phase 5: Generate statistics and final formatting
        final_schedule = self._format_final_schedule(optimized_schedule)
        self.stats = self._generate_statistics(optimized_schedule, requirements_data)
        
        print("Enhanced scheduling completed successfully!")
        return final_schedule
    
    def _generate_feasible_assignments(self, coaches_data: Dict, requirements_data: List[Dict], 
                                     popular_timeslots: Set[Tuple], branch_configs: Dict) -> List[Assignment]:
        """Generate all feasible class assignments based on constraints"""
        assignments = []
        
        for requirement in requirements_data:
            req_branch = requirement['branch']
            req_level = requirement['level']
            req_students = requirement['students']
            req_capacity = requirement['capacity']
            req_duration = requirement['duration']
            
            # Calculate number of classes needed
            classes_needed = max(1, (req_students + req_capacity - 1) // req_capacity)
            
            # Find qualified coaches
            qualified_coaches = self._find_qualified_coaches(coaches_data, req_branch, req_level)
            
            # Generate timeslots for this level
            timeslots = self._generate_timeslots_for_level(req_level, req_duration)
            
            # Create assignments for each needed class
            for class_num in range(classes_needed):
                students_in_class = min(req_capacity, req_students - (class_num * req_capacity))
                
                for coach_id, coach in qualified_coaches.items():
                    for timeslot in timeslots:
                        if self._is_coach_available(coach, timeslot['day'], timeslot['period']):
                            # Check if this is a popular timeslot
                            is_popular = (req_level, timeslot['day'], timeslot['time_slot_str']) in popular_timeslots
                            
                            # Calculate priority score
                            priority_score = self._calculate_priority_score(
                                coach, req_level, timeslot, is_popular, req_branch
                            )
                            
                            assignment = Assignment(
                                coach_id=coach_id,
                                coach_name=coach['name'],
                                branch=req_branch,
                                level=req_level,
                                day=timeslot['day'],
                                start_time=timeslot['start_time'],
                                end_time=timeslot['end_time'],
                                duration=req_duration,
                                students_count=students_in_class,
                                is_popular=is_popular,
                                priority_score=priority_score
                            )
                            assignments.append(assignment)
        
        return assignments
    
    def _find_qualified_coaches(self, coaches_data: Dict, branch: str, level: str) -> Dict:
        """Find coaches qualified to teach a specific level at a branch"""
        qualified = {}
        for coach_id, coach in coaches_data.items():
            if (branch in coach['branches'] and 
                (level in coach['qualifications'] or self._can_teach_merged_level(coach['qualifications'], level))):
                qualified[coach_id] = coach
        return qualified
    
    def _can_teach_merged_level(self, qualifications: List[str], target_level: str) -> bool:
        """Check if coach can teach target level through level merging"""
        if target_level in self.mergeable_levels:
            return any(qual in self.mergeable_levels[target_level] for qual in qualifications)
        return False
    
    def _generate_timeslots_for_level(self, level: str, duration: int) -> List[Dict]:
        """Generate valid timeslots for a specific level"""
        timeslots = []
        
        for day, periods in self.operating_hours.items():
            for period_start, period_end in periods:
                start_dt = datetime.strptime(period_start, '%H:%M')
                end_dt = datetime.strptime(period_end, '%H:%M')
                
                # Generate 30-minute intervals
                current = start_dt
                while current + timedelta(minutes=duration) <= end_dt:
                    slot_start = current.strftime('%H:%M')
                    slot_end = (current + timedelta(minutes=duration)).strftime('%H:%M')
                    
                    # Check lunch break constraint for weekdays
                    if self._is_valid_timeslot(current, duration, day):
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
    
    def _is_valid_timeslot(self, start_time: datetime, duration: int, day: str) -> bool:
        """Check if timeslot is valid (doesn't conflict with lunch break on weekdays)"""
        if day not in ['TUE', 'WED', 'THU', 'FRI']:
            return True
            
        class_start = start_time
        class_end = start_time + timedelta(minutes=duration)
        lunch_start = datetime.strptime(self.lunch_break[0], '%H:%M')
        lunch_end = datetime.strptime(self.lunch_break[1], '%H:%M')
        
        # Class should not overlap with lunch break
        return class_end <= lunch_start or class_start >= lunch_end
    
    def _is_coach_available(self, coach: Dict, day: str, period: str) -> bool:
        """Check if coach is available for the given day and period"""
        return coach['availability'].get(day, {}).get(period, False)
    
    def _calculate_priority_score(self, coach: Dict, level: str, timeslot: Dict, 
                                 is_popular: bool, branch: str) -> float:
        """Calculate priority score for assignment (higher is better)"""
        score = 0.0
        
        # Popular timeslot bonus
        if is_popular:
            score += 10.0
        
        # Coach status preference (Full time > Part time)
        status_scores = {
            'Full time': 5.0,
            'Senior Coach': 4.0,
            'Admin cum coach': 3.0,
            'Junior Coach': 2.0,
            'Part time': 1.0,
            'Branch Manager': 3.5
        }
        score += status_scores.get(coach['status'], 1.0)
        
        # Exact level match bonus
        if level in coach['qualifications']:
            score += 3.0
        
        # Peak hours preference (afternoon/evening on weekdays, morning/afternoon on weekends)
        hour = int(timeslot['start_time'].split(':')[0])
        if timeslot['day'] in ['SAT', 'SUN']:
            if 9 <= hour <= 17:  # Peak weekend hours
                score += 2.0
        else:
            if 15 <= hour <= 18:  # Peak weekday hours
                score += 2.0
        
        return score
    
    def _create_initial_schedule(self, feasible_assignments: List[Assignment]) -> List[Assignment]:
        """Create initial schedule using greedy assignment based on priority scores"""
        # Sort assignments by priority score (descending)
        sorted_assignments = sorted(feasible_assignments, key=lambda x: x.priority_score, reverse=True)
        
        selected_assignments = []
        used_slots = set()  # (coach_id, day, start_time)
        
        for assignment in sorted_assignments:
            slot_key = (assignment.coach_id, assignment.day, assignment.start_time)
            
            if slot_key not in used_slots:
                selected_assignments.append(assignment)
                used_slots.add(slot_key)
        
        return selected_assignments
    
    def _validate_and_resolve_conflicts(self, assignments: List[Assignment]) -> List[Assignment]:
        """Validate assignments against strict constraints and resolve conflicts"""
        validated_assignments = []
        self.constraint_violations = []
        
        # Group assignments by coach and day for validation
        coach_day_assignments = defaultdict(lambda: defaultdict(list))
        for assignment in assignments:
            coach_day_assignments[assignment.coach_id][assignment.day].append(assignment)
        
        for coach_id, daily_assignments in coach_day_assignments.items():
            for day, day_assignments in daily_assignments.items():
                # Sort by start time
                day_assignments.sort(key=lambda x: x.start_time)
                
                # Validate daily constraints
                valid_assignments = self._validate_daily_assignments(day_assignments, coach_id, day)
                validated_assignments.extend(valid_assignments)
        
        return validated_assignments
    
    def _validate_daily_assignments(self, day_assignments: List[Assignment], 
                                   coach_id: int, day: str) -> List[Assignment]:
        """Validate assignments for a coach on a specific day"""
        if len(day_assignments) > self.max_classes_per_coach_per_day:
            self.constraint_violations.append(
                f"Coach {coach_id} exceeds max classes per day on {day}"
            )
            # Keep only the highest priority assignments
            day_assignments = sorted(day_assignments, key=lambda x: x.priority_score, reverse=True)
            day_assignments = day_assignments[:self.max_classes_per_coach_per_day]
        
        # Check for time conflicts and minimum break requirements
        valid_assignments = []
        last_end_time = None
        
        for assignment in day_assignments:
            start_time = datetime.strptime(assignment.start_time, '%H:%M')
            end_time = datetime.strptime(assignment.end_time, '%H:%M')
            
            # Check minimum break requirement
            if last_end_time and (start_time - last_end_time).total_seconds() < (self.min_break_between_classes * 60):
                self.constraint_violations.append(
                    f"Insufficient break for coach {coach_id} on {day} at {assignment.start_time}"
                )
                continue
            
            # Check maximum consecutive hours
            if self._violates_consecutive_hours_limit(valid_assignments, assignment):
                self.constraint_violations.append(
                    f"Coach {coach_id} exceeds consecutive hours limit on {day}"
                )
                continue
            
            valid_assignments.append(assignment)
            last_end_time = end_time
        
        return valid_assignments
    
    def _violates_consecutive_hours_limit(self, existing_assignments: List[Assignment], 
                                        new_assignment: Assignment) -> bool:
        """Check if adding new assignment violates consecutive hours limit"""
        if not existing_assignments:
            return False
        
        # Find continuous block including new assignment
        all_assignments = existing_assignments + [new_assignment]
        all_assignments.sort(key=lambda x: x.start_time)
        
        consecutive_duration = 0
        last_end_time = None
        
        for assignment in all_assignments:
            start_time = datetime.strptime(assignment.start_time, '%H:%M')
            end_time = datetime.strptime(assignment.end_time, '%H:%M')
            
            if last_end_time and (start_time - last_end_time).total_seconds() <= (self.min_break_between_classes * 60):
                # Continuous block
                consecutive_duration += assignment.duration
            else:
                # New block starts
                consecutive_duration = assignment.duration
            
            if consecutive_duration > (self.max_consecutive_hours * 60):
                return True
            
            last_end_time = end_time
        
        return False
    
    def _optimize_schedule(self, assignments: List[Assignment], 
                          requirements_data: List[Dict]) -> List[Assignment]:
        """Optimize schedule through level merging and gap filling"""
        optimized_assignments = copy.deepcopy(assignments)
        
        # Phase 1: Identify gaps in coverage
        coverage_gaps = self._identify_coverage_gaps(assignments, requirements_data)
        
        # Phase 2: Attempt to fill gaps through level merging
        for gap in coverage_gaps:
            merged_assignment = self._attempt_level_merging(gap, optimized_assignments)
            if merged_assignment:
                optimized_assignments.append(merged_assignment)
        
        # Phase 3: Load balancing among coaches
        optimized_assignments = self._balance_coach_workload(optimized_assignments)
        
        return optimized_assignments
    
    def _identify_coverage_gaps(self, assignments: List[Assignment], 
                               requirements_data: List[Dict]) -> List[Dict]:
        """Identify gaps in enrollment coverage"""
        gaps = []
        
        # Count assignments by branch and level
        assignment_counts = defaultdict(lambda: defaultdict(int))
        for assignment in assignments:
            assignment_counts[assignment.branch][assignment.level] += 1
        
        # Compare with requirements
        for requirement in requirements_data:
            branch = requirement['branch']
            level = requirement['level']
            students = requirement['students']
            capacity = requirement['capacity']
            
            classes_needed = max(1, (students + capacity - 1) // capacity)
            classes_assigned = assignment_counts[branch][level]
            
            if classes_assigned < classes_needed:
                gaps.append({
                    'branch': branch,
                    'level': level,
                    'gap': classes_needed - classes_assigned,
                    'students': students,
                    'capacity': capacity
                })
        
        return gaps
    
    def _attempt_level_merging(self, gap: Dict, existing_assignments: List[Assignment]) -> Optional[Assignment]:
        """Attempt to fill coverage gap through level merging"""
        target_level = gap['level']
        target_branch = gap['branch']
        
        # Find mergeable levels with available capacity
        mergeable = self.mergeable_levels.get(target_level, [])
        
        for assignment in existing_assignments:
            if (assignment.branch == target_branch and 
                assignment.level in mergeable and 
                assignment.students_count < self.class_capacities.get(assignment.level, 8)):
                
                # Can merge some students into this class
                additional_capacity = self.class_capacities.get(assignment.level, 8) - assignment.students_count
                students_to_merge = min(additional_capacity, gap['students'])
                
                if students_to_merge > 0:
                    # Create merged assignment
                    return Assignment(
                        coach_id=assignment.coach_id,
                        coach_name=assignment.coach_name,
                        branch=target_branch,
                        level=f"{assignment.level}+{target_level}",  # Indicate merged class
                        day=assignment.day,
                        start_time=assignment.start_time,
                        end_time=assignment.end_time,
                        duration=assignment.duration,
                        students_count=students_to_merge,
                        is_popular=assignment.is_popular,
                        priority_score=assignment.priority_score * 0.9  # Slightly lower priority
                    )
        
        return None
    
    def _balance_coach_workload(self, assignments: List[Assignment]) -> List[Assignment]:
        """Balance workload distribution among coaches"""
        # Count assignments per coach
        coach_workload = defaultdict(int)
        for assignment in assignments:
            coach_workload[assignment.coach_id] += 1
        
        # Identify overloaded and underloaded coaches
        avg_workload = sum(coach_workload.values()) / len(coach_workload) if coach_workload else 0
        
        # For now, return as-is (more complex balancing can be added later)
        return assignments
    
    def _format_final_schedule(self, assignments: List[Assignment]) -> Dict:
        """Format assignments into final schedule structure for frontend"""
        schedule = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
        
        # Day name mapping for frontend compatibility
        day_mapping = {
            'TUE': 'Tuesday', 'WED': 'Wednesday', 'THU': 'Thursday',
            'FRI': 'Friday', 'SAT': 'Saturday', 'SUN': 'Sunday', 'MON': 'Monday'
        }
        
        for assignment in assignments:
            frontend_day = day_mapping.get(assignment.day, assignment.day)
            schedule[assignment.branch][frontend_day][assignment.coach_name].append({
                'name': assignment.level,
                'start_time': assignment.start_time.replace(':', ''),
                'duration': assignment.duration // 30,  # Convert to 30-min slots
                'students': assignment.students_count,
                'is_popular': assignment.is_popular
            })
        
        # Convert to final format
        result = {}
        for branch, branch_schedule in schedule.items():
            coaches = set()
            for day_schedule in branch_schedule.values():
                coaches.update(day_schedule.keys())
            
            result[branch] = {
                'coaches': sorted(list(coaches)),
                'schedule': dict(branch_schedule)
            }
        
        return result
    
    def _generate_statistics(self, assignments: List[Assignment], 
                           requirements_data: List[Dict]) -> ScheduleStats:
        """Generate comprehensive statistics for the schedule"""
        total_assignments = len(assignments)
        
        # Calculate coverage percentage
        total_required_classes = sum(
            max(1, (req['students'] + req['capacity'] - 1) // req['capacity'])
            for req in requirements_data
        )
        coverage_percentage = (total_assignments / total_required_classes * 100) if total_required_classes > 0 else 0
        
        # Coach utilization
        coach_assignments = defaultdict(int)
        for assignment in assignments:
            coach_assignments[assignment.coach_name] += 1
        
        coach_utilization = {
            coach: count / self.max_classes_per_coach_per_day * 7  # Across all days
            for coach, count in coach_assignments.items()
        }
        
        # Popular slot coverage
        popular_assignments = sum(1 for assignment in assignments if assignment.is_popular)
        popular_slot_coverage = (popular_assignments / total_assignments * 100) if total_assignments > 0 else 0
        
        # Branch and level distribution
        branch_distribution = defaultdict(int)
        level_distribution = defaultdict(int)
        for assignment in assignments:
            branch_distribution[assignment.branch] += 1
            level_distribution[assignment.level] += 1
        
        return ScheduleStats(
            total_assignments=total_assignments,
            coverage_percentage=coverage_percentage,
            coach_utilization=coach_utilization,
            popular_slot_coverage=popular_slot_coverage,
            constraint_violations=len(self.constraint_violations),
            branch_distribution=dict(branch_distribution),
            level_distribution=dict(level_distribution)
        )
    
    def get_statistics(self) -> Optional[ScheduleStats]:
        """Get the statistics from the last generated schedule"""
        return self.stats
    
    def get_constraint_violations(self) -> List[str]:
        """Get list of constraint violations from the last run"""
        return self.constraint_violations