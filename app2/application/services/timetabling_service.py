"""
Timetabling service that coordinates the entire scheduling process.
This service bridges the database models and the scheduling algorithm.
"""
import os
import tempfile
import shutil
from typing import Dict, Any, Optional
from application.utils.data_export import DataExporter
from application.services.data_processor import OptimizedLPDataStorage, MaxCoverageScheduler


class TimetablingService:
    """
    Main service for generating timetables.
    Coordinates data export, processing, and scheduling.
    """
    
    def __init__(self):
        """Initialize the timetabling service."""
        self.data_exporter = DataExporter()
        self.temp_dir = None
        
    def generate_timetable(self) -> Dict[str, Any]:
        """
        Generate a complete timetable using the database data.
        
        Returns:
            Dict containing the generated schedule in the expected format
            
        Raises:
            Exception: If timetable generation fails
        """
        try:
            # Create temporary directory for this generation
            self.temp_dir = tempfile.mkdtemp(prefix='timetabling_')
            self.data_exporter = DataExporter(self.temp_dir)
            
            print(f"Starting timetable generation in {self.temp_dir}")
            
            # Step 1: Export database data to CSV files
            print("Step 1: Exporting database data...")
            exported_files = self.data_exporter.export_all_data()
            print(f"Exported files: {list(exported_files.keys())}")
            
            # Step 2: Load and process data
            print("Step 2: Loading and processing data...")
            data_storage = OptimizedLPDataStorage(self.temp_dir)
            optimized_data = data_storage.get_data_dict()
            
            # Step 3: Generate schedule
            print("Step 3: Generating schedule...")
            scheduler = MaxCoverageScheduler(optimized_data)
            schedule = scheduler.generate_schedule()
            
            print("Timetable generation completed successfully!")
            return schedule
            
        except Exception as e:
            print(f"Error generating timetable: {str(e)}")
            raise Exception(f"Timetable generation failed: {str(e)}")
            
        finally:
            # Clean up temporary directory
            if self.temp_dir and os.path.exists(self.temp_dir):
                try:
                    shutil.rmtree(self.temp_dir)
                except Exception as e:
                    print(f"Warning: Could not clean up temp directory {self.temp_dir}: {e}")
    
    def validate_schedule(self, schedule: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate the generated schedule against business rules.
        
        Args:
            schedule: The generated schedule
            
        Returns:
            Dictionary with validation results
        """
        validation_results = {
            'valid': True,
            'warnings': [],
            'errors': [],
            'statistics': {}
        }
        
        try:
            total_classes = 0
            total_coaches_used = set()
            branch_stats = {}
            
            for branch_name, branch_data in schedule.items():
                branch_classes = 0
                branch_coaches = set()
                
                for day_name, day_schedule in branch_data.get('schedule', {}).items():
                    for coach_name, coach_classes in day_schedule.items():
                        branch_coaches.add(coach_name)
                        total_coaches_used.add(coach_name)
                        
                        for class_info in coach_classes:
                            branch_classes += 1
                            total_classes += 1
                
                branch_stats[branch_name] = {
                    'classes': branch_classes,
                    'coaches': len(branch_coaches)
                }
            
            validation_results['statistics'] = {
                'total_classes': total_classes,
                'total_coaches_used': len(total_coaches_used),
                'branches_covered': len(schedule),
                'branch_statistics': branch_stats
            }
            
            # Basic validation checks
            if total_classes == 0:
                validation_results['valid'] = False
                validation_results['errors'].append("No classes scheduled")
            
            if len(total_coaches_used) == 0:
                validation_results['valid'] = False
                validation_results['errors'].append("No coaches assigned")
                
        except Exception as e:
            validation_results['valid'] = False
            validation_results['errors'].append(f"Validation error: {str(e)}")
        
        return validation_results
    
    def get_schedule_summary(self, schedule: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a summary of the schedule for reporting.
        
        Args:
            schedule: The generated schedule
            
        Returns:
            Dictionary with schedule summary
        """
        summary = {
            'generation_time': 'N/A',  # Would be set by caller
            'branches': [],
            'total_classes': 0,
            'total_coaches': 0,
            'coverage_analysis': {}
        }
        
        try:
            all_coaches = set()
            
            for branch_name, branch_data in schedule.items():
                branch_info = {
                    'name': branch_name,
                    'coaches': branch_data.get('coaches', []),
                    'total_classes': 0,
                    'days_covered': []
                }
                
                for day_name, day_schedule in branch_data.get('schedule', {}).items():
                    if day_schedule:  # If there are classes this day
                        branch_info['days_covered'].append(day_name)
                        
                    for coach_name, coach_classes in day_schedule.items():
                        all_coaches.add(coach_name)
                        branch_info['total_classes'] += len(coach_classes)
                
                summary['branches'].append(branch_info)
                summary['total_classes'] += branch_info['total_classes']
            
            summary['total_coaches'] = len(all_coaches)
            
            # Coverage analysis
            days_with_classes = set()
            for branch_data in schedule.values():
                for day_name in branch_data.get('schedule', {}).keys():
                    if branch_data['schedule'][day_name]:
                        days_with_classes.add(day_name)
            
            summary['coverage_analysis'] = {
                'days_with_classes': list(days_with_classes),
                'branches_with_classes': len([b for b in summary['branches'] if b['total_classes'] > 0])
            }
            
        except Exception as e:
            summary['error'] = f"Summary generation failed: {str(e)}"
        
        return summary