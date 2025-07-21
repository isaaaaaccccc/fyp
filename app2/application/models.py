from application import db
from flask_login import UserMixin
from datetime import datetime

# =============================================================
# =========================== Users ===========================
# =============================================================

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(32), nullable=False, unique=True)
    password = db.Column(db.String(128), nullable=False)
    permissions = db.Column(db.Integer, nullable=False)  # Whether a person has read or edit access 
    time_joined = db.Column(db.DateTime, nullable=False, default=datetime.now)

# =============================================================
# ==================== Relational Entities ====================
# =============================================================

class Branch(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(32), nullable=False, unique=True)
    abbrv = db.Column(db.String(4), nullable=False, unique=True)  # Abbreviated form
    max_classes = db.Column(db.Integer, nullable=False)

    assigned_coaches = db.relationship('CoachBranch', back_populates='branch')

class Level(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(32), nullable=False, unique=True)
    max_students = db.Column(db.Integer, nullable=False)
    duration = db.Column(db.Integer, nullable=False)  # Duration will be in terms of number of 30min timeslots

    preferred_by_coaches = db.relationship('CoachPreference', back_populates='level')

class Coach(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(32), nullable=False)
    residential_area = db.Column(db.String(32), nullable=False)
    position = db.Column(db.String(32), nullable=False)
    status = db.Column(db.String(32), nullable=False)

    assigned_branches = db.relationship('CoachBranch', back_populates='coach')
    offdays = db.relationship('CoachOffday', back_populates='coach')
    preferred_levels = db.relationship('CoachPreference', back_populates='coach')

# =============================================================
# ===== Association tables for many-to-many relationships =====
# =============================================================

# Handles which branch a coach gets assigned to
class CoachBranch(db.Model):
    __tablename__ = 'coach_branch'

    coach_id = db.Column(db.Integer, db.ForeignKey('coach.id'), primary_key=True)
    branch_id = db.Column(db.Integer, db.ForeignKey('branch.id'), primary_key=True)

    coach = db.relationship('Coach', back_populates='assigned_branches')
    branch = db.relationship('Branch', back_populates='assigned_coaches')

# Handles which days/timeslots a coach can work on
class CoachOffday(db.Model):
    __tablename__ = 'coach_offday'

    coach_id = db.Column(db.Integer, db.ForeignKey('coach.id'), primary_key=True)
    day = db.Column(db.Integer, primary_key=True)  # 0 = Monday, 6 = Sunday
    am = db.Column(db.Boolean, primary_key=True)
    reason = db.Column(db.String(64), nullable=True)  

    coach = db.relationship('Coach', back_populates='offdays')

# Handles which class levels a coach prefers to teach, (eg. L1, L2) 
class CoachPreference(db.Model):
    __tablename__ = 'coach_preference'

    coach_id = db.Column(db.Integer, db.ForeignKey('coach.id'), primary_key=True)
    level_id = db.Column(db.Integer, db.ForeignKey('level.id'), primary_key=True)

    coach = db.relationship('Coach', back_populates='preferred_levels')
    level = db.relationship('Level', back_populates='preferred_by_coaches')

# =============================================================
# ==================== Generated Timetable ====================
# =============================================================

# class Timetable(db.Model):
#     timetable_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
#     date_created = db.Column(db.DateTime, nullable=False, default=datetime.now)

# =============================================================
# ==================== Helper Methods ====================
# =============================================================

    def to_dict(self):
        """Convert coach to dictionary for API responses."""
        return {
            'id': self.id,
            'name': self.name,
            'residential_area': self.residential_area,
            'position': self.position,
            'status': self.status,
            'assigned_branches': [cb.branch.abbrv for cb in self.assigned_branches],
            'offdays': [{
                'day': cd.day,
                'am': cd.am,
                'reason': cd.reason
            } for cd in self.offdays],
            'preferred_levels': [cl.level.name for cl in self.preferred_levels]
        }

# Add helper methods to Coach class
Coach.to_dict = lambda self: {
    'id': self.id,
    'name': self.name,
    'residential_area': self.residential_area,
    'position': self.position,
    'status': self.status,
    'assigned_branches': [cb.branch.abbrv for cb in self.assigned_branches],
    'offdays': [{
        'day': cd.day,
        'am': cd.am,
        'reason': cd.reason
    } for cd in self.offdays],
    'preferred_levels': [cl.level.name for cl in self.preferred_levels]
}

# Add helper methods to Branch class  
Branch.to_dict = lambda self: {
    'id': self.id,
    'name': self.name,
    'abbrv': self.abbrv,
    'max_classes': self.max_classes
}

# Add helper methods to Level class
Level.to_dict = lambda self: {
    'id': self.id,
    'name': self.name,
    'max_students': self.max_students,
    'duration': self.duration
}