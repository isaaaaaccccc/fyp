"""
Simple database initialization script using the available cleaned_data
"""
from application import create_app, db
from application.models import User, Branch, Level, Coach, CoachBranch, CoachOffday, CoachPreference
import pandas as pd
import os

def init_database():
    """Initialize database with sample data."""
    app = create_app()
    with app.app_context():
        # Drop and recreate all tables
        db.drop_all()
        db.create_all()
        
        print("Initializing database...")
        
        # Create branches
        branches_data = [
            ('Bukit Batok', 'BB', 4),
            ('Choa Chu Kang', 'CCK', 4),
            ('Changi', 'CH', 5),
            ('Hougang', 'HG', 4),
            ('Katong', 'KT', 4),
            ('Pasir Ris', 'PR', 6),
        ]
        
        for name, abbrv, max_classes in branches_data:
            branch = Branch(name=name, abbrv=abbrv, max_classes=max_classes)
            db.session.add(branch)
        
        # Create levels
        levels_data = [
            ('Tots', 7, 2),  # 1 hour = 2 * 30min slots
            ('Jolly', 8, 2),
            ('Bubbly', 8, 2),
            ('Lively', 8, 2),
            ('Flexi', 8, 2),
            ('L1', 8, 3),  # 1.5 hours = 3 * 30min slots
            ('L2', 9, 3),
            ('L3', 10, 3),
            ('L4', 10, 3),
            ('Advance', 10, 3),
            ('Free', 10, 3)
        ]
        
        for name, max_students, duration in levels_data:
            level = Level(name=name, max_students=max_students, duration=duration)
            db.session.add(level)
        
        db.session.commit()
        
        # Load coaches data if available
        coaches_file = '../cleaned_data/coaches_df.csv'
        if os.path.exists(coaches_file):
            coaches_df = pd.read_csv(coaches_file)
            
            for _, row in coaches_df.iterrows():
                coach = Coach(
                    id=row['coach_id'],
                    name=row['coach_name'],
                    residential_area=row['residential_area'],
                    position=row['position'] if pd.notna(row['position']) else 'Part time',
                    status=row['status']
                )
                db.session.add(coach)
                db.session.flush()  # Get the ID
                
                # Add branch assignment
                branch = Branch.query.filter_by(abbrv=row['assigned_branch']).first()
                if branch:
                    coach_branch = CoachBranch(coach_id=coach.id, branch_id=branch.id)
                    db.session.add(coach_branch)
                
                # Add level preferences
                level_columns = ['BearyTots', 'Jolly', 'Bubbly', 'Lively', 'Flexi', 
                               'Level_1', 'Level_2', 'Level_3', 'Level_4', 'Advance', 'Free']
                
                for level_col in level_columns:
                    if level_col in row and row[level_col]:
                        # Map column name to level name
                        level_name = level_col
                        if level_col == 'BearyTots':
                            level_name = 'Tots'
                        elif level_col.startswith('Level_'):
                            level_name = f"L{level_col.split('_')[1]}"
                        
                        level = Level.query.filter_by(name=level_name).first()
                        if level:
                            coach_pref = CoachPreference(coach_id=coach.id, level_id=level.id)
                            db.session.add(coach_pref)
            
            print(f"Added {len(coaches_df)} coaches")
        else:
            # Add a few sample coaches if no data file
            sample_coaches = [
                {'name': 'Chris', 'area': 'JB', 'branch': 'CCK', 'position': 'Branch Manager', 'status': 'Full time'},
                {'name': 'Yenzen', 'area': 'Tampines', 'branch': 'CCK', 'position': 'Senior Coach', 'status': 'Full time'},
                {'name': 'Vivian', 'area': 'Bedok', 'branch': 'CCK', 'position': 'Junior Coach', 'status': 'Full time'},
            ]
            
            for i, coach_data in enumerate(sample_coaches, 1):
                coach = Coach(
                    id=i,
                    name=coach_data['name'],
                    residential_area=coach_data['area'],
                    position=coach_data['position'],
                    status=coach_data['status']
                )
                db.session.add(coach)
                db.session.flush()
                
                # Add branch assignment
                branch = Branch.query.filter_by(abbrv=coach_data['branch']).first()
                if branch:
                    coach_branch = CoachBranch(coach_id=coach.id, branch_id=branch.id)
                    db.session.add(coach_branch)
                
                # Add some level preferences
                levels = Level.query.limit(5).all()
                for level in levels:
                    coach_pref = CoachPreference(coach_id=coach.id, level_id=level.id)
                    db.session.add(coach_pref)
        
        # Load availability data if available
        availability_file = '../cleaned_data/availability_df.csv'
        if os.path.exists(availability_file):
            try:
                availability_df = pd.read_csv(availability_file)
                availability_df = availability_df[availability_df['available'] == False]
                
                for _, row in availability_df.iterrows():
                    coach = Coach.query.filter_by(name=row['coach_name']).first()
                    if coach:
                        day_mapping = {'MON': 0, 'TUE': 1, 'WED': 2, 'THU': 3, 'FRI': 4, 'SAT': 5, 'SUN': 6}
                        day_num = day_mapping.get(row['day'], 0)
                        
                        coach_offday = CoachOffday(
                            coach_id=coach.id,
                            day=day_num,
                            am=(row['period'] == 'AM'),
                            reason='Unavailable'
                        )
                        db.session.add(coach_offday)
                
                print("Added availability restrictions")
            except Exception as e:
                print(f"Could not load availability data: {e}")
        
        db.session.commit()
        print("Database initialization completed!")

if __name__ == '__main__':
    init_database()