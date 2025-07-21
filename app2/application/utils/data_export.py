"""
Data export utilities to convert database models to CSV format
required by the timetabling algorithm.
"""
import pandas as pd
import os
from typing import Dict, List
from application.models import Coach, Branch, Level, CoachBranch, CoachOffday, CoachPreference
from application import db


class DataExporter:
    """Export database models to CSV format for timetabling algorithm."""
    
    def __init__(self, export_dir='/tmp/timetabling_data'):
        """Initialize with export directory."""
        self.export_dir = export_dir
        self.ensure_export_dir()
    
    def ensure_export_dir(self):
        """Create export directory if it doesn't exist."""
        os.makedirs(self.export_dir, exist_ok=True)
    
    def export_coaches_data(self) -> str:
        """Export coaches data to CSV format expected by algorithm."""
        coaches = db.session.query(Coach).all()
        
        # Prepare data structure matching coaches_df.csv format
        coach_data = []
        
        for coach in coaches:
            # Get assigned branches
            assigned_branches = [cb.branch.abbrv for cb in coach.assigned_branches]
            primary_branch = assigned_branches[0] if assigned_branches else ''
            
            # Get level preferences - map to boolean columns
            preferred_levels = {cp.level.name for cp in coach.preferred_levels}
            
            coach_row = {
                'coach_id': coach.id,
                'coach_name': coach.name,
                'residential_area': coach.residential_area,
                'assigned_branch': primary_branch,
                'position': coach.position,
                'status': coach.status,
                # Level preferences as boolean columns
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
            }
            coach_data.append(coach_row)
        
        # Create DataFrame and export
        df = pd.DataFrame(coach_data)
        filepath = os.path.join(self.export_dir, 'coaches_df.csv')
        df.to_csv(filepath, index=False)
        return filepath
    
    def export_availability_data(self) -> str:
        """Export coach availability data to CSV format."""
        # Get all coaches and their off days
        coaches = db.session.query(Coach).all()
        
        availability_data = []
        days_mapping = {0: 'MON', 1: 'TUE', 2: 'WED', 3: 'THU', 4: 'FRI', 5: 'SAT', 6: 'SUN'}
        
        for coach in coaches:
            # Get off days for this coach
            off_days = {(od.day, od.am) for od in coach.offdays}
            
            # Generate availability records for each day and time period
            for day_num, day_name in days_mapping.items():
                for am_period in [True, False]:
                    period_name = 'AM' if am_period else 'PM'
                    
                    # Check if this coach is off during this period
                    is_available = (day_num, am_period) not in off_days
                    
                    availability_data.append({
                        'coach_name': coach.name,
                        'day': day_name,
                        'period': period_name,
                        'available': is_available
                    })
        
        # Create DataFrame and export
        df = pd.DataFrame(availability_data)
        filepath = os.path.join(self.export_dir, 'availability_df.csv')
        df.to_csv(filepath, index=False)
        return filepath
    
    def export_branch_config(self) -> str:
        """Export branch configuration data."""
        branches = db.session.query(Branch).all()
        
        branch_data = []
        for branch in branches:
            branch_data.append({
                'branch': branch.abbrv,
                'max_classes_per_slot': branch.max_classes
            })
        
        df = pd.DataFrame(branch_data)
        filepath = os.path.join(self.export_dir, 'branch_config.csv')
        df.to_csv(filepath, index=False)
        return filepath
    
    def export_enrollment_counts(self) -> str:
        """Export enrollment counts data. 
        
        Note: This creates sample data as the database doesn't have enrollment info.
        In a real system, this would query actual enrollment data.
        """
        branches = db.session.query(Branch).all()
        levels = db.session.query(Level).all()
        
        enrollment_data = []
        
        # Create sample enrollment data based on levels and branches
        sample_counts = {
            'Tots': 15, 'Jolly': 25, 'Bubbly': 40, 'Lively': 35, 'Flexi': 45,
            'L1': 60, 'L2': 50, 'L3': 30, 'L4': 20, 'Advance': 10, 'Free': 8
        }
        
        for branch in branches:
            for level in levels:
                level_name = level.name
                base_count = sample_counts.get(level_name, 20)
                
                # Add some variation per branch
                import random
                random.seed(hash(f"{branch.abbrv}_{level_name}"))  # Consistent random
                count = max(1, base_count + random.randint(-10, 10))
                
                enrollment_data.append({
                    'Branch': branch.abbrv,
                    'Level Category Base': level_name,
                    'Count': count
                })
        
        df = pd.DataFrame(enrollment_data)
        filepath = os.path.join(self.export_dir, 'enrollment_counts.csv')
        df.to_csv(filepath, index=False)
        return filepath
    
    def export_all_data(self) -> Dict[str, str]:
        """Export all required data files and return file paths."""
        return {
            'coaches': self.export_coaches_data(),
            'availability': self.export_availability_data(), 
            'branch_config': self.export_branch_config(),
            'enrollment': self.export_enrollment_counts()
        }