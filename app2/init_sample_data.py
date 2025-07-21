"""
Initialize database with sample data for testing
"""

from application import create_app, db
from application.models import Branch, Level

def init_sample_data():
    app = create_app()
    
    with app.app_context():
        # Create sample branches
        branches = [
            {'name': 'Bukit Batok', 'abbrv': 'BB', 'max_classes': 4},
            {'name': 'Choa Chu Kang', 'abbrv': 'CCK', 'max_classes': 4},
            {'name': 'Clementi', 'abbrv': 'CH', 'max_classes': 5},
            {'name': 'Hougang', 'abbrv': 'HG', 'max_classes': 4},
            {'name': 'Kallang', 'abbrv': 'KT', 'max_classes': 4},
            {'name': 'Pasir Ris', 'abbrv': 'PR', 'max_classes': 6}
        ]
        
        for branch_data in branches:
            branch = Branch.query.filter_by(abbrv=branch_data['abbrv']).first()
            if not branch:
                branch = Branch(
                    name=branch_data['name'],
                    abbrv=branch_data['abbrv'],
                    max_classes=branch_data['max_classes']
                )
                db.session.add(branch)
        
        # Create sample levels
        levels = [
            {'name': 'Tots', 'max_students': 7, 'duration': 2},      # 60 min = 2 slots
            {'name': 'Jolly', 'max_students': 8, 'duration': 2},
            {'name': 'Bubbly', 'max_students': 8, 'duration': 2},
            {'name': 'Lively', 'max_students': 8, 'duration': 2},
            {'name': 'Flexi', 'max_students': 8, 'duration': 2},
            {'name': 'L1', 'max_students': 8, 'duration': 3},        # 90 min = 3 slots
            {'name': 'L2', 'max_students': 9, 'duration': 3},
            {'name': 'L3', 'max_students': 10, 'duration': 3},
            {'name': 'L4', 'max_students': 10, 'duration': 3},
            {'name': 'Advance', 'max_students': 10, 'duration': 3},
            {'name': 'Free', 'max_students': 10, 'duration': 3}
        ]
        
        for level_data in levels:
            level = Level.query.filter_by(name=level_data['name']).first()
            if not level:
                level = Level(
                    name=level_data['name'],
                    max_students=level_data['max_students'],
                    duration=level_data['duration']
                )
                db.session.add(level)
        
        db.session.commit()
        print("Sample data initialized successfully!")

if __name__ == '__main__':
    init_sample_data()