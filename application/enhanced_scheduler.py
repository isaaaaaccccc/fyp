import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from collections import defaultdict
import random

class EnhancedStrictConstraintScheduler:
    """
    Enhanced Strict Constraint Scheduler - Optimizes student assignment with strict workload limits
    
    Algorithm Overview:
    1. Systematic assignment by priority (scarcity-based)
    2. Gap filling for unmet requirements
    3. Level merging to maximize capacity utilization
    4. Multi-level combinations for complex gaps
    5. Exhaustive assignment using all available resources
    6. Maximum utilization within strict constraints
    7. Comprehensive validation to ensure requirements are met
    """
    
    # ==================== EDITABLE CONFIGURATION ====================
    
    # Workload Limits (STRICT - never exceeded)
    WEEKEND_DAILY_LIMIT = 5        # Max classes per coach per weekend day
    WEEKDAY_DAILY_LIMIT = 3        # Max classes per coach per weekday
    WEEKEND_DAILY_HOURS = 480      # Max minutes per coach per weekend day (8 hours)
    WEEKDAY_DAILY_HOURS = 240      # Max minutes per coach per weekday (4 hours)
    
    # Weekly Workload Limits by Coach Type
    FULL_TIME_WEEKLY_MAX = 25      # Max classes per week for full-time coaches
    PART_TIME_WEEKLY_MAX = 15      # Max classes per week for part-time coaches
    MANAGER_WEEKLY_MAX = 3         # Max classes per week for branch managers
    
    # Class Management Rules
    CONSECUTIVE_LIMIT = 3          # Max consecutive classes without break
    MIN_BREAK_MINUTES = 60         # Minimum break between consecutive classes
    LEVEL_MERGE_DISTANCE = 1       # Max levels apart for merging (1 = adjacent only)
    MIN_MERGE_SIZE = 3             # Minimum students to create multi-level class
    
    # Algorithm Behavior
    MAX_ITERATIONS = 60            # Number of optimization iterations
    USE_ALL_SLOTS_AFTER = 15       # Switch to all slots after this iteration
    SHUFFLE_INTERVAL = 5           # Shuffle assignments every N iterations
    MAX_ASSIGNMENT_ATTEMPTS = 20   # Max attempts per requirement
    MAX_VALID_ATTEMPTS = 5         # Max attempts to find valid solutions
    
    # Scoring Weights (higher = more preferred)
    POPULAR_SLOT_BONUS = 20        # Bonus for popular timeslots
    WEEKEND_BIAS = 5               # Weekend preference (set to 0 for neutral)
    WEEKDAY_BIAS = 0               # Weekday preference (set to positive for weekday preference)
    UNDERUTILIZED_COACH_BONUS = 8  # Bonus for coaches with <5 classes
    CAPACITY_MULTIPLIER = 2        # Multiplier for class capacity in scoring
    
    # NEW: Class Diversity and Anti-Back-to-Back Parameters
    SAME_TYPE_BACK_TO_BACK_PENALTY = -15   # Penalty for back-to-back same level classes on weekday mornings
    DIVERSE_CLASS_BONUS = 10               # Bonus for having different class types at the same time
    
    # Priority Weights
    SCARCITY_WEIGHT = 0.5          # Weight for resource scarcity in priority
    COMPLEXITY_WEIGHT = 0.3        # Weight for level complexity in priority
    SIZE_WEIGHT = 0.2              # Weight for enrollment size in priority
    
    # ==================== END EDITABLE CONFIGURATION ====================
    
    def __init__(self, data, config:dict =None):
        if config:
            for key, value in config.items():
                if hasattr(self, key.upper()):
                    setattr(self, key.upper(), value)
        
        print("ENHANCED STRICT CONSTRAINT SCHEDULER")
        print("Target: Maximum student assignment with strict workload limits")
        print(f"STRICT LIMIT: Max {self.WEEKEND_DAILY_LIMIT} classes per coach per weekend day")
        print(f"STRICT LIMIT: Max {self.WEEKDAY_DAILY_LIMIT} classes per coach per weekday")

        self.data = data
        self.enrollment_dict = data['enrollment_dict']
        self.coaches_data = data['coaches_data']
        self.feasible_assignments = data['feasible_assignments']
        
        # Split assignments by popularity
        self.popular_assignments = [a for a in self.feasible_assignments if a.get('is_popular', False)]
        self.all_assignments = self.feasible_assignments
        
        print(f"Popular assignments available: {len(self.popular_assignments)}")
        print(f"Total feasible assignments: {len(self.all_assignments)}")
        
        # Load constraints and hierarchy
        self.class_capacities = data['class_capacities']
        self.branch_limits = data['branch_limits']
        self.level_hierarchy = ['Tots', 'Jolly', 'Bubbly', 'Lively', 'Flexi', 'L1', 'L2', 'L3', 'L4', 'Advance', 'Free']
        self.weekdays = data['weekdays']
        self.weekends = data['weekends']
        
        self.total_students_required = sum(self.enrollment_dict.values())
        
        # Categorize coaches by type
        self.full_time_coaches = [c for c in self.coaches_data.values() if c['status'] == 'Full Time']
        self.part_time_coaches = [c for c in self.coaches_data.values() if c['status'] == 'Part Time']
        self.branch_managers = [c for c in self.coaches_data.values() if c['status'] == 'Branch Manager']
        
        print(f"Total students to schedule: {self.total_students_required}")
        print(f"Coaches: {len(self.full_time_coaches)} FT, {len(self.part_time_coaches)} PT, {len(self.branch_managers)} MGR")
        
        self._analyze_enrollment_requirements()
        
        # Calculate theoretical capacity
        self.theoretical_capacity = self._calculate_theoretical_capacity()
        print(f"Theoretical maximum capacity (strict limits): {self.theoretical_capacity}")
        
        if self.theoretical_capacity < self.total_students_required:
            print("WARNING: Theoretical capacity insufficient with strict workload limits")
            print("Will maximize coverage within constraints")
    
    def _analyze_enrollment_requirements(self):
        """Analyze enrollment requirements and identify potential bottlenecks"""
        print("\nAnalyzing enrollment requirements:")
        
        for req_key, students in self.enrollment_dict.items():
            branch, level = req_key
            
            qualified_coaches = len([c for c in self.full_time_coaches + self.part_time_coaches + self.branch_managers
                                   if level in c['qualifications'] and branch in c['branches']])
            
            popular_slots = len([a for a in self.popular_assignments 
                               if a['branch'] == branch and a['level'] == level])
            all_slots = len([a for a in self.all_assignments 
                           if a['branch'] == branch and a['level'] == level])
            
            print(f"  {branch} {level}: {students} students, {qualified_coaches} coaches, {popular_slots} popular slots, {all_slots} total slots")
            
            if students > 0 and (qualified_coaches == 0 or all_slots == 0):
                print(f"    WARNING: Critical shortage for {branch} {level}")
    
    def schedule_with_complete_coverage(self):
        """Main scheduling algorithm with strict constraint enforcement and validation"""
        print("\nStarting enhanced scheduling with strict workload enforcement...")
        print(f"CONSTRAINT: Never exceed {self.WEEKEND_DAILY_LIMIT} weekend / {self.WEEKDAY_DAILY_LIMIT} weekday classes per coach per day")
        print("STRATEGY: Maximize coverage within absolute limits")
        
        best_result = None
        best_coverage = 0
        best_valid_result = None
        valid_attempts = 0
        
        for iteration in range(1, self.MAX_ITERATIONS + 1):
            print(f"\nITERATION {iteration}")
            print("-" * 40)
            
            state = self._initialize_enhanced_state()
            
            # Determine assignment pool strategy
            use_all_slots = iteration > self.USE_ALL_SLOTS_AFTER
            assignment_pool = self.all_assignments if use_all_slots else self.popular_assignments
            
            pool_type = "ALL available slots" if use_all_slots else "POPULAR slots"
            print(f"Using {pool_type} for maximum coverage")
            
            # Execute six-phase optimization
            self._phase1_enhanced_systematic(state, assignment_pool)
            self._phase2_enhanced_gap_filling(state, assignment_pool)
            self._phase3_enhanced_merging(state)
            self._phase4_multi_level_merging(state, assignment_pool)
            self._phase5_exhaustive_assignment(state, assignment_pool)
            self._phase6_maximum_utilization_strict(state, assignment_pool)
            
            # Validate and score result
            result = self._build_and_validate_result(state)
            coverage = result['statistics']['coverage_percentage']
            violations = self._count_violations(result)
            workload_violations = self._count_workload_violations(result)
            
            print(f"Result: {coverage:.1f}% coverage, {violations} violations, {workload_violations} workload violations")
            
            # Perform comprehensive validation
            validation_results = self._validate_schedule_comprehensively(result)
            validation_status = validation_results['status']
            
            # Accept only zero-violation results
            if violations == 0 and workload_violations == 0 and coverage > best_coverage:
                best_result = result
                best_coverage = coverage
                print(f"New best VALID result: {coverage:.1f}% (strict limits enforced)")
                
                # Check if this result passes comprehensive validation
                if validation_status == 'PASSED':
                    best_valid_result = result
                    best_valid_result['validation'] = validation_results
                    valid_attempts += 1
                    print(f"VALIDATION PASSED - Solution meets all requirements")
                    
                    # If we've found multiple valid solutions, check if we have perfect coverage
                    if coverage >= 100.0:
                        print("100% coverage with validation passed - SUCCESS")
                        break
                        
                    # Exit after finding enough valid solutions
                    if valid_attempts >= self.MAX_VALID_ATTEMPTS:
                        print(f"Found {valid_attempts} valid solutions - selecting best")
                        break
            elif workload_violations > 0:
                print(f"REJECTED: {workload_violations} workload limit violations")
            elif violations > 0:
                print(f"REJECTED: {violations} other constraint violations")
            
            if validation_status != 'PASSED':
                print(f"VALIDATION STATUS: {validation_status}")
                if validation_results.get('violations'):
                    violation_count = len(validation_results['violations'])
                    print(f"Found {violation_count} validation violations")
            
            # Report remaining gaps
            gaps = self._identify_gaps(result)
            if gaps:
                unassigned_total = sum(gap for _, gap in gaps)
                print(f"Remaining unassigned: {unassigned_total} students")
                if len(gaps) <= 5:
                    print("Critical gaps:")
                    for req_key, gap in gaps:
                        print(f"  {req_key[0]} {req_key[1]}: {gap} students")
            
            # Periodic shuffling for better exploration
            if iteration % self.SHUFFLE_INTERVAL == 0:
                self._enhanced_adaptive_shuffle()
        
        # Use the best validated result if available, otherwise use best constraint-valid result
        final_result = best_valid_result if best_valid_result else best_result
        
        if not final_result:
            final_result = self._create_best_effort_strict_result()
            print("\nNo fully valid solution found. Created best effort result.")
        
        # Add detailed statistics to final result
        final_result = self._add_detailed_statistics(final_result)
        
        final_coverage = final_result['statistics']['coverage_percentage']
        print(f"\nFINAL RESULT: {final_coverage:.1f}% coverage with strict workload limits")
        
        if final_coverage >= 100.0:
            print("SUCCESS: 100% coverage within strict workload limits")
        else:
            remaining = final_result['statistics']['total_students_required'] - final_result['statistics']['total_students_scheduled']
            print(f"RESULT: {remaining} students unassigned due to strict workload constraints")
            print("GUARANTEE: All workload limits strictly respected")
        
        # Print final statistics
        self._print_final_statistics(final_result)
        
        return final_result
    
    def _validate_schedule_comprehensively(self, result):
        """Comprehensive validation of schedule against original requirements"""
        validation_results = {
            'status': 'UNKNOWN',
            'violations': [],
            'warnings': [],
            'enrollment_coverage': {}
        }
        
        # Extract schedule from result
        schedule = result.get('schedule', [])
        if not schedule:
            validation_results['status'] = 'FAILED'
            validation_results['violations'].append("No schedule entries found")
            return validation_results
            
        # Validate student enrollment
        self._validate_student_enrollment(schedule, validation_results)
        
        # Validate coach workload
        self._validate_coach_workload(schedule, validation_results)
        
        # Validate branch capacity
        self._validate_branch_capacity(schedule, validation_results)
        
        # Validate coach qualifications
        self._validate_coach_qualifications(schedule, validation_results)
        
        # Validate coach branches (one branch per day)
        self._validate_coach_branch_assignments(schedule, validation_results)
        
        # Validate no overlapping classes
        self._validate_no_overlapping_classes(schedule, validation_results)
        
        # NEW: Validate back-to-back classes of the same type on weekday mornings
        self._validate_back_to_back_same_type(schedule, validation_results)
        
        # NEW: Validate class diversity at the same time
        self._validate_class_diversity(schedule, validation_results)
        
        # Set final status
        if validation_results['violations']:
            validation_results['status'] = 'FAILED'
        elif validation_results['warnings']:
            validation_results['status'] = 'PASSED_WITH_WARNINGS'
        else:
            validation_results['status'] = 'PASSED'
        
        return validation_results
    
    def _validate_back_to_back_same_type(self, schedule, results):
        """Validate back-to-back classes of the same level on weekday mornings"""
        # Group by branch, day, level
        branch_day_level_classes = defaultdict(list)
        for entry in schedule:
            branch = entry['Branch']
            day = entry['Day']
            level = entry['Gymnastics Level']
            start_time = entry['Start Time']
            end_time = entry['End Time']
            students = entry['Students']
            key = (branch, day, level)
            
            # Only check weekday mornings
            if day in self.weekdays and start_time < '12:00':
                branch_day_level_classes[key].append({
                    'start_time': start_time,
                    'end_time': end_time,
                    'students': students,
                    'capacity': entry['Capacity']
                })
        
        # Check for back-to-back classes
        for key, classes in branch_day_level_classes.items():
            if len(classes) <= 1:
                continue
            
            # Sort by start time
            classes.sort(key=lambda x: x['start_time'])
            
            for i in range(len(classes) - 1):
                class1 = classes[i]
                class2 = classes[i+1]
                
                # Calculate time gap
                end1 = datetime.strptime(class1['end_time'], '%H:%M')
                start2 = datetime.strptime(class2['start_time'], '%H:%M')
                gap_minutes = (start2 - end1).total_seconds() / 60
                
                # Check if back-to-back (less than MIN_BREAK_MINUTES) and if first class is not full
                if gap_minutes < self.MIN_BREAK_MINUTES and class1['students'] < class1['capacity']:
                    branch, day, level = key
                    results['warnings'].append(f"Back-to-back {level} classes on {day} morning at {branch} with first class not full ({class1['students']}/{class1['capacity']})")
    
    def _validate_class_diversity(self, schedule, results):
        """Validate diversity of class types running at the same time"""
        # Group by branch, day, start_time
        branch_day_time_classes = defaultdict(list)
        for entry in schedule:
            branch = entry['Branch']
            day = entry['Day']
            start_time = entry['Start Time']
            level = entry['Gymnastics Level']
            key = (branch, day, start_time)
            branch_day_time_classes[key].append(level)
        
        # Check diversity
        for key, levels in branch_day_time_classes.items():
            if len(levels) > 1 and len(set(levels)) == 1:
                # Same level classes running at the same time
                branch, day, time = key
                level = levels[0]
                results['warnings'].append(f"Multiple {level} classes running simultaneously at {branch} on {day} at {time}")
    
    def _validate_student_enrollment(self, schedule, results):
        """Validate that students are assigned according to enrollment requirements"""
        scheduled_students = defaultdict(int)
        
        # Count scheduled students by branch and level
        for entry in schedule:
            key = (entry['Branch'], entry['Gymnastics Level'])
            scheduled_students[key] += entry['Students']
        
        # Compare with enrollment data
        total_required = 0
        total_scheduled = 0
        missing_students = 0
        
        for req_key, req_students in self.enrollment_dict.items():
            scheduled = scheduled_students.get(req_key, 0)
            total_required += req_students
            total_scheduled += min(scheduled, req_students)  # Only count up to required
            
            # Check for missing students
            if scheduled < req_students:
                diff = req_students - scheduled
                missing_students += diff
                results['violations'].append(f"Under-scheduled: {req_key[0]} {req_key[1]} has {req_students} required but only {scheduled} scheduled")
            
            # Store coverage information
            results['enrollment_coverage'][req_key] = {
                'required': req_students,
                'scheduled': scheduled,
                'coverage_pct': round(scheduled / req_students * 100 if req_students > 0 else 100, 2)
            }
        
        # Calculate overall coverage
        coverage_pct = round(total_scheduled / total_required * 100 if total_required > 0 else 100, 2)
        results['overall_coverage'] = {
            'total_required': total_required,
            'total_scheduled': total_scheduled,
            'missing_students': missing_students,
            'coverage_pct': coverage_pct
        }
        
        if missing_students > 0:
            results['violations'].append(f"Total missing students: {missing_students}")
    
    def _validate_coach_workload(self, schedule, results):
        """Validate coach workload limits"""
        coach_daily_classes = defaultdict(lambda: defaultdict(int))
        coach_daily_minutes = defaultdict(lambda: defaultdict(int))
        coach_schedules = defaultdict(lambda: defaultdict(list))
        
        for entry in schedule:
            coach_id = entry['Coach ID']
            day = entry['Day']
            duration = entry['Duration (min)']
            
            coach_daily_classes[coach_id][day] += 1
            coach_daily_minutes[coach_id][day] += duration
            coach_schedules[coach_id][day].append(entry)
        
        # Check daily class limits
        for coach_id, daily_classes in coach_daily_classes.items():
            for day, count in daily_classes.items():
                limit = self.WEEKEND_DAILY_LIMIT if day in self.weekends else self.WEEKDAY_DAILY_LIMIT
                if count > limit:
                    results['violations'].append(f"Coach {coach_id} has {count} classes on {day} (limit: {limit})")
        
        # Check daily hours limits
        for coach_id, daily_minutes in coach_daily_minutes.items():
            for day, minutes in daily_minutes.items():
                limit = self.WEEKEND_DAILY_HOURS if day in self.weekends else self.WEEKDAY_DAILY_HOURS
                if minutes > limit:
                    results['violations'].append(f"Coach {coach_id} has {minutes} minutes on {day} (limit: {limit})")
        
        # Check consecutive class limits
        for coach_id, days in coach_schedules.items():
            for day, entries in days.items():
                if len(entries) <= 1:
                    continue
                
                # Sort by start time
                sorted_entries = sorted(entries, key=lambda e: e['Start Time'])
                
                consecutive_count = 1
                for i in range(1, len(sorted_entries)):
                    prev_end = datetime.strptime(sorted_entries[i-1]['End Time'], '%H:%M')
                    curr_start = datetime.strptime(sorted_entries[i]['Start Time'], '%H:%M')
                    
                    gap_minutes = (curr_start - prev_end).total_seconds() / 60
                    
                    if gap_minutes < self.MIN_BREAK_MINUTES:
                        consecutive_count += 1
                        if consecutive_count > self.CONSECUTIVE_LIMIT:
                            results['violations'].append(f"Coach {coach_id} has {consecutive_count} consecutive classes on {day} without required break")
                            break
                    else:
                        consecutive_count = 1
    
    def _validate_branch_capacity(self, schedule, results):
        """Validate branch capacity limits"""
        branch_time_usage = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
        
        for entry in schedule:
            branch = entry['Branch']
            day = entry['Day']
            
            # Calculate time slots used by this class
            start_time = datetime.strptime(entry['Start Time'], '%H:%M')
            end_time = datetime.strptime(entry['End Time'], '%H:%M')
            
            current = start_time
            while current < end_time:
                time_slot = current.strftime('%H:%M')
                branch_time_usage[branch][day][time_slot] += 1
                current += timedelta(minutes=30)
        
        # Check against branch limits
        for branch, days in branch_time_usage.items():
            max_classes = self.branch_limits.get(branch, 4)
            
            for day, time_slots in days.items():
                for time_slot, count in time_slots.items():
                    if count > max_classes:
                        results['violations'].append(f"Branch {branch} exceeds capacity on {day} at {time_slot}: {count} classes (limit: {max_classes})")
    
    def _validate_coach_qualifications(self, schedule, results):
        """Validate that coaches are qualified for assigned levels"""
        for entry in schedule:
            coach_id = entry['Coach ID']
            level = entry['Gymnastics Level']
            
            if coach_id in self.coaches_data:
                coach = self.coaches_data[coach_id]
                qualifications = coach.get('qualifications', [])
                
                if level not in qualifications:
                    results['violations'].append(f"Coach {coach_id} ({coach.get('name', 'Unknown')}) not qualified to teach {level}")
    
    def _validate_coach_branch_assignments(self, schedule, results):
        """Validate that coaches only work at one branch per day"""
        coach_branch_daily = defaultdict(lambda: defaultdict(set))
        
        for entry in schedule:
            coach_id = entry['Coach ID']
            day = entry['Day']
            branch = entry['Branch']
            
            coach_branch_daily[coach_id][day].add(branch)
        
        for coach_id, days in coach_branch_daily.items():
            for day, branches in days.items():
                if len(branches) > 1:
                    results['violations'].append(f"Coach {coach_id} assigned to multiple branches on {day}: {', '.join(branches)}")
    
    def _validate_no_overlapping_classes(self, schedule, results):
        """Validate that coaches don't have overlapping classes"""
        coach_schedules = defaultdict(lambda: defaultdict(list))
        
        for entry in schedule:
            coach_id = entry['Coach ID']
            day = entry['Day']
            start_time = entry['Start Time']
            end_time = entry['End Time']
            
            coach_schedules[coach_id][day].append({
                'branch': entry['Branch'],
                'level': entry['Gymnastics Level'],
                'start_time': start_time,
                'end_time': end_time
            })
        
        # Check for overlaps
        for coach_id, days in coach_schedules.items():
            for day, classes in days.items():
                for i in range(len(classes)):
                    for j in range(i+1, len(classes)):
                        class1 = classes[i]
                        class2 = classes[j]
                        
                        start1 = datetime.strptime(class1['start_time'], '%H:%M')
                        end1 = datetime.strptime(class1['end_time'], '%H:%M')
                        start2 = datetime.strptime(class2['start_time'], '%H:%M')
                        end2 = datetime.strptime(class2['end_time'], '%H:%M')
                        
                        if start1 < end2 and start2 < end1:
                            results['violations'].append(f"Coach {coach_id} has overlapping classes on {day}: "
                                                       f"{class1['level']} ({class1['start_time']}-{class1['end_time']}) and "
                                                       f"{class2['level']} ({class2['start_time']}-{class2['end_time']})")
    
    def _calculate_theoretical_capacity(self):
        """Calculate maximum theoretical capacity with strict constraints"""
        total_capacity = 0
        
        for coach in self.full_time_coaches + self.part_time_coaches + self.branch_managers:
            coach_capacity = 0
            
            # Calculate daily capacity with strict limits
            for day in ['TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN']:
                daily_classes = self.WEEKEND_DAILY_LIMIT if day in self.weekends else self.WEEKDAY_DAILY_LIMIT
                coach_capacity += daily_classes
            
            # Apply weekly limits by coach type
            weekly_limit = self._get_coach_weekly_limit(coach)
            coach_capacity = min(coach_capacity, weekly_limit)
            
            total_capacity += coach_capacity
        
        # Apply average class capacity
        average_class_capacity = sum(self.class_capacities.values()) / len(self.class_capacities)
        return int(total_capacity * average_class_capacity)
    
    def _get_coach_weekly_limit(self, coach):
        """Get weekly class limit based on coach type"""
        status = coach['status']
        if status == 'Full Time':
            return self.FULL_TIME_WEEKLY_MAX
        elif status == 'Part Time':
            return self.PART_TIME_WEEKLY_MAX
        else:  # Branch Manager
            return self.MANAGER_WEEKLY_MAX
    
    def _initialize_enhanced_state(self):
        """Initialize state tracking for scheduling iteration"""
        return {
            'selected_assignments': [],
            'coach_schedules': defaultdict(lambda: defaultdict(list)),
            'coach_daily_hours': defaultdict(lambda: defaultdict(int)),
            'coach_daily_classes': defaultdict(lambda: defaultdict(int)),
            'coach_branch_daily': defaultdict(lambda: defaultdict(str)),
            'branch_time_usage': defaultdict(lambda: defaultdict(lambda: defaultdict(int))),
            'requirement_coverage': defaultdict(int),
            'coach_workload': defaultdict(int),
            'unassigned_students': dict(self.enrollment_dict),
            'critical_gaps': [],
            'resource_utilization': defaultdict(float),
            'assignment_attempts': defaultdict(int),
            # NEW: Track branch-day-time-level information for diversity check
            'branch_time_levels': defaultdict(lambda: defaultdict(lambda: defaultdict(set))),
            # NEW: Track branch-day-level-time information for back-to-back check
            'branch_day_level_times': defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
        }
    
    def _phase1_enhanced_systematic(self, state, assignment_pool):
        """Phase 1: Systematic assignment by priority with strict constraint enforcement"""
        print("Phase 1: Enhanced systematic assignment (strict workload limits)")
        
        sorted_requirements = self._get_enhanced_priority_requirements()
        
        for req_key, requirement in sorted_requirements:
            branch, level = req_key
            students_needed = requirement['students']
            max_capacity = self.class_capacities.get(level, 8)
            
            print(f"  Processing {branch} {level}: {students_needed} students")
            
            students_assigned = 0
            qualified_coaches = self._get_prioritized_coaches(branch, level)
            attempts = 0
            
            while students_assigned < students_needed and attempts < self.MAX_ASSIGNMENT_ATTEMPTS:
                attempts += 1
                assignment = self._find_optimal_assignment_strict(qualified_coaches, branch, level, state, assignment_pool)
                
                if not assignment:
                    print(f"    No valid assignment found on attempt {attempts} (strict limits)")
                    break
                
                remaining_students = students_needed - students_assigned
                class_size = min(remaining_students, max_capacity)
                
                if self._add_validated_assignment_strict(assignment, class_size, state):
                    students_assigned += class_size
                    state['unassigned_students'][req_key] = students_needed - students_assigned
                    print(f"    Class added: {class_size} students, Coach {assignment['coach_name']}")
                else:
                    print(f"    Failed to add assignment (strict limits enforced)")
            
            if students_assigned > 0:
                coverage_rate = (students_assigned / students_needed * 100)
                print(f"    Coverage: {students_assigned}/{students_needed} ({coverage_rate:.1f}%)")
            else:
                print(f"    CONSTRAINT LIMITED: No students assigned for {branch} {level}")
                state['critical_gaps'].append(req_key)
        
        total_scheduled = sum(a['actual_students'] for a in state['selected_assignments'])
        coverage = (total_scheduled / self.total_students_required * 100)
        print(f"  Phase 1 Complete: {coverage:.1f}% total coverage")
    
    def _phase2_enhanced_gap_filling(self, state, assignment_pool):
        """Phase 2: Fill remaining gaps with additional classes"""
        print("Phase 2: Enhanced gap filling (strict workload limits)")
        
        gaps = [(k, v) for k, v in state['unassigned_students'].items() if v > 0]
        if not gaps:
            print("  No gaps to fill")
            return
        
        # Sort gaps by urgency (size and scarcity)
        gaps.sort(key=lambda x: (x[1], self._calculate_scarcity_score(x[0])), reverse=True)
        
        for req_key, gap_size in gaps:
            branch, level = req_key
            print(f"  Filling gap: {branch} {level} - {gap_size} students")
            
            all_qualified = self._get_all_qualified_coaches(branch, level)
            students_filled = 0
            
            for coach in all_qualified:
                if students_filled >= gap_size:
                    break
                
                assignment = self._find_specific_coach_assignment_strict(coach['id'], branch, level, state, assignment_pool)
                if assignment:
                    max_capacity = self.class_capacities.get(level, 8)
                    class_size = min(gap_size - students_filled, max_capacity)
                    
                    if self._add_validated_assignment_strict(assignment, class_size, state):
                        students_filled += class_size
                        state['unassigned_students'][req_key] -= class_size
                        print(f"    Gap filled: {class_size} students, Coach {coach['name']}")
            
            if students_filled == 0:
                print(f"    CONSTRAINT LIMITED: Could not fill gap for {branch} {level}")
        
        total_scheduled = sum(a['actual_students'] for a in state['selected_assignments'])
        coverage = (total_scheduled / self.total_students_required * 100)
        print(f"  Phase 2 Complete: {coverage:.1f}% total coverage")
    
    def _phase3_enhanced_merging(self, state):
        """Phase 3: Merge students from different levels into existing classes"""
        print("Phase 3: Enhanced merging")
        
        gaps = [(k, v) for k, v in state['unassigned_students'].items() if v > 0]
        if not gaps:
            print("  No gaps requiring merging")
            return
        
        for req_key, gap_size in gaps:
            branch, level = req_key
            print(f"  Merging for {branch} {level}: {gap_size} students")
            
            # Find compatible existing classes with available capacity
            compatible_classes = []
            for assignment in state['selected_assignments']:
                if (assignment['branch'] == branch and 
                    self._check_level_compatibility(assignment['level'], level)):
                    
                    current_students = assignment['actual_students']
                    max_capacity = self.class_capacities.get(assignment['level'], 8)
                    available_space = max_capacity - current_students
                    
                    if available_space > 0:
                        compatible_classes.append((assignment, available_space))
            
            # Sort by available space (largest first)
            compatible_classes.sort(key=lambda x: x[1], reverse=True)
            
            students_merged = 0
            for assignment, available_space in compatible_classes:
                if students_merged >= gap_size:
                    break
                
                merge_size = min(gap_size - students_merged, available_space)
                
                if merge_size > 0:
                    new_total = assignment['actual_students'] + merge_size
                    max_capacity = self.class_capacities.get(assignment['level'], 8)
                    
                    if new_total <= max_capacity:
                        assignment['actual_students'] += merge_size
                        students_merged += merge_size
                        self._update_merge_info(assignment, level)
                        print(f"    Merged {merge_size}: {assignment['level']}+{level}")
            
            if students_merged > 0:
                state['unassigned_students'][req_key] -= students_merged
                print(f"  Merge progress: {students_merged}/{gap_size} students merged")
        
        total_scheduled = sum(a['actual_students'] for a in state['selected_assignments'])
        coverage = (total_scheduled / self.total_students_required * 100)
        print(f"  Phase 3 Complete: {coverage:.1f}% total coverage")
    
    def _phase4_multi_level_merging(self, state, assignment_pool):
        """Phase 4: Create new classes combining multiple levels"""
        print("Phase 4: Multi-level merging")
        
        gaps = [(k, v) for k, v in state['unassigned_students'].items() if v > 0]
        if not gaps:
            print("  No gaps requiring multi-level merging")
            return
        
        # Group gaps by branch for efficient processing
        branch_gaps = defaultdict(list)
        for req_key, gap_size in gaps:
            branch, level = req_key
            branch_gaps[branch].append((level, gap_size))
        
        for branch, level_gaps in branch_gaps.items():
            print(f"  Multi-level merging for branch {branch}")
            
            level_combinations = self._generate_level_combinations(level_gaps)
            
            for levels, total_students in level_combinations:
                if total_students < self.MIN_MERGE_SIZE:
                    continue
                
                qualified_coaches = self._find_multi_qualified_coaches(branch, levels)
                
                for coach in qualified_coaches:
                    assignment = self._find_specific_coach_assignment_strict(coach['id'], branch, levels[0], state, assignment_pool)
                    
                    if assignment:
                        max_capacity = max(self.class_capacities.get(level, 8) for level in levels)
                        class_size = min(total_students, max_capacity)
                        
                        if self._add_validated_assignment_strict(assignment, class_size, state):
                            self._distribute_students_across_levels(levels, level_gaps, class_size, state)
                            assignment['merged_levels'] = levels
                            assignment['merged'] = 'Yes'
                            assignment['merged_with'] = '+'.join(sorted(levels))
                            
                            print(f"    Multi-level class: {'+'.join(levels)} - {class_size} students")
                            break
        
        total_scheduled = sum(a['actual_students'] for a in state['selected_assignments'])
        coverage = (total_scheduled / self.total_students_required * 100)
        print(f"  Phase 4 Complete: {coverage:.1f}% total coverage")
    
    def _phase5_exhaustive_assignment(self, state, assignment_pool):
        """Phase 5: Use every available coach slot within strict limits"""
        print("Phase 5: Exhaustive assignment (strict limits enforced)")
        
        gaps = [(k, v) for k, v in state['unassigned_students'].items() if v > 0]
        if not gaps:
            print("  No gaps requiring exhaustive assignment")
            return
        
        for coach in self.full_time_coaches + self.part_time_coaches + self.branch_managers:
            coach_id = coach['id']
            
            for day in ['TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN']:
                current_classes = state['coach_daily_classes'][coach_id][day]
                max_classes = self.WEEKEND_DAILY_LIMIT if day in self.weekends else self.WEEKDAY_DAILY_LIMIT
                
                if current_classes < max_classes:
                    for req_key, gap_size in gaps:
                        branch, level = req_key
                        
                        if (gap_size > 0 and 
                            level in coach['qualifications'] and 
                            branch in coach['branches']):
                            
                            assignment = self._find_specific_coach_day_assignment_strict(
                                coach_id, branch, level, day, state, assignment_pool
                            )
                            
                            if assignment:
                                max_capacity = self.class_capacities.get(level, 8)
                                class_size = min(gap_size, max_capacity)
                                
                                if self._add_validated_assignment_strict(assignment, class_size, state):
                                    state['unassigned_students'][req_key] -= class_size
                                    print(f"    Exhaustive class: {class_size} students, {coach['name']} on {day}")
                                    break
        
        total_scheduled = sum(a['actual_students'] for a in state['selected_assignments'])
        coverage = (total_scheduled / self.total_students_required * 100)
        print(f"  Phase 5 Complete: {coverage:.1f}% total coverage")
    
    def _phase6_maximum_utilization_strict(self, state, assignment_pool):
        """Phase 6: Final optimization to maximize utilization within strict limits"""
        print("Phase 6: Maximum utilization (strict limits)")
        
        gaps = [(k, v) for k, v in state['unassigned_students'].items() if v > 0]
        if not gaps:
            print("  No gaps - maximum coverage achieved within strict limits")
            return
        
        print(f"  Final optimization for {len(gaps)} remaining gaps")
        
        # Final push: use every remaining slot within strict limits
        for coach in self.full_time_coaches + self.part_time_coaches + self.branch_managers:
            coach_id = coach['id']
            
            for day in ['TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN']:
                current_classes = state['coach_daily_classes'][coach_id][day]
                max_classes = self.WEEKEND_DAILY_LIMIT if day in self.weekends else self.WEEKDAY_DAILY_LIMIT
                
                while current_classes < max_classes:
                    assignment_added = False
                    
                    for req_key, gap_size in gaps:
                        if gap_size <= 0:
                            continue
                            
                        branch, level = req_key
                        
                        if (level in coach['qualifications'] and 
                            branch in coach['branches']):
                            
                            assignment = self._find_specific_coach_day_assignment_strict(
                                coach_id, branch, level, day, state, assignment_pool
                            )
                            
                            if assignment:
                                max_capacity = self.class_capacities.get(level, 8)
                                class_size = min(gap_size, max_capacity)
                                
                                if self._add_validated_assignment_strict(assignment, class_size, state):
                                    state['unassigned_students'][req_key] -= class_size
                                    current_classes += 1
                                    assignment_added = True
                                    print(f"    Max utilization: {class_size} students, {coach['name']} {day}")
                                    break
                    
                    if not assignment_added:
                        break
        
        total_scheduled = sum(a['actual_students'] for a in state['selected_assignments'])
        coverage = (total_scheduled / self.total_students_required * 100)
        print(f"  Phase 6 Complete: {coverage:.1f}% total coverage")
        
        # Final gap report
        remaining_gaps = [(k, v) for k, v in state['unassigned_students'].items() if v > 0]
        if remaining_gaps:
            total_unassigned = sum(gap for _, gap in remaining_gaps)
            print(f"  {total_unassigned} students remain unassigned due to strict workload limits")
            for req_key, gap in remaining_gaps[:5]:
                print(f"    CONSTRAINED: {req_key[0]} {req_key[1]} - {gap} students")
        else:
            print("  100% ASSIGNMENT ACHIEVED within strict workload limits")
    
    # ==================== ASSIGNMENT SCORING AND SELECTION ====================
    
    def _score_assignment_enhanced(self, assignment, state):
        """Score assignment based on configured preferences with new diversity scoring"""
        score = 0
        
        # Popular slot preference
        if assignment.get('is_popular', False):
            score += self.POPULAR_SLOT_BONUS
        
        # Day preferences
        if assignment['day'] in self.weekends:
            score += self.WEEKEND_BIAS
        else:
            score += self.WEEKDAY_BIAS
        
        # Coach workload balance
        coach_load = state['coach_workload'][assignment['coach_id']]
        if coach_load < 5:
            score += self.UNDERUTILIZED_COACH_BONUS
        
        # Capacity utilization
        score += assignment['capacity'] * self.CAPACITY_MULTIPLIER
        
        # NEW: Check for back-to-back same level classes on weekday mornings
        branch = assignment['branch']
        day = assignment['day']
        level = assignment['level']
        start_time = assignment['start_time']
        
        if day in self.weekdays and start_time < '12:00':
            # Check if there are already classes of the same level in the same branch & day
            day_level_times = state['branch_day_level_times'].get(branch, {}).get(day, {}).get(level, [])
            
            if day_level_times:
                # Convert to datetime for comparison
                new_start = datetime.strptime(start_time, '%H:%M')
                new_end = datetime.strptime(assignment['end_time'], '%H:%M')
                
                for existing_start, existing_end in day_level_times:
                    # Check for back-to-back
                    if (existing_end <= new_start and (new_start - existing_end).total_seconds()/60 < self.MIN_BREAK_MINUTES) or \
                       (new_end <= existing_start and (existing_start - new_end).total_seconds()/60 < self.MIN_BREAK_MINUTES):
                        score += self.SAME_TYPE_BACK_TO_BACK_PENALTY
                        break
        
        # NEW: Check for class diversity at the same time
        branch_time_levels = state['branch_time_levels'].get(branch, {}).get(day, {}).get(start_time, set())
        if level not in branch_time_levels and branch_time_levels:
            # Bonus for adding diversity
            score += self.DIVERSE_CLASS_BONUS
        
        return score
    
    def _get_enhanced_priority_requirements(self):
        """Calculate priority scores for all requirements"""
        requirements = []
        
        for req_key, students in self.enrollment_dict.items():
            branch, level = req_key
            
            scarcity_score = self._calculate_scarcity_score(req_key)
            complexity_score = self._calculate_level_complexity(level)
            size_priority = min(students / 20, 1.0)
            
            # Calculate combined priority score
            priority_score = (scarcity_score * self.SCARCITY_WEIGHT + 
                            complexity_score * self.COMPLEXITY_WEIGHT + 
                            size_priority * self.SIZE_WEIGHT)
            
            requirements.append((req_key, {'students': students}, priority_score))
        
        requirements.sort(key=lambda x: x[2], reverse=True)
        return [(req_key, req) for req_key, req, _ in requirements]
    
    def _calculate_scarcity_score(self, req_key):
        """Calculate resource scarcity for prioritization"""
        branch, level = req_key
        
        qualified_coaches = len([c for c in self.full_time_coaches + self.part_time_coaches + self.branch_managers
                               if level in c['qualifications'] and branch in c['branches']])
        
        available_slots = len([a for a in self.all_assignments
                             if a['branch'] == branch and a['level'] == level])
        
        scarcity = (50 / max(1, qualified_coaches)) + (30 / max(1, available_slots))
        return min(scarcity, 10.0)
    
    def _calculate_level_complexity(self, level):
        """Calculate complexity score based on level hierarchy"""
        if level not in self.level_hierarchy:
            return 0.5
        
        level_index = self.level_hierarchy.index(level)
        return level_index / len(self.level_hierarchy)
    
    # ==================== CONSTRAINT VALIDATION ====================
    
    def _validate_strict_workload_constraints(self, assignment, state):
        """Validate all constraints with strict workload enforcement"""
        coach_id = assignment['coach_id']
        coach = self.coaches_data[coach_id]
        day = assignment['day']
        period = assignment['period']
        branch = assignment['branch']
        start_time = assignment['start_time']
        end_time = assignment['end_time']
        duration = assignment['duration']
        level = assignment['level']
        
        # Basic availability check
        if not coach['availability'].get(day, {}).get(period, False):
            return False
        
        # Time conflict check
        if self._has_time_conflict(assignment, state):
            return False
        
        # One branch per day constraint
        existing_branch = state['coach_branch_daily'][coach_id][day]
        if existing_branch and existing_branch != branch:
            return False
        
        # Strict daily class limits
        current_classes = state['coach_daily_classes'][coach_id][day]
        strict_limit = self.WEEKEND_DAILY_LIMIT if day in self.weekends else self.WEEKDAY_DAILY_LIMIT
        
        if current_classes >= strict_limit:
            return False
        
        # Daily hours limits
        current_hours = state['coach_daily_hours'][coach_id][day]
        hours_limit = self.WEEKEND_DAILY_HOURS if day in self.weekends else self.WEEKDAY_DAILY_HOURS
        
        if current_hours + duration > hours_limit:
            return False
        
        # Consecutive class limits
        if not self._respects_consecutive_limits(assignment, state):
            return False
        
        # Branch capacity limits
        if not self._within_branch_capacity(assignment, state):
            return False
        
        # NEW: Check for back-to-back classes of the same type on weekday mornings
        if day in self.weekdays and start_time < '12:00':
            day_level_times = state['branch_day_level_times'].get(branch, {}).get(day, {}).get(level, [])
            
            if day_level_times:
                # Convert to datetime for comparison
                new_start = datetime.strptime(start_time, '%H:%M')
                new_end = datetime.strptime(end_time, '%H:%M')
                
                for existing_start, existing_end in day_level_times:
                    # Check for back-to-back
                    if (existing_end <= new_start and (new_start - existing_end).total_seconds()/60 < self.MIN_BREAK_MINUTES) or \
                       (new_end <= existing_start and (existing_start - new_end).total_seconds()/60 < self.MIN_BREAK_MINUTES):
                        # Only apply penalty in scoring, don't block completely
                        pass
        
        return True
    
    def _has_time_conflict(self, assignment, state):
        """Check for overlapping time assignments"""
        coach_id = assignment['coach_id']
        day = assignment['day']
        start_time = assignment['start_time']
        end_time = assignment['end_time']
        
        new_start = datetime.strptime(start_time, '%H:%M')
        new_end = datetime.strptime(end_time, '%H:%M')
        
        for existing in state['coach_schedules'][coach_id][day]:
            existing_start = datetime.strptime(existing['start_time'], '%H:%M')
            existing_end = datetime.strptime(existing['end_time'], '%H:%M')
            
            if new_start < existing_end and existing_start < new_end:
                return True
        
        return False
    
    def _respects_consecutive_limits(self, assignment, state):
        """Check consecutive class limits with required breaks"""
        coach_id = assignment['coach_id']
        day = assignment['day']
        start_time = assignment['start_time']
        end_time = assignment['end_time']
        
        day_assignments = state['coach_schedules'][coach_id][day].copy()
        day_assignments.append({'start_time': start_time, 'end_time': end_time})
        day_assignments.sort(key=lambda x: datetime.strptime(x['start_time'], '%H:%M'))
        
        consecutive_count = 1
        
        for i in range(1, len(day_assignments)):
            prev_end = datetime.strptime(day_assignments[i-1]['end_time'], '%H:%M')
            curr_start = datetime.strptime(day_assignments[i]['start_time'], '%H:%M')
            
            gap_minutes = (curr_start - prev_end).total_seconds() / 60
            
            if gap_minutes < self.MIN_BREAK_MINUTES:
                consecutive_count += 1
                if consecutive_count > self.CONSECUTIVE_LIMIT:
                    return False
            else:
                consecutive_count = 1
        
        return True
    
    def _within_branch_capacity(self, assignment, state):
        """Check branch capacity constraints"""
        branch = assignment['branch']
        day = assignment['day']
        start_time = assignment['start_time']
        end_time = assignment['end_time']
        
        max_capacity = self.branch_limits.get(branch, 4)
        
        start_dt = datetime.strptime(start_time, '%H:%M')
        end_dt = datetime.strptime(end_time, '%H:%M')
        
        current = start_dt
        while current < end_dt:
            slot_key = current.strftime('%H:%M')
            current_usage = state['branch_time_usage'][branch][day][slot_key]
            
            if current_usage >= max_capacity:
                return False
            
            current += timedelta(minutes=30)
        
        return True
    
    # ==================== LEVEL MERGING AND COMPATIBILITY ====================
    
    def _check_level_compatibility(self, level1, level2):
        """Check if two levels can be merged based on configured distance"""
        if level1 == level2:
            return True
        
        if level1 not in self.level_hierarchy or level2 not in self.level_hierarchy:
            return False
        
        idx1 = self.level_hierarchy.index(level1)
        idx2 = self.level_hierarchy.index(level2)
        
        return abs(idx1 - idx2) <= self.LEVEL_MERGE_DISTANCE
    
    def _update_merge_info(self, assignment, new_level):
        """Update assignment with merge information"""
        if 'merged_levels' not in assignment:
            assignment['merged_levels'] = [assignment['level']]
        
        if new_level not in assignment['merged_levels']:
            assignment['merged_levels'].append(new_level)
            assignment['merged'] = 'Yes'
            assignment['merged_with'] = '+'.join(sorted(assignment['merged_levels']))
    
    def _generate_level_combinations(self, level_gaps):
        """Generate valid level combinations for multi-level classes"""
        combinations = []
        level_gaps.sort(key=lambda x: x[1], reverse=True)
        levels = [lg[0] for lg in level_gaps]
        
        for i in range(len(levels)):
            for j in range(i + 1, len(levels)):
                level1, level2 = levels[i], levels[j]
                if self._check_level_compatibility(level1, level2):
                    gap1 = next(g[1] for g in level_gaps if g[0] == level1)
                    gap2 = next(g[1] for g in level_gaps if g[0] == level2)
                    combinations.append(([level1, level2], gap1 + gap2))
        
        combinations.sort(key=lambda x: x[1], reverse=True)
        return combinations
    
    def _distribute_students_across_levels(self, levels, level_gaps, total_class_size, state):
        """Distribute students proportionally across merged levels"""
        total_gap = sum(gap for level, gap in level_gaps if level in levels)
        
        for level, gap in level_gaps:
            if level in levels and total_gap > 0:
                proportion = gap / total_gap
                assigned = int(total_class_size * proportion)
                req_key = None
                
                for key in state['unassigned_students']:
                    if key[1] == level:
                        req_key = key
                        break
                
                if req_key and assigned > 0:
                    state['unassigned_students'][req_key] = max(0, state['unassigned_students'][req_key] - assigned)
    
    # ==================== COACH MANAGEMENT ====================
    
    def _get_prioritized_coaches(self, branch, level):
        """Get qualified coaches prioritized by type and availability"""
        qualified = []
        
        for coach_list in [self.full_time_coaches, self.part_time_coaches, self.branch_managers]:
            for coach in coach_list:
                if level in coach['qualifications'] and branch in coach['branches']:
                    qualified.append(coach)
        
        qualified.sort(key=lambda c: (
            c['status'] == 'Branch Manager',
            c['status'] != 'Full Time'
        ))
        
        return qualified
    
    def _get_all_qualified_coaches(self, branch, level):
        """Get all coaches qualified for specific branch and level"""
        return [c for c in self.full_time_coaches + self.part_time_coaches + self.branch_managers
                if level in c['qualifications'] and branch in c['branches']]
    
    def _find_multi_qualified_coaches(self, branch, levels):
        """Find coaches qualified for multiple levels"""
        qualified = []
        
        for coach in self.full_time_coaches + self.part_time_coaches + self.branch_managers:
            if (branch in coach['branches'] and 
                all(level in coach['qualifications'] for level in levels)):
                qualified.append(coach)
        
        return qualified
    
    # ==================== ASSIGNMENT FINDING ====================
    
    def _find_optimal_assignment_strict(self, qualified_coaches, branch, level, state, assignment_pool):
        """Find best assignment with strict constraint validation"""
        best_assignment = None
        best_score = -1
        
        for coach in qualified_coaches:
            coach_id = coach['id']
            
            # Check weekly workload limits
            weekly_limit = self._get_coach_weekly_limit(coach)
            if state['coach_workload'][coach_id] >= weekly_limit:
                continue
            
            candidates = [a for a in assignment_pool
                         if (a['coach_id'] == coach_id and 
                             a['branch'] == branch and 
                             a['level'] == level)]
            
            for assignment in candidates:
                if self._validate_strict_workload_constraints(assignment, state):
                    score = self._score_assignment_enhanced(assignment, state)
                    if score > best_score:
                        best_score = score
                        best_assignment = assignment
        
        return best_assignment
    
    def _find_specific_coach_assignment_strict(self, coach_id, branch, level, state, assignment_pool):
        """Find assignment for specific coach with constraint validation"""
        candidates = [a for a in assignment_pool
                     if (a['coach_id'] == coach_id and 
                         a['branch'] == branch and 
                         a['level'] == level)]
        
        candidates.sort(key=lambda a: self._score_assignment_enhanced(a, state), reverse=True)
        
        for assignment in candidates:
            if self._validate_strict_workload_constraints(assignment, state):
                return assignment
        
        return None
    
    def _find_specific_coach_day_assignment_strict(self, coach_id, branch, level, day, state, assignment_pool):
        """Find assignment for specific coach on specific day"""
        candidates = [a for a in assignment_pool
                     if (a['coach_id'] == coach_id and 
                         a['branch'] == branch and 
                         a['level'] == level and
                         a['day'] == day)]
        
        candidates.sort(key=lambda a: self._score_assignment_enhanced(a, state), reverse=True)
        
        for assignment in candidates:
            if self._validate_strict_workload_constraints(assignment, state):
                return assignment
        
        return None
    
    # ==================== ASSIGNMENT CREATION ====================
    
    def _add_validated_assignment_strict(self, assignment, students, state):
        """Add assignment to schedule with strict validation"""
        max_capacity = self.class_capacities.get(assignment['level'], 8)
        if students > max_capacity:
            return False
        
        if not self._validate_strict_workload_constraints(assignment, state):
            return False
        
        assignment_record = {
            'id': assignment['id'],
            'coach_id': assignment['coach_id'],
            'coach_name': assignment['coach_name'],
            'coach_status': assignment['coach_status'],
            'branch': assignment['branch'],
            'level': assignment['level'],
            'day': assignment['day'],
            'start_time': assignment['start_time'],
            'end_time': assignment['end_time'],
            'duration': assignment['duration'],
            'period': assignment['period'],
            'is_popular': assignment.get('is_popular', False),
            'capacity': assignment['capacity'],
            'actual_students': students
        }
        
        state['selected_assignments'].append(assignment_record)
        
        # Update state tracking
        coach_id = assignment['coach_id']
        day = assignment['day']
        branch = assignment['branch']
        level = assignment['level']
        start_time = assignment['start_time']
        end_time = assignment['end_time']
        
        state['coach_schedules'][coach_id][day].append(assignment_record)
        state['coach_daily_hours'][coach_id][day] += assignment['duration']
        state['coach_daily_classes'][coach_id][day] += 1
        state['coach_branch_daily'][coach_id][day] = branch
        state['coach_workload'][coach_id] += 1
        
        # NEW: Update branch-day-time-level tracking for diversity check
        state['branch_time_levels'][branch][day][start_time].add(level)
        
        # NEW: Update branch-day-level-time tracking for back-to-back check
        state['branch_day_level_times'][branch][day][level].append((
            datetime.strptime(start_time, '%H:%M'),
            datetime.strptime(end_time, '%H:%M')
        ))
        
        # Update branch time usage
        start_dt = datetime.strptime(start_time, '%H:%M')
        end_dt = datetime.strptime(end_time, '%H:%M')
        
        current = start_dt
        while current < end_dt:
            slot_key = current.strftime('%H:%M')
            state['branch_time_usage'][branch][day][slot_key] += 1
            current += timedelta(minutes=30)
        
        return True
    
    # ==================== UTILITY FUNCTIONS ====================
    
    def _enhanced_adaptive_shuffle(self):
        """Shuffle assignments for better exploration"""
        print("  Enhanced adaptive shuffling...")
        random.shuffle(self.all_assignments)
        random.shuffle(self.popular_assignments)
        random.shuffle(self.full_time_coaches)
        random.shuffle(self.part_time_coaches)
        random.shuffle(self.branch_managers)
    
    def _count_workload_violations(self, result):
        """Count workload constraint violations"""
        violations = 0
        
        coach_daily_classes = defaultdict(lambda: defaultdict(int))
        for entry in result['schedule']:
            coach_id = entry['Coach ID']
            day = entry['Day']
            coach_daily_classes[coach_id][day] += 1
        
        for coach_id, daily_counts in coach_daily_classes.items():
            for day, count in daily_counts.items():
                limit = self.WEEKEND_DAILY_LIMIT if day in self.weekends else self.WEEKDAY_DAILY_LIMIT
                
                if count > limit:
                    violations += 1
        
        return violations
    
    def _count_violations(self, result):
        """Count general constraint violations"""
        violations = 0
        
        # Check class capacities
        for entry in result['schedule']:
            level = entry['Gymnastics Level']
            students = entry['Students']
            max_capacity = self.class_capacities.get(level, 8)
            
            if students > max_capacity:
                violations += 1
        
        # Check branch assignments (one branch per day)
        coach_day_branches = defaultdict(lambda: defaultdict(set))
        for entry in result['schedule']:
            coach_id = entry['Coach ID']
            day = entry['Day']
            branch = entry['Branch']
            coach_day_branches[coach_id][day].add(branch)
        
        for coach_id, day_branches in coach_day_branches.items():
            for day, branches in day_branches.items():
                if len(branches) > 1:
                    violations += 1
        
        # Check consecutive limits
        coach_day_assignments = defaultdict(lambda: defaultdict(list))
        for entry in result['schedule']:
            coach_id = entry['Coach ID']
            day = entry['Day']
            coach_day_assignments[coach_id][day].append(entry)
        
        for coach_id, day_assignments in coach_day_assignments.items():
            for day, assignments in day_assignments.items():
                if len(assignments) > 1:
                    assignments.sort(key=lambda x: datetime.strptime(x['Start Time'], '%H:%M'))
                    
                    consecutive_count = 1
                    for i in range(1, len(assignments)):
                        prev_end = datetime.strptime(assignments[i-1]['End Time'], '%H:%M')
                        curr_start = datetime.strptime(assignments[i]['Start Time'], '%H:%M')
                        
                        gap_minutes = (curr_start - prev_end).total_seconds() / 60
                        
                        if gap_minutes < self.MIN_BREAK_MINUTES:
                            consecutive_count += 1
                            if consecutive_count > self.CONSECUTIVE_LIMIT:
                                violations += 1
                                break
                        else:
                            consecutive_count = 1
        
        return violations
    
    def _identify_gaps(self, result):
        """Identify unmet student requirements"""
        scheduled_students = defaultdict(int)
        
        for entry in result['schedule']:
            key = (entry['Branch'], entry['Gymnastics Level'])
            scheduled_students[key] += entry['Students']
        
        gaps = []
        for req_key, required in self.enrollment_dict.items():
            scheduled = scheduled_students.get(req_key, 0)
            if scheduled < required:
                gaps.append((req_key, required - scheduled))
        
        return gaps
    
    def _add_detailed_statistics(self, result):
        """Add detailed statistics to the result"""
        schedule = result['schedule']
        
        # Classes by level
        classes_by_level = defaultdict(int)
        students_by_level = defaultdict(int)
        for entry in schedule:
            level = entry['Gymnastics Level']
            classes_by_level[level] += 1
            students_by_level[level] += entry['Students']
        
        # Coach utilization statistics
        coach_classes = defaultdict(int)
        coach_students = defaultdict(int)
        coach_type_usage = defaultdict(lambda: {'coaches': set(), 'classes': 0, 'students': 0})
        
        for entry in schedule:
            coach_id = entry['Coach ID']
            coach_status = entry['Coach Status']
            coach_classes[coach_id] += 1
            coach_students[coach_id] += entry['Students']
            
            coach_type_usage[coach_status]['coaches'].add(coach_id)
            coach_type_usage[coach_status]['classes'] += 1
            coach_type_usage[coach_status]['students'] += entry['Students']
        
        # Coach type statistics
        coach_type_statistics = {}
        for coach_type, usage in coach_type_usage.items():
            total_of_type = len([c for c in self.coaches_data.values() if c['status'] == coach_type])
            coaches_used = len(usage['coaches'])
            
            coach_type_statistics[coach_type] = {
                'total_coaches': total_of_type,
                'coaches_used': coaches_used,
                'utilization_rate': round(coaches_used / max(1, total_of_type) * 100, 2),
                'total_classes': usage['classes'],
                'total_students': usage['students'],
                'classes_per_coach': round(usage['classes'] / max(1, coaches_used), 2)
            }
        
        # Individual coach statistics
        all_coach_statistics = {}
        for coach_id, coach_data in self.coaches_data.items():
            classes = coach_classes.get(coach_id, 0)
            students = coach_students.get(coach_id, 0)
            
            all_coach_statistics[coach_id] = {
                'name': coach_data.get('name', f"Coach {coach_id}"),
                'status': coach_data.get('status', 'Unknown'),
                'classes': classes,
                'students': students
            }
        
        # Branch statistics
        classes_by_branch = defaultdict(int)
        students_by_branch = defaultdict(int)
        for entry in schedule:
            branch = entry['Branch']
            classes_by_branch[branch] += 1
            students_by_branch[branch] += entry['Students']
        
        # Day distribution
        classes_by_day = defaultdict(int)
        students_by_day = defaultdict(int)
        for entry in schedule:
            day = entry['Day']
            classes_by_day[day] += 1
            students_by_day[day] += entry['Students']
        
        # Time slot distribution
        classes_by_hour = defaultdict(int)
        for entry in schedule:
            start_hour = int(entry['Start Time'].split(':')[0])
            classes_by_hour[start_hour] += 1
        
        # Popular slot usage
        popular_slots = len([e for e in schedule if e.get('Popular Slot') == 'Yes'])
        merged_classes = len([e for e in schedule if e.get('Merged') == 'Yes'])
        
        # Add detailed statistics to result
        result['detailed_statistics'] = {
            'classes_by_level': dict(classes_by_level),
            'students_by_level': dict(students_by_level),
            'coach_type_statistics': coach_type_statistics,
            'all_coach_statistics': all_coach_statistics,
            'classes_by_branch': dict(classes_by_branch),
            'students_by_branch': dict(students_by_branch),
            'classes_by_day': dict(classes_by_day),
            'students_by_day': dict(students_by_day),
            'classes_by_hour': dict(classes_by_hour),
            'popular_slot_usage': popular_slots,
            'merged_classes': merged_classes,
            'weekend_classes': sum(classes_by_day.get(day, 0) for day in self.weekends),
            'weekday_classes': sum(classes_by_day.get(day, 0) for day in self.weekdays),
            'back_to_back_same_type': self._count_back_to_back_same_type_classes(schedule),
            'same_time_diverse_classes': self._count_diverse_class_times(schedule)
        }
        
        return result
    
    def _count_back_to_back_same_type_classes(self, schedule):
        """Count back-to-back classes of same type on weekday mornings"""
        back_to_back_count = 0
        
        # Group by branch, day, level
        branch_day_level_classes = defaultdict(list)
        for entry in schedule:
            branch = entry['Branch']
            day = entry['Day']
            level = entry['Gymnastics Level']
            start_time = entry['Start Time']
            end_time = entry['End Time']
            students = entry['Students']
            capacity = entry['Capacity']
            key = (branch, day, level)
            
            # Only check weekday mornings
            if day in self.weekdays and start_time < '12:00':
                branch_day_level_classes[key].append({
                    'start_time': start_time,
                    'end_time': end_time,
                    'students': students,
                    'capacity': capacity
                })
        
        # Check for back-to-back classes
        for key, classes in branch_day_level_classes.items():
            if len(classes) <= 1:
                continue
            
            # Sort by start time
            classes.sort(key=lambda x: x['start_time'])
            
            for i in range(len(classes) - 1):
                class1 = classes[i]
                class2 = classes[i+1]
                
                # Calculate time gap
                end1 = datetime.strptime(class1['end_time'], '%H:%M')
                start2 = datetime.strptime(class2['start_time'], '%H:%M')
                gap_minutes = (start2 - end1).total_seconds() / 60
                
                # Check if back-to-back and if first class is not full
                if gap_minutes < self.MIN_BREAK_MINUTES and class1['students'] < class1['capacity']:
                    back_to_back_count += 1
        
        return back_to_back_count
    
    def _count_diverse_class_times(self, schedule):
        """Count time slots with diverse class types"""
        diverse_time_count = 0
        
        # Group by branch, day, start_time
        branch_day_time_classes = defaultdict(list)
        for entry in schedule:
            branch = entry['Branch']
            day = entry['Day']
            start_time = entry['Start Time']
            level = entry['Gymnastics Level']
            key = (branch, day, start_time)
            branch_day_time_classes[key].append(level)
        
        # Count diverse time slots
        for levels in branch_day_time_classes.values():
            if len(levels) > 1 and len(set(levels)) > 1:
                diverse_time_count += 1
        
        return diverse_time_count
    
    def _print_final_statistics(self, result):
        """Print comprehensive final statistics"""
        print("\nSCHEDULE STATISTICS SUMMARY")
        print("-" * 40)
        
        stats = result['statistics']
        detailed = result.get('detailed_statistics', {})
        
        # Coverage statistics
        print(f"Coverage: {stats['coverage_percentage']:.2f}% ({stats['total_students_scheduled']}/{stats['total_students_required']} students)")
        print(f"Total classes scheduled: {stats['total_classes']}")
        
        # Level distribution
        print("\nCLASSES BY LEVEL:")
        level_stats = detailed.get('classes_by_level', {})
        for level in self.level_hierarchy:
            if level in level_stats:
                students = detailed.get('students_by_level', {}).get(level, 0)
                print(f"  {level}: {level_stats[level]} classes, {students} students")
        
        # Coach utilization
        print("\nCOACH UTILIZATION BY TYPE:")
        coach_stats = detailed.get('coach_type_statistics', {})
        for coach_type in ['Full Time', 'Part Time', 'Branch Manager']:
            if coach_type in coach_stats:
                type_stats = coach_stats[coach_type]
                print(f"  {coach_type}: {type_stats['coaches_used']}/{type_stats['total_coaches']} coaches used ({type_stats['utilization_rate']}%)")
                print(f"    Classes: {type_stats['total_classes']} ({type_stats['classes_per_coach']} per coach)")
                print(f"    Students: {type_stats['total_students']}")
        
        # Individual coach statistics
        print("\nINDIVIDUAL COACH STATISTICS:")
        all_coach_stats = detailed.get('all_coach_statistics', {})
        # Sort coaches by status and number of classes
        sorted_coaches = sorted(
            all_coach_stats.items(),
            key=lambda x: (
                0 if x[1]['status'] == 'Full Time' else (1 if x[1]['status'] == 'Part Time' else 2),
                -x[1]['classes']  # Descending by class count
            )
        )
        
        for coach_id, coach_stats in sorted_coaches:
            print(f"  {coach_stats['name']} ({coach_stats['status']}): {coach_stats['classes']} classes, {coach_stats['students']} students")
        
        # Branch distribution
        print("\nBRANCH DISTRIBUTION:")
        branch_stats = detailed.get('classes_by_branch', {})
        for branch in sorted(branch_stats.keys()):
            students = detailed.get('students_by_branch', {}).get(branch, 0)
            print(f"  {branch}: {branch_stats[branch]} classes, {students} students")
        
        # Day distribution
        print("\nDAY DISTRIBUTION:")
        day_stats = detailed.get('classes_by_day', {})
        for day in ['TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN']:
            if day in day_stats:
                students = detailed.get('students_by_day', {}).get(day, 0)
                print(f"  {day}: {day_stats[day]} classes, {students} students")
        
        # Weekday vs Weekend
        if 'weekend_classes' in detailed and 'weekday_classes' in detailed:
            total_classes = detailed['weekend_classes'] + detailed['weekday_classes']
            if total_classes > 0:
                weekend_pct = (detailed['weekend_classes'] / total_classes) * 100
                print(f"\nWeekday vs Weekend: {detailed['weekday_classes']} weekday classes, {detailed['weekend_classes']} weekend classes ({weekend_pct:.1f}% weekend)")
        
        # NEW: Back-to-back and diversity metrics
        print("\nSPECIAL METRICS:")
        print(f"  Back-to-back same type classes on weekday mornings: {detailed.get('back_to_back_same_type', 0)}")
        print(f"  Time slots with diverse class types: {detailed.get('same_time_diverse_classes', 0)}")
        print(f"  Merged classes: {detailed.get('merged_classes', 0)}")
        print(f"  Popular slots used: {detailed.get('popular_slot_usage', 0)}")
        
        if 'validation' in result:
            val_status = result['validation']['status']
            print(f"\nValidation Status: {val_status}")
            if val_status == 'PASSED_WITH_WARNINGS':
                warning_count = len(result['validation'].get('warnings', []))
                print(f"  Warnings: {warning_count}")
        
        print("\nScheduling complete.")
        print("-" * 40)

    def _build_and_validate_result(self, state):
        """Build final schedule and calculate statistics"""
        schedule = []
        for assignment in state['selected_assignments']:
            entry = {
                'Branch': assignment['branch'],
                'Day': assignment['day'],
                'Start Time': assignment['start_time'],
                'End Time': assignment['end_time'],
                'Gymnastics Level': assignment['level'],
                'Coach ID': assignment['coach_id'],
                'Coach Name': assignment['coach_name'],
                'Coach Status': assignment['coach_status'],
                'Students': assignment['actual_students'],
                'Capacity': assignment['capacity'],
                'Duration (min)': assignment['duration'],
                'Popular Slot': 'Yes' if assignment.get('is_popular', False) else 'No',
                'Merged': assignment.get('merged', 'No'),
                'Merged With': assignment.get('merged_with', '')
            }
            schedule.append(entry)
        
        # Sort schedule chronologically
        day_order = {'TUE': 0, 'WED': 1, 'THU': 2, 'FRI': 3, 'SAT': 4, 'SUN': 5}
        schedule.sort(key=lambda x: (day_order.get(x['Day'], 6), x['Start Time'], x['Branch']))
        
        # Calculate statistics
        total_students_scheduled = sum(entry['Students'] for entry in schedule)
        coverage_percentage = (total_students_scheduled / self.total_students_required * 100) if self.total_students_required > 0 else 0
        
        # Coach utilization statistics
        coach_workload = defaultdict(int)
        for entry in schedule:
            coach_workload[entry['Coach ID']] += 1
        
        coach_utilization = {}
        for status in ['Full Time', 'Part Time', 'Branch Manager']:
            status_coaches = [c for c in self.coaches_data.values() if c['status'] == status]
            total_coaches = len(status_coaches)
            
            total_classes = sum(coach_workload.get(c['id'], 0) for c in status_coaches)
            coaches_used = len([c for c in status_coaches if coach_workload.get(c['id'], 0) > 0])
            
            avg_classes = total_classes / total_coaches if total_coaches > 0 else 0
            utilization_rate = coaches_used / total_coaches * 100 if total_coaches > 0 else 0
            
            coach_utilization[status] = {
                'total_coaches': total_coaches,
                'coaches_used': coaches_used,
                'total_classes': total_classes,
                'avg_classes_per_coach': avg_classes,
                'utilization_rate': utilization_rate
            }
        
        return {
            'schedule': schedule,
            'statistics': {
                'total_classes': len(schedule),
                'total_students_scheduled': total_students_scheduled,
                'total_students_required': self.total_students_required,
                'coverage_percentage': coverage_percentage,
                'perfect_coverage': coverage_percentage >= 100.0,
                'coach_utilization': coach_utilization,
                'popular_slots_used': len([s for s in schedule if s['Popular Slot'] == 'Yes']),
                'total_slots': len(schedule),
                'merged_classes': len([s for s in schedule if s['Merged'] == 'Yes'])
            },
            'success': True
        }
    
    def _create_best_effort_strict_result(self):
        """Create fallback result with strict constraint enforcement"""
        print("Creating best effort result with strict workload limits...")
        
        state = self._initialize_enhanced_state()
        
        for req_key, students in self.enrollment_dict.items():
            branch, level = req_key
            
            qualified_coaches = self._get_all_qualified_coaches(branch, level)
            if qualified_coaches:
                assignment = self._find_optimal_assignment_strict(qualified_coaches, branch, level, state, self.all_assignments)
                
                if assignment:
                    capacity = self.class_capacities.get(level, 8)
                    class_size = min(students, capacity)
                    if self._add_validated_assignment_strict(assignment, class_size, state):
                        state['unassigned_students'][req_key] = students - class_size
        
        return self._build_and_validate_result(state)


def execute_enhanced_strict_constraint_scheduling(data):
    """Execute the enhanced scheduling algorithm"""
    scheduler = EnhancedStrictConstraintScheduler(data)
    result = scheduler.schedule_with_complete_coverage()
    return result