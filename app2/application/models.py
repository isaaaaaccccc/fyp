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
# ===================== New Upload Models =====================
# =============================================================

class Availability(db.Model):
    __tablename__ = 'availability'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)  # Auto-generated primary key
    original_availability_id = db.Column(db.Integer, nullable=True)   # Store original CSV ID if needed
    coach_id = db.Column(db.Integer, db.ForeignKey('coach.id'), nullable=False)
    day = db.Column(db.String(10), nullable=False)  # MON, TUE, etc.
    period = db.Column(db.String(10), nullable=False)  # am, pm
    available = db.Column(db.Boolean, nullable=False)
    restriction_reason = db.Column(db.String(100), nullable=True)
    
    # Add unique constraint on coach_id, day, period to prevent duplicates
    __table_args__ = (db.UniqueConstraint('coach_id', 'day', 'period', name='_coach_day_period_uc'),)
    
    coach = db.relationship('Coach', backref='availability_records')

class BranchConfig(db.Model):
    __tablename__ = 'branch_config'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    branch = db.Column(db.String(10), nullable=False, unique=True)
    max_classes_per_slot = db.Column(db.Integer, nullable=False)

class Enrollment(db.Model):
    __tablename__ = 'enrollment'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    branch = db.Column(db.String(10), nullable=False)
    level_category_base = db.Column(db.String(50), nullable=False)
    count = db.Column(db.Integer, nullable=False)

class PopularTimeslot(db.Model):
    __tablename__ = 'popular_timeslot'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    time_slot = db.Column(db.String(20), nullable=False)
    day = db.Column(db.String(10), nullable=False)
    level = db.Column(db.String(20), nullable=False)

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