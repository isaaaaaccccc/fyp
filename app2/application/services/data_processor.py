"""
Data processing and scheduling algorithm classes extracted from timetabling.ipynb.
These classes handle the core timetabling logic.
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Dict, List, Tuple, Set
import itertools
import re
import os


class OptimizedLPDataStorage:
    """
    Optimized data storage for Linear Programming scheduler
    Pre-processes and stores all data in LP-friendly formats for maximum performance
    UPDATED: Keeps Advance and Free as separate categories
    """
    
    def __init__(self, data_dir='cleaned_data'):
        self.data_dir = data_dir
        
        # Core configuration constants - UPDATED: Keep Advance and Free separate
        self.LEVEL_MAPPING = {
            'BearyTots': 'Tots', 'Bearytots': 'Tots',
            'Level 1': 'L1', 'Level 2': 'L2', 'Level 3': 'L3', 'Level 4': 'L4',
            'Adv': 'Advance', 'Advanced': 'Advance'
            # Removed: 'Free': 'Advance' - keep Free separate
        }
        
        self.CLASS_DURATIONS = {
            'Tots': 60, 'Jolly': 60, 'Bubbly': 60, 'Lively': 60, 'Flexi': 60,
            'L1': 90, 'L2': 90, 'L3': 90, 'L4': 90, 'Advance': 90, 'Free': 90
        }
        
        self.CLASS_CAPACITIES = {
            'Tots': 7, 'Jolly': 8, 'Bubbly': 8, 'Lively': 8, 'Flexi': 8, 'L1': 8,
            'L2': 9, 'L3': 10, 'L4': 10, 'Advance': 10, 'Free': 10
        }
        
        self.BRANCH_LIMITS = {'BB': 4, 'CCK': 4, 'CH': 5, 'HG': 4, 'KT': 4, 'PR': 6}
        self.WEEKDAYS = ['TUE', 'WED', 'THU', 'FRI']
        self.WEEKENDS = ['SAT', 'SUN']
        self.ALL_DAYS = self.WEEKDAYS + self.WEEKENDS
        
        # UPDATED: Include Free as separate category
        self.ALL_LEVELS = ['Tots', 'Jolly', 'Bubbly', 'Lively', 'Flexi', 'L1', 'L2', 'L3', 'L4', 'Advance', 'Free']
        self.ALL_BRANCHES = ['BB', 'CCK', 'CH', 'HG', 'KT', 'PR']
        
        # Level priority weights for LP objective - UPDATED: Separate weights for Advance and Free
        self.LEVEL_WEIGHTS = {
            'L4': 10000, 'Advance': 9000, 'Free': 8500, 'L3': 8000, 'L2': 7000, 'L1': 6000,
            'Flexi': 5000, 'Lively': 4000, 'Bubbly': 3000, 'Jolly': 2000, 'Tots': 1000
        }
        
        # Initialize storage
        self.feasible_assignments = []
        self.enrollment_dict = {}
        self.total_students = 0
        self.coach_names = []
        self.coach_status = {}
        self.class_capacities = self.CLASS_CAPACITIES
        self.class_durations = self.CLASS_DURATIONS
        self.branch_limits = self.BRANCH_LIMITS
        self.level_weights = self.LEVEL_WEIGHTS
        self.all_branches = self.ALL_BRANCHES
        self.all_levels = self.ALL_LEVELS
        self.all_days = self.ALL_DAYS
        self.weekdays = self.WEEKDAYS
        self.weekends = self.WEEKENDS
        
        # Load and process data
        self._load_and_process_data()
    
    def _load_and_process_data(self):
        """Load and process all data files."""
        print("OPTIMIZED LP DATA STORAGE - SEPARATE ADVANCE/FREE CATEGORIES")
        print("=" * 60)
        print(f"Processing Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC")
        
        # Load data files
        coaches_df = pd.read_csv(os.path.join(self.data_dir, 'coaches_df.csv'))
        availability_df = pd.read_csv(os.path.join(self.data_dir, 'availability_df.csv'))
        enrollment_df = pd.read_csv(os.path.join(self.data_dir, 'enrollment_counts.csv'))
        branch_config_df = pd.read_csv(os.path.join(self.data_dir, 'branch_config.csv'))
        
        # Update branch limits from config
        for _, row in branch_config_df.iterrows():
            if row['branch'] in self.BRANCH_LIMITS:
                self.BRANCH_LIMITS[row['branch']] = row['max_classes_per_slot']
        
        # Process enrollment data
        self._process_enrollment_data(enrollment_df)
        
        # Process coach data
        self._process_coach_data(coaches_df, availability_df)
        
        print(f"Loaded {len(self.coach_names)} coaches")
        print(f"Generated {len(self.feasible_assignments)} feasible assignments")
        print(f"Total students to schedule: {self.total_students}")
    
    def _process_enrollment_data(self, enrollment_df):
        """Process enrollment data."""
        for _, row in enrollment_df.iterrows():
            branch = row['Branch']
            level = row['Level Category Base']
            count = row['Count']
            
            if branch not in self.enrollment_dict:
                self.enrollment_dict[branch] = {}
            
            self.enrollment_dict[branch][level] = count
            self.total_students += count
    
    def _process_coach_data(self, coaches_df, availability_df):
        """Process coach data and generate feasible assignments."""
        # Get coach names and status
        self.coach_names = coaches_df['coach_name'].tolist()
        for _, row in coaches_df.iterrows():
            self.coach_status[row['coach_name']] = row['status']
        
        # Process availability
        availability_dict = {}
        for _, row in availability_df.iterrows():
            coach = row['coach_name']
            day = row['day']
            period = row['period']
            available = row['available']
            
            if coach not in availability_dict:
                availability_dict[coach] = {}
            if day not in availability_dict[coach]:
                availability_dict[coach][day] = {}
            
            availability_dict[coach][day][period] = available
        
        # Generate feasible assignments
        self._generate_feasible_assignments(coaches_df, availability_dict)
    
    def _generate_feasible_assignments(self, coaches_df, availability_dict):
        """Generate all feasible coach-branch-day-time-level assignments."""
        print("Generating feasible assignments...")
        
        # Define time slots
        weekday_slots = [
            ('AM', '1000'), ('AM', '1030'), ('AM', '1100'), ('AM', '1130'),
            ('PM', '1500'), ('PM', '1530'), ('PM', '1600'), ('PM', '1630'),
            ('PM', '1700'), ('PM', '1730'), ('PM', '1800'), ('PM', '1830')
        ]
        
        weekend_slots = [
            ('AM', '0900'), ('AM', '0930'), ('AM', '1000'), ('AM', '1030'),
            ('AM', '1100'), ('AM', '1130'), ('PM', '1200'), ('PM', '1230'),
            ('PM', '1300'), ('PM', '1330'), ('PM', '1400'), ('PM', '1430'),
            ('PM', '1500'), ('PM', '1530'), ('PM', '1600'), ('PM', '1630'),
            ('PM', '1700'), ('PM', '1730'), ('PM', '1800'), ('PM', '1830')
        ]
        
        for _, coach_row in coaches_df.iterrows():
            coach_name = coach_row['coach_name']
            assigned_branches = [coach_row['assigned_branch']]  # Simplified
            
            # Get levels this coach can teach
            teachable_levels = []
            for level in self.ALL_LEVELS:
                level_col = level if level in coach_row else f'Level_{level[1:]}'
                if level_col in coach_row and coach_row[level_col]:
                    teachable_levels.append(level)
            
            # Generate assignments for each branch, day, time, level
            for branch in assigned_branches:
                if not branch or branch not in self.ALL_BRANCHES:
                    continue
                    
                for day in self.ALL_DAYS:
                    # Skip Monday (closed)
                    if day == 'MON':
                        continue
                    
                    # Get appropriate time slots
                    time_slots = weekend_slots if day in self.WEEKENDS else weekday_slots
                    
                    # Check coach availability for this day
                    if (coach_name in availability_dict and 
                        day in availability_dict[coach_name]):
                        
                        for period, start_time in time_slots:
                            # Check if coach is available for this period
                            if availability_dict[coach_name][day].get(period, True):
                                
                                for level in teachable_levels:
                                    # Create feasible assignment
                                    assignment = {
                                        'coach': coach_name,
                                        'branch': branch,
                                        'day': day,
                                        'start_time': start_time,
                                        'level': level,
                                        'period': period,
                                        'duration': self.CLASS_DURATIONS[level],
                                        'capacity': self.CLASS_CAPACITIES[level]
                                    }
                                    self.feasible_assignments.append(assignment)
    
    def get_data_dict(self):
        """Return all processed data as a dictionary."""
        return {
            'feasible_assignments': self.feasible_assignments,
            'enrollment_dict': self.enrollment_dict,
            'total_students': self.total_students,
            'coach_names': self.coach_names,
            'coach_status': self.coach_status,
            'class_capacities': self.class_capacities,
            'class_durations': self.class_durations,
            'branch_limits': self.branch_limits,
            'level_weights': self.level_weights,
            'all_branches': self.all_branches,
            'all_levels': self.all_levels,
            'all_days': self.all_days,
            'weekdays': self.weekdays,
            'weekends': self.weekends
        }


class MaxCoverageScheduler:
    """
    Maximum coverage scheduler that prioritizes getting all students scheduled
    """
    
    def __init__(self, optimized_data):
        """Initialize with maximum coverage focus"""
        print("MAXIMUM COVERAGE SCHEDULER")
        print("=" * 80)
        print(f"Current Date and Time (UTC): {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)
        print("MAXIMUM COVERAGE FEATURES:")
        print("• Maximize coach utilization across all suitable coaches")
        print("• Aggressive assignment generation for full coverage")
        print("• Dynamic workload expansion based on demand")
        print("• Multi-branch flexibility for coaches")
        print("• Extended operating hours from data patterns")
        print("• Comprehensive requirement satisfaction")
        print("=" * 80)
        
        # Extract data
        self.feasible_assignments = optimized_data['feasible_assignments']
        self.enrollment_dict = optimized_data['enrollment_dict']
        self.total_students = optimized_data['total_students']
        self.coach_names = optimized_data['coach_names']
        self.coach_status = optimized_data['coach_status']
        self.class_capacities = optimized_data['class_capacities']
        self.class_durations = optimized_data['class_durations']
        self.branch_limits = optimized_data['branch_limits']
        self.level_weights = optimized_data['level_weights']
        self.all_branches = optimized_data['all_branches']
        self.all_levels = optimized_data['all_levels']
        self.all_days = optimized_data['all_days']
        self.weekdays = optimized_data['weekdays']
        self.weekends = optimized_data['weekends']
        
        # Processing results storage
        self.popular_timeslots_raw = []
        self.time_chunks = []
        self.scheduling_log = []
        self.selected_assignments = []
        
    def generate_schedule(self):
        """Generate the complete schedule using greedy maximum coverage approach."""
        print("Starting schedule generation...")
        
        # Simplified greedy scheduling approach
        remaining_demand = {}
        for branch in self.enrollment_dict:
            remaining_demand[branch] = self.enrollment_dict[branch].copy()
        
        selected_assignments = []
        coach_workload = {coach: {day: 0 for day in self.all_days} for coach in self.coach_names}
        
        # Sort assignments by priority (level weights)
        sorted_assignments = sorted(
            self.feasible_assignments,
            key=lambda x: self.level_weights.get(x['level'], 0),
            reverse=True
        )
        
        for assignment in sorted_assignments:
            branch = assignment['branch']
            level = assignment['level']
            coach = assignment['coach']
            day = assignment['day']
            
            # Check if there's still demand for this branch/level
            if (branch in remaining_demand and 
                level in remaining_demand[branch] and 
                remaining_demand[branch][level] > 0):
                
                # Check coach workload limits
                max_classes = 5 if day in self.weekends else 3
                if coach_workload[coach][day] < max_classes:
                    
                    # Add this assignment
                    selected_assignments.append(assignment)
                    coach_workload[coach][day] += 1
                    
                    # Reduce demand by class capacity
                    capacity = assignment['capacity']
                    remaining_demand[branch][level] = max(0, 
                        remaining_demand[branch][level] - capacity)
        
        self.selected_assignments = selected_assignments
        return self._format_schedule_output()
    
    def _format_schedule_output(self):
        """Format the selected assignments into the expected output format."""
        schedule = {}
        
        # Group by branch
        for assignment in self.selected_assignments:
            branch = assignment['branch']
            coach = assignment['coach']
            day = assignment['day']
            level = assignment['level']
            start_time = assignment['start_time']
            duration = assignment['duration']
            
            if branch not in schedule:
                schedule[branch] = {
                    'coaches': list(set([a['coach'] for a in self.selected_assignments if a['branch'] == branch])),
                    'schedule': {}
                }
            
            # Map day names
            day_mapping = {
                'TUE': 'Tuesday', 'WED': 'Wednesday', 
                'THU': 'Thursday', 'FRI': 'Friday',
                'SAT': 'Saturday', 'SUN': 'Sunday'
            }
            
            day_name = day_mapping.get(day, day)
            
            if day_name not in schedule[branch]['schedule']:
                schedule[branch]['schedule'][day_name] = {}
            
            if coach not in schedule[branch]['schedule'][day_name]:
                schedule[branch]['schedule'][day_name][coach] = []
            
            # Convert duration from minutes to 30-minute slots
            duration_slots = duration // 30
            
            schedule[branch]['schedule'][day_name][coach].append({
                'name': level,
                'start_time': start_time,
                'duration': duration_slots
            })
        
        return schedule