from application import create_app, db
from application.models import (
    User, Branch, Level, Coach, CoachBranch, CoachOffday, CoachPreference,
    Availability, BranchConfig, Enrollment, PopularTimeslot
)
import pandas as pd

abbrv = {
    'Bukit Batok': 'BB',
    'Choa Chu Kang': 'CCK',
    'Changi': 'CH',
    'Hougang': 'HG',
    'Katong': 'KT',
    'Pasir Ris': 'PR',
}

max_classes = {
    'Bukit Batok': 4,
    'Choa Chu Kang': 4,
    'Changi': 5,
    'Hougang': 4,
    'Katong': 4,
    'Pasir Ris': 6,
}

max_students = {
    'BearyTots': 7,
    'Jolly': 8,
    'Bubbly': 8,
    'Lively': 8,
    'Flexi': 8,
    'L1': 8,
    'L2': 9,
    'L3': 10,
    'L4': 10,
    'Advance': 10,
    'Free': 10
}

duration = {
    'BearyTots': 1,
    'Jolly': 1,
    'Bubbly': 1,
    'Lively': 1,
    'Flexi': 1,
    'L1': 1.5,
    'L2': 1.5,
    'L3': 1.5,
    'L4': 1.5,
    'Advance': 1.5,
    'Free': 1.5
}

def load_csv_safely(file_path):
    """Safely load CSV file, return empty DataFrame if file doesn't exist"""
    try:
        return pd.read_csv(file_path)
    except FileNotFoundError:
        print(f"Warning: {file_path} not found. Skipping...")
        return pd.DataFrame()
    except Exception as e:
        print(f"Error loading {file_path}: {e}")
        return pd.DataFrame()

def main():
    app = create_app()
    with app.app_context():
        print("Dropping all existing tables...")
        db.drop_all()
        
        print("Creating all tables...")
        db.create_all()
        
        print("Initializing base data...")
        
        # Initialize Branches
        print("Creating branches...")
        for branch_name in abbrv.keys():
            branch = Branch(
                name=branch_name,
                abbrv=abbrv[branch_name],
                max_classes=max_classes[branch_name],
            )
            db.session.add(branch)
        
        # Initialize Levels
        print("Creating levels...")
        for level_name in max_students.keys():
            level = Level(
                name=level_name,
                max_students=max_students[level_name],
                duration=int(duration[level_name] * 2)  # Number of hours * 2 = Number of 30 minute slots
            )
            db.session.add(level)
        
        # Commit base data first
        db.session.commit()
        print("Base data committed successfully.")
        
        # Load coaches data if available
        coaches_df = load_csv_safely('../Updated Datasets/coaches_df.csv')
        if not coaches_df.empty:
            print(f"Loading {len(coaches_df)} coaches...")
            for _, row in coaches_df.iterrows():
                coach = Coach(
                    id=row['coach_id'],
                    name=row['coach_name'],
                    residential_area=row['residential_area'],
                    position=row['position'] if not pd.isna(row['position']) else 'Part time',
                    status=row['status']
                )
                db.session.add(coach)
                
                # Add coach-branch relationships
                for branch_abbrv in row['assigned_branch'].split(','):
                    branch = Branch.query.filter_by(abbrv=branch_abbrv.strip()).first()
                    if branch:
                        coach_branch = CoachBranch(
                            coach_id=coach.id,
                            branch_id=branch.id
                        )
                        db.session.add(coach_branch)
                
                # Add coach preferences
                for level_name, prefers_teaching in row.iloc[6:].items():
                    if not prefers_teaching:
                        continue
                    
                    level = Level.query.filter_by(name=level_name.replace('evel_', '')).first()
                    if level:
                        coach_preference = CoachPreference(
                            coach_id=coach.id,
                            level_id=level.id
                        )
                        db.session.add(coach_preference)
            
            db.session.commit()
            print("Coaches data loaded successfully.")
        
        # Load availability data if available
        availability_df = load_csv_safely('../Updated Datasets/availability_df.csv')
        if not availability_df.empty:
            print(f"Loading {len(availability_df)} availability records...")
            # Filter for unavailable records only
            availability_df = availability_df[availability_df['available'] == False]
            
            for _, row in availability_df.iterrows():
                availability = Availability(
                    availability_id=row['availability_id'],
                    coach_id=row['coach_id'],
                    day=row['day'],
                    period=row['period'],
                    available=row['available'],
                    restriction_reason=row.get('restriction_reason') if not pd.isna(row.get('restriction_reason')) else None
                )
                db.session.add(availability)
            
            db.session.commit()
            print("Availability data loaded successfully.")
        
        # Load branch config data if available
        branch_config_df = load_csv_safely('../Updated Datasets/branch_config_df.csv')
        if not branch_config_df.empty:
            print(f"Loading {len(branch_config_df)} branch configurations...")
            for _, row in branch_config_df.iterrows():
                config = BranchConfig(
                    branch=row['branch'],
                    max_classes_per_slot=row['max_classes_per_slot']
                )
                db.session.add(config)
            
            db.session.commit()
            print("Branch config data loaded successfully.")
        
        # Load enrollment data if available
        enrollment_df = load_csv_safely('../Updated Datasets/enrollment_df.csv')
        if not enrollment_df.empty:
            print(f"Loading {len(enrollment_df)} enrollment records...")
            for _, row in enrollment_df.iterrows():
                enrollment = Enrollment(
                    branch=row['Branch'],
                    level_category_base=row['Level Category Base'],
                    count=row['Count']
                )
                db.session.add(enrollment)
            
            db.session.commit()
            print("Enrollment data loaded successfully.")
        
        # Load popular timeslots data if available
        popular_timeslots_df = load_csv_safely('../Updated Datasets/popular_timeslots_df.csv')
        if not popular_timeslots_df.empty:
            print(f"Loading {len(popular_timeslots_df)} popular timeslot records...")
            for _, row in popular_timeslots_df.iterrows():
                timeslot = PopularTimeslot(
                    time_slot=row['time_slot'],
                    day=row['day'],
                    level=row['level']
                )
                db.session.add(timeslot)
            
            db.session.commit()
            print("Popular timeslots data loaded successfully.")
        
        # Create a default admin user (optional)
        print("Creating default admin user...")
        admin_user = User(
            username='admin',
            password='hashed_password_here',  # You should hash this properly
            permissions=1  # Full permissions
        )
        db.session.add(admin_user)
        
        db.session.commit()
        print("Database initialization completed successfully!")
        
        # Print summary
        print("\n" + "="*50)
        print("DATABASE INITIALIZATION SUMMARY")
        print("="*50)
        print(f"Branches: {Branch.query.count()}")
        print(f"Levels: {Level.query.count()}")
        print(f"Coaches: {Coach.query.count()}")
        print(f"Coach-Branch relationships: {CoachBranch.query.count()}")
        print(f"Coach preferences: {CoachPreference.query.count()}")
        print(f"Availability records: {Availability.query.count()}")
        print(f"Branch configurations: {BranchConfig.query.count()}")
        print(f"Enrollment records: {Enrollment.query.count()}")
        print(f"Popular timeslots: {PopularTimeslot.query.count()}")
        print(f"Users: {User.query.count()}")
        print("="*50)

if __name__ == '__main__':
    main()