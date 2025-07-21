from application import create_app, db
from application.models import User, Branch, Level, Coach, CoachBranch, CoachOffday, CoachPreference
import pandas as pd

abbrv = {
    'Bukit Batok':  'BB',
    'Choa Chu Kang':  'CCK',
    'Changi':  'CH',
    'Hougang':  'HG',
    'Katong':  'KT',
    'Pasir Ris':  'PR',
}

max_classes = {
    'Bukit Batok':  4,
    'Choa Chu Kang':  4,
    'Changi':  5,
    'Hougang':  4,
    'Katong':  4,
    'Pasir Ris':  6,
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

coaches_df = pd.read_csv('../Updated Datasets/coaches_df.csv')
availability_df = pd.read_csv('../Updated Datasets/availability_df.csv')
availability_df = availability_df[availability_df['available'] == False]

def main():
    app = create_app()
    with app.app_context():
        db.drop_all()
        db.create_all()

        for branch_name in abbrv.keys():
            branch = Branch(
                name=branch_name,
                abbrv=abbrv[branch_name],
                max_classes=max_classes[branch_name],
            )
            db.session.add(branch)


        for level_name in max_students.keys():
            level = Level(
                name=level_name,
                max_students=max_students[level_name],
                duration=int(duration[level_name] * 2)  # Number of hours * 2 = Number of 30 minute slots
            )
            db.session.add(level)
    
        for _, row in coaches_df.iterrows():
            coach = Coach(
                id=row['coach_id'],
                name=row['coach_name'],
                residential_area=row['residential_area'],
                position=row['position'] if not pd.isna(row['position']) else 'Part time',  # All part timers do not have a position
                status=row['status']
            )

            for branch_abbrv in row['assigned_branch'].split(','):
                branch = Branch.query.filter_by(abbrv=branch_abbrv.strip()).first()
                coach_branch = CoachBranch(
                    coach_id=coach.id,
                    branch_id=branch.id
                )
                db.session.add(coach_branch)
            
            for level_name, prefers_teaching in row.iloc[6:].items():
                if not prefers_teaching:
                    continue

                level = Level.query.filter_by(name=level_name.replace('evel_', '')).first()
                coach_preference = CoachPreference(
                    coach_id=coach.id,
                    level_id=level.id
                )
                db.session.add(coach_preference)            

            db.session.add(coach)

        for _, row in availability_df.iterrows():
            coach_offday = CoachOffday(
                coach_id=row['coach_id'],
                day=row['day'], 
                am=(row['period'] == 'am'),
                reason=row['restriction_reason']
            )
            db.session.add(coach_offday)

        db.session.commit()
            

if __name__ == '__main__':
    main()