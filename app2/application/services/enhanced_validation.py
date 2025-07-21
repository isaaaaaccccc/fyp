"""
Additional validation and configuration utilities for the Enhanced Timetabling System.
"""
from typing import Dict, List, Any
import pandas as pd
from collections import defaultdict


class ScheduleValidator:
    """Advanced validation for enhanced schedules."""
    
    def __init__(self, schedule: List[Dict[str, Any]], config: Dict[str, Any]):
        self.schedule = schedule
        self.config = config
        self.workload_limits = config.get('workload_limits', {})
    
    def validate_comprehensive(self) -> Dict[str, Any]:
        """Perform comprehensive schedule validation."""
        validation = {
            'overall_valid': True,
            'constraint_violations': {
                'workload': self._validate_workload_constraints(),
                'time_conflicts': self._validate_time_conflicts(),
                'capacity': self._validate_capacity_constraints(),
                'popular_slots': self._validate_popular_slot_usage()
            },
            'quality_metrics': {
                'coverage_efficiency': self._calculate_coverage_efficiency(),
                'coach_utilization_balance': self._calculate_coach_balance(),
                'time_distribution': self._analyze_time_distribution(),
                'branch_balance': self._analyze_branch_balance()
            },
            'recommendations': []
        }
        
        # Overall validity check
        for category, violations in validation['constraint_violations'].items():
            if violations['count'] > 0:
                validation['overall_valid'] = False
        
        # Generate recommendations
        validation['recommendations'] = self._generate_recommendations(validation)
        
        return validation
    
    def _validate_workload_constraints(self) -> Dict[str, Any]:
        """Validate workload constraints for all coaches."""
        violations = {'count': 0, 'details': [], 'summary': {}}
        coach_workloads = defaultdict(lambda: {'weekly': 0, 'daily': defaultdict(int)})
        
        # Calculate workloads
        for cls in self.schedule:
            coach_id = cls['Coach ID']
            day = cls['Day']
            coach_workloads[coach_id]['weekly'] += 1
            coach_workloads[coach_id]['daily'][day] += 1
        
        # Check against limits
        for coach_id, workload in coach_workloads.items():
            # Get coach position to determine limits
            position = 'Full Time'  # Default
            limits = self.workload_limits.get(position, {'weekly': 25, 'weekend_daily': 5, 'weekday_daily': 3})
            
            # Check weekly limit
            if workload['weekly'] > limits['weekly']:
                violations['count'] += 1
                violations['details'].append({
                    'coach_id': coach_id,
                    'violation_type': 'weekly_limit',
                    'current': workload['weekly'],
                    'limit': limits['weekly']
                })
            
            # Check daily limits
            weekends = ['SAT', 'SUN']
            for day, daily_count in workload['daily'].items():
                daily_limit = limits['weekend_daily'] if day in weekends else limits['weekday_daily']
                if daily_count > daily_limit:
                    violations['count'] += 1
                    violations['details'].append({
                        'coach_id': coach_id,
                        'violation_type': 'daily_limit',
                        'day': day,
                        'current': daily_count,
                        'limit': daily_limit
                    })
        
        violations['summary'] = {
            'coaches_checked': len(coach_workloads),
            'average_weekly_load': sum(w['weekly'] for w in coach_workloads.values()) / len(coach_workloads) if coach_workloads else 0
        }
        
        return violations
    
    def _validate_time_conflicts(self) -> Dict[str, Any]:
        """Check for time conflicts for coaches."""
        conflicts = {'count': 0, 'details': []}
        
        # Group by coach and day
        coach_schedule = defaultdict(lambda: defaultdict(list))
        for cls in self.schedule:
            coach_id = cls['Coach ID']
            day = cls['Day']
            start_time = cls['Start Time']
            end_time = cls['End Time']
            coach_schedule[coach_id][day].append({
                'start': start_time,
                'end': end_time,
                'class': cls
            })
        
        # Check for overlaps
        for coach_id, days in coach_schedule.items():
            for day, classes in days.items():
                sorted_classes = sorted(classes, key=lambda x: x['start'])
                
                for i in range(len(sorted_classes) - 1):
                    current = sorted_classes[i]
                    next_class = sorted_classes[i + 1]
                    
                    if current['end'] > next_class['start']:
                        conflicts['count'] += 1
                        conflicts['details'].append({
                            'coach_id': coach_id,
                            'day': day,
                            'conflict': f"{current['start']}-{current['end']} overlaps {next_class['start']}-{next_class['end']}"
                        })
        
        return conflicts
    
    def _validate_capacity_constraints(self) -> Dict[str, Any]:
        """Validate class capacity constraints."""
        violations = {'count': 0, 'details': []}
        
        class_capacities = {
            'Tots': 7, 'Jolly': 8, 'Bubbly': 8, 'Lively': 8, 'Flexi': 8, 'L1': 8,
            'L2': 9, 'L3': 10, 'L4': 10, 'Advance': 10, 'Free': 10
        }
        
        for cls in self.schedule:
            level = cls['Gymnastics Level']
            students = cls['Students']
            max_capacity = class_capacities.get(level, 8)
            
            if students > max_capacity:
                violations['count'] += 1
                violations['details'].append({
                    'class': cls,
                    'level': level,
                    'students': students,
                    'max_capacity': max_capacity
                })
        
        return violations
    
    def _validate_popular_slot_usage(self) -> Dict[str, Any]:
        """Analyze popular time slot usage."""
        popular_usage = {'total_popular': 0, 'total_classes': len(self.schedule), 'percentage': 0}
        
        for cls in self.schedule:
            if cls['Popular Slot'] == 'Yes':
                popular_usage['total_popular'] += 1
        
        if popular_usage['total_classes'] > 0:
            popular_usage['percentage'] = (popular_usage['total_popular'] / popular_usage['total_classes']) * 100
        
        return popular_usage
    
    def _calculate_coverage_efficiency(self) -> float:
        """Calculate how efficiently the schedule covers demand."""
        if not self.schedule:
            return 0.0
        
        total_students = sum(cls['Students'] for cls in self.schedule)
        total_capacity = len(self.schedule) * 8  # Average capacity
        
        return (total_students / total_capacity * 100) if total_capacity > 0 else 0.0
    
    def _calculate_coach_balance(self) -> Dict[str, Any]:
        """Calculate coach utilization balance."""
        coach_loads = defaultdict(int)
        
        for cls in self.schedule:
            coach_loads[cls['Coach ID']] += 1
        
        if not coach_loads:
            return {'balance_score': 0, 'min_load': 0, 'max_load': 0, 'std_dev': 0}
        
        loads = list(coach_loads.values())
        min_load = min(loads)
        max_load = max(loads)
        avg_load = sum(loads) / len(loads)
        
        # Calculate standard deviation
        variance = sum((load - avg_load) ** 2 for load in loads) / len(loads)
        std_dev = variance ** 0.5
        
        # Balance score (lower is better)
        balance_score = std_dev / avg_load if avg_load > 0 else 0
        
        return {
            'balance_score': balance_score,
            'min_load': min_load,
            'max_load': max_load,
            'std_dev': std_dev,
            'avg_load': avg_load
        }
    
    def _analyze_time_distribution(self) -> Dict[str, Any]:
        """Analyze distribution of classes across time slots."""
        time_distribution = defaultdict(int)
        day_distribution = defaultdict(int)
        
        for cls in self.schedule:
            time_distribution[cls['Start Time']] += 1
            day_distribution[cls['Day']] += 1
        
        return {
            'time_slots': dict(time_distribution),
            'days': dict(day_distribution),
            'peak_time': max(time_distribution.items(), key=lambda x: x[1])[0] if time_distribution else None,
            'peak_day': max(day_distribution.items(), key=lambda x: x[1])[0] if day_distribution else None
        }
    
    def _analyze_branch_balance(self) -> Dict[str, Any]:
        """Analyze balance across branches."""
        branch_stats = defaultdict(lambda: {'classes': 0, 'students': 0, 'coaches': set()})
        
        for cls in self.schedule:
            branch = cls['Branch']
            branch_stats[branch]['classes'] += 1
            branch_stats[branch]['students'] += cls['Students']
            branch_stats[branch]['coaches'].add(cls['Coach ID'])
        
        # Convert to regular dict and calculate coaches count
        result = {}
        for branch, stats in branch_stats.items():
            result[branch] = {
                'classes': stats['classes'],
                'students': stats['students'],
                'coaches': len(stats['coaches'])
            }
        
        return result
    
    def _generate_recommendations(self, validation: Dict[str, Any]) -> List[str]:
        """Generate optimization recommendations based on validation results."""
        recommendations = []
        
        # Workload recommendations
        workload_violations = validation['constraint_violations']['workload']
        if workload_violations['count'] > 0:
            recommendations.append(f"Consider redistributing workload for {workload_violations['count']} coach(es) exceeding limits")
        
        # Time conflict recommendations
        time_conflicts = validation['constraint_violations']['time_conflicts']
        if time_conflicts['count'] > 0:
            recommendations.append(f"Resolve {time_conflicts['count']} time conflict(s) in coach schedules")
        
        # Popular slot usage
        popular_usage = validation['constraint_violations']['popular_slots']
        if popular_usage['percentage'] < 50:
            recommendations.append("Consider scheduling more classes in popular time slots to improve demand satisfaction")
        
        # Coach balance
        coach_balance = validation['quality_metrics']['coach_utilization_balance']
        if coach_balance['balance_score'] > 0.5:
            recommendations.append("Coach workload distribution is uneven - consider rebalancing assignments")
        
        return recommendations


class ConfigurationManager:
    """Manage enhanced algorithm configurations."""
    
    @staticmethod
    def get_default_config() -> Dict[str, Any]:
        """Get default configuration for enhanced algorithm."""
        return {
            'workload_limits': {
                'Full Time': {'weekly': 25, 'weekend_daily': 5, 'weekday_daily': 3},
                'Part Time': {'weekly': 15, 'weekend_daily': 5, 'weekday_daily': 3},
                'Manager': {'weekly': 3, 'weekend_daily': 2, 'weekday_daily': 2}
            },
            'algorithm': {
                'iterations': 60,
                'popular_timeslot_boost': 1.5,
                'level_merge_threshold': 0.7,
                'consecutive_limit': 3
            },
            'scheduling_preferences': {
                'prioritize_popular_slots': True,
                'enable_level_merging': True,
                'strict_constraint_enforcement': True,
                'optimize_for_coverage': True
            },
            'operating_hours': {
                'weekday': {'start': '15:30', 'end': '21:00'},
                'weekend': {'start': '09:00', 'end': '18:00'}
            }
        }
    
    @staticmethod
    def get_conservative_config() -> Dict[str, Any]:
        """Get conservative configuration with stricter limits."""
        config = ConfigurationManager.get_default_config()
        config['workload_limits'] = {
            'Full Time': {'weekly': 20, 'weekend_daily': 4, 'weekday_daily': 2},
            'Part Time': {'weekly': 12, 'weekend_daily': 3, 'weekday_daily': 2},
            'Manager': {'weekly': 2, 'weekend_daily': 1, 'weekday_daily': 1}
        }
        config['algorithm']['iterations'] = 80
        return config
    
    @staticmethod
    def get_aggressive_config() -> Dict[str, Any]:
        """Get aggressive configuration for maximum coverage."""
        config = ConfigurationManager.get_default_config()
        config['workload_limits'] = {
            'Full Time': {'weekly': 30, 'weekend_daily': 6, 'weekday_daily': 4},
            'Part Time': {'weekly': 20, 'weekend_daily': 6, 'weekday_daily': 3},
            'Manager': {'weekly': 5, 'weekend_daily': 3, 'weekday_daily': 2}
        }
        config['algorithm']['iterations'] = 40
        config['scheduling_preferences']['optimize_for_coverage'] = True
        return config
    
    @staticmethod
    def validate_config(config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate configuration parameters."""
        validation = {'valid': True, 'errors': [], 'warnings': []}
        
        # Check workload limits
        if 'workload_limits' in config:
            for position, limits in config['workload_limits'].items():
                if limits.get('weekly', 0) <= 0:
                    validation['errors'].append(f"Invalid weekly limit for {position}")
                    validation['valid'] = False
                
                if limits.get('weekend_daily', 0) > limits.get('weekly', 0):
                    validation['warnings'].append(f"Weekend daily limit exceeds weekly for {position}")
        
        # Check algorithm parameters
        if 'algorithm' in config:
            iterations = config['algorithm'].get('iterations', 0)
            if iterations < 10 or iterations > 200:
                validation['warnings'].append("Iterations outside recommended range (10-200)")
        
        return validation