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
# ======================== CSV Data Models =====================
# =============================================================

class PopularTimeslots(db.Model):
    __tablename__ = 'popular_timeslots'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    time_slot = db.Column(db.String(32), nullable=False)  # e.g., "08:30-12:30"
    day = db.Column(db.String(10), nullable=False)        # e.g., "WED"
    level = db.Column(db.String(32), nullable=False)      # e.g., "Tots"

class EnrollmentCounts(db.Model):
    __tablename__ = 'enrollment_counts'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    branch = db.Column(db.String(10), nullable=False)           # e.g., "BB"
    level_category_base = db.Column(db.String(32), nullable=False)  # e.g., "Advance"
    count = db.Column(db.Integer, nullable=False)

class BranchConfig(db.Model):
    __tablename__ = 'branch_config'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    branch = db.Column(db.String(10), nullable=False, unique=True)  # e.g., "BB"
    max_classes_per_slot = db.Column(db.Integer, nullable=False)

class CoachAvailability(db.Model):
    __tablename__ = 'coach_availability'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    coach_id = db.Column(db.Integer, nullable=False)
    day = db.Column(db.String(10), nullable=False)        # e.g., "MON"
    period = db.Column(db.String(10), nullable=False)     # "am" or "pm"
    available = db.Column(db.Boolean, nullable=False)
    restriction_reason = db.Column(db.String(64), nullable=True)

# =============================================================
# ==================== Generated Timetable ====================
# =============================================================

class Timetable(db.Model):
    """Store generated timetables"""
    __tablename__ = 'timetables'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(128), nullable=False)
    description = db.Column(db.Text, nullable=True)
    date_created = db.Column(db.DateTime, nullable=False, default=datetime.now)
    date_updated = db.Column(db.DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)
    is_active = db.Column(db.Boolean, nullable=False, default=False)
    algorithm_version = db.Column(db.String(32), nullable=False, default='Enhanced_v1.0')
    
    # Statistics
    total_assignments = db.Column(db.Integer, nullable=True)
    coverage_percentage = db.Column(db.Float, nullable=True)
    popular_slot_coverage = db.Column(db.Float, nullable=True)
    constraint_violations = db.Column(db.Integer, nullable=True)
    
    # Relationships
    assignments = db.relationship('TimetableAssignment', back_populates='timetable', cascade='all, delete-orphan')

class TimetableAssignment(db.Model):
    """Individual class assignments within a timetable"""
    __tablename__ = 'timetable_assignments'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    timetable_id = db.Column(db.Integer, db.ForeignKey('timetables.id'), nullable=False)
    
    # Assignment details
    coach_id = db.Column(db.Integer, db.ForeignKey('coach.id'), nullable=False)
    branch = db.Column(db.String(10), nullable=False)
    level = db.Column(db.String(32), nullable=False)
    day = db.Column(db.String(10), nullable=False)  # MON, TUE, etc.
    start_time = db.Column(db.String(8), nullable=False)  # HH:MM format
    end_time = db.Column(db.String(8), nullable=False)  # HH:MM format
    duration = db.Column(db.Integer, nullable=False)  # Duration in minutes
    students_count = db.Column(db.Integer, nullable=False)
    is_popular = db.Column(db.Boolean, nullable=False, default=False)
    priority_score = db.Column(db.Float, nullable=True)
    
    # Relationships
    timetable = db.relationship('Timetable', back_populates='assignments')
    coach = db.relationship('Coach', backref='timetable_assignments')

class TimetableStatistics(db.Model):
    """Detailed statistics for timetables"""
    __tablename__ = 'timetable_statistics'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    timetable_id = db.Column(db.Integer, db.ForeignKey('timetables.id'), nullable=False)
    
    # Coach utilization (stored as JSON)
    coach_utilization = db.Column(db.Text, nullable=True)  # JSON string
    branch_distribution = db.Column(db.Text, nullable=True)  # JSON string
    level_distribution = db.Column(db.Text, nullable=True)  # JSON string
    constraint_violations_detail = db.Column(db.Text, nullable=True)  # JSON string
    
    # Relationships
    timetable = db.relationship('Timetable', backref='statistics', uselist=False)