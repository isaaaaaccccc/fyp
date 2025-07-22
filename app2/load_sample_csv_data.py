"""
Load sample CSV data into database for testing
"""

from application import create_app, db
from application.models import (
    PopularTimeslots, EnrollmentCounts, BranchConfig, CoachAvailability
)
import pandas as pd

def load_sample_csv_data():
    app = create_app()
    
    with app.app_context():
        try:
            # Load enrollment data
            enrollment_df = pd.read_csv('sample_data/enrollment.csv')
            
            # Clear existing enrollment data
            EnrollmentCounts.query.delete()
            
            for _, row in enrollment_df.iterrows():
                enrollment = EnrollmentCounts(
                    branch=row['Branch'],
                    level_category_base=row['Level Category Base'],
                    count=row['Count']
                )
                db.session.add(enrollment)
            
            print(f"Loaded {len(enrollment_df)} enrollment records")
            
            # Load popular timeslots
            timeslots_df = pd.read_csv('sample_data/popular_timeslots.csv')
            
            # Clear existing timeslots data
            PopularTimeslots.query.delete()
            
            for _, row in timeslots_df.iterrows():
                timeslot = PopularTimeslots(
                    time_slot=row['time_slot'],
                    day=row['day'],
                    level=row['level']
                )
                db.session.add(timeslot)
            
            print(f"Loaded {len(timeslots_df)} popular timeslot records")
            
            # Load branch config
            branch_config_df = pd.read_csv('sample_data/branch_config.csv')
            
            # Clear existing branch config data
            BranchConfig.query.delete()
            
            for _, row in branch_config_df.iterrows():
                config = BranchConfig(
                    branch=row['branch'],
                    max_classes_per_slot=row['max_classes_per_slot']
                )
                db.session.add(config)
            
            print(f"Loaded {len(branch_config_df)} branch config records")
            
            # Load coach availability (this data should already be loaded from init_db.py)
            availability_df = pd.read_csv('sample_data/availability.csv')
            
            # Clear existing availability data
            CoachAvailability.query.delete()
            
            for _, row in availability_df.iterrows():
                availability = CoachAvailability(
                    coach_id=row['coach_id'],
                    day=row['day'],
                    period=row['period'],
                    available=row['available'],
                    restriction_reason=row.get('restriction_reason', '')
                )
                db.session.add(availability)
            
            print(f"Loaded {len(availability_df)} availability records")
            
            db.session.commit()
            print("All sample CSV data loaded successfully!")
            
        except Exception as e:
            db.session.rollback()
            print(f"Error loading sample data: {e}")
            raise

if __name__ == '__main__':
    load_sample_csv_data()