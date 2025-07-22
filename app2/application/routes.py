from flask import Blueprint, render_template, request, flash, redirect, jsonify, get_flashed_messages, url_for
from werkzeug.utils import secure_filename
from application import db, bcrypt
from application.models import User, Coach, Level, Branch, CoachBranch, CoachOffday, CoachPreference, Availability, BranchConfig, Enrollment, PopularTimeslot
from flask_login import login_user, logout_user, login_required
from .forms import CoachFilter, CoachDetails, DataUploadForm
import pandas as pd
import os

pages_bp = Blueprint('pages', __name__)
api_bp = Blueprint('apis', __name__, url_prefix='/api')

@pages_bp.route('/')
def index():
    return render_template('index.html')

@pages_bp.route('/auth/')
def auth():
    return render_template('auth.html')

@pages_bp.route('/dashboard/')
def dashboard():
    return render_template('dashboard.html')

@pages_bp.route('/timetable/')
def timetable():
    return render_template('timetable.html')

@pages_bp.route('/database/coach/')
def coach_db():
    return render_template('coach_db.html', filter=CoachFilter(), details=CoachDetails())

@pages_bp.route('/data-upload/', methods=['GET', 'POST'])
def data_upload():
    form = DataUploadForm()
    
    if form.validate_on_submit():
        try:
            upload_results = []
            
            # Process Availability file
            if form.availability_file.data:
                result = process_availability_file(form.availability_file.data)
                upload_results.append(result)
            
            # Process Branch Config file
            if form.branch_config_file.data:
                result = process_branch_config_file(form.branch_config_file.data)
                upload_results.append(result)
            
            # Process Coaches file
            if form.coaches_file.data:
                result = process_coaches_file(form.coaches_file.data)
                upload_results.append(result)
            
            # Process Enrollment file
            if form.enrollment_file.data:
                result = process_enrollment_file(form.enrollment_file.data)
                upload_results.append(result)
            
            # Process Popular Timeslots file
            if form.popular_timeslots_file.data:
                result = process_popular_timeslots_file(form.popular_timeslots_file.data)
                upload_results.append(result)
            
            if upload_results:
                db.session.commit()
                flash(f'Successfully processed {len(upload_results)} file(s)!', 'success')
            else:
                flash('No files were uploaded.', 'warning')
                
        except Exception as e:
            db.session.rollback()
            flash(f'Error processing files: {str(e)}', 'error')
    
    return render_template('data_upload.html', form=form)

def process_availability_file(file):
    """Process availability CSV file"""
    df = pd.read_csv(file)
    
    # Use no_autoflush to prevent premature flushing
    with db.session.no_autoflush:
        # Clear existing availability data first
        db.session.query(Availability).delete()
        
        for _, row in df.iterrows():
            # Handle NaN values for restriction_reason
            restriction_reason = row.get('restriction_reason')
            if pd.isna(restriction_reason):
                restriction_reason = None
            
            # Check if this coach-day-period combination already exists
            existing = db.session.query(Availability).filter_by(
                coach_id=int(row['coach_id']),
                day=str(row['day']),
                period=str(row['period'])
            ).first()
            
            if existing:
                # Update existing record
                existing.available = bool(row['available'])
                existing.restriction_reason = restriction_reason
                existing.original_availability_id = int(row['availability_id'])
            else:
                # Create new record
                availability = Availability(
                    original_availability_id=int(row['availability_id']),
                    coach_id=int(row['coach_id']),
                    day=str(row['day']),
                    period=str(row['period']),
                    available=bool(row['available']),
                    restriction_reason=restriction_reason
                )
                db.session.add(availability)
    
    return f"Processed {len(df)} availability records"

def process_branch_config_file(file):
    """Process branch config CSV file"""
    df = pd.read_csv(file)
    
    with db.session.no_autoflush:
        # Clear existing branch config data
        db.session.query(BranchConfig).delete()
        
        for _, row in df.iterrows():
            config = BranchConfig(
                branch=str(row['branch']),
                max_classes_per_slot=int(row['max_classes_per_slot'])
            )
            db.session.add(config)
    
    return f"Processed {len(df)} branch configurations"

def process_coaches_file(file):
    """Process coaches CSV file"""
    df = pd.read_csv(file)
    
    processed_count = 0
    
    with db.session.no_autoflush:
        for _, row in df.iterrows():
            # Check if coach already exists
            existing_coach = Coach.query.filter_by(id=int(row['coach_id'])).first()
            
            if existing_coach:
                # Update existing coach
                existing_coach.name = str(row['coach_name'])
                existing_coach.residential_area = str(row['residential_area'])
                existing_coach.position = str(row['position']) if not pd.isna(row['position']) else 'Part time'
                existing_coach.status = str(row['status'])
            else:
                # Create new coach
                coach = Coach(
                    id=int(row['coach_id']),
                    name=str(row['coach_name']),
                    residential_area=str(row['residential_area']),
                    position=str(row['position']) if not pd.isna(row['position']) else 'Part time',
                    status=str(row['status'])
                )
                db.session.add(coach)
            
            processed_count += 1
    
    return f"Processed {processed_count} coach records"

def process_enrollment_file(file):
    """Process enrollment CSV file"""
    df = pd.read_csv(file)
    
    with db.session.no_autoflush:
        # Clear existing enrollment data
        db.session.query(Enrollment).delete()
        
        for _, row in df.iterrows():
            enrollment = Enrollment(
                branch=str(row['Branch']),
                level_category_base=str(row['Level Category Base']),
                count=int(row['Count'])
            )
            db.session.add(enrollment)
    
    return f"Processed {len(df)} enrollment records"

def process_popular_timeslots_file(file):
    """Process popular timeslots CSV file"""
    df = pd.read_csv(file)
    
    with db.session.no_autoflush:
        # Clear existing popular timeslots data
        db.session.query(PopularTimeslot).delete()
        
        for _, row in df.iterrows():
            timeslot = PopularTimeslot(
                time_slot=str(row['time_slot']),
                day=str(row['day']),
                level=str(row['level'])
            )
            db.session.add(timeslot)
    
    return f"Processed {len(df)} popular timeslot records"

# Existing API endpoints
@api_bp.route('/coach/')
def api_coach():
    name = request.args.get('name', '')
    branch_id = request.args.get('branch', '')
    position = request.args.get('position', '')
    level_id = request.args.get('level', '')

    query = Coach.query

    if name:
        query = query.filter(Coach.name.ilike(f'%{name}%'))
    
    if branch_id:
        query = query.join(CoachBranch).filter(CoachBranch.branch_id == branch_id)
    
    if position:
        query = query.filter(Coach.position == position)
    
    if level_id:
        query = query.join(CoachPreference).filter(CoachPreference.level_id == level_id)

    coaches = query.all()
    
    coaches_data = []
    for coach in coaches:
        assigned_branches = [cb.branch.abbrv for cb in coach.assigned_branches]
        preferred_levels = [cp.level.name for cp in coach.preferred_levels]
        
        coaches_data.append({
            'id': coach.id,
            'name': coach.name,
            'residential_area': coach.residential_area,
            'position': coach.position,
            'status': coach.status,
            'assigned_branches': assigned_branches,
            'preferred_levels': preferred_levels
        })
    
    return jsonify(coaches_data)

# To replace with timetable generation algorithm
@api_bp.route('/generate/', methods=['GET'])
def generate():
    return jsonify({
        'CCK': {
            'coaches': ['Chris', 'Yenzen', 'Vivian', 'Cheng Hong', 'Francis', 'Eugene'],
            'schedule': {
                'Tuesday': {
                    'Yenzen': [
                        {'name': 'L2', 'start_time': '1530', 'duration': 3},
                        {'name': 'L2', 'start_time': '1700', 'duration': 3},
                    ],
                    'Vivian': [
                        {'name': 'Lively', 'start_time': '1630', 'duration': 2},
                        {'name': 'Bubbly', 'start_time': '1730', 'duration': 2},
                    ],
                    'Cheng Hong': [
                        {'name': 'L1', 'start_time': '1530', 'duration': 3},
                        {'name': 'Flexi', 'start_time': '1730', 'duration': 2},
                    ],
                },
                'Wednesday': {
                    'Yenzen': [
                        {'name': 'L2', 'start_time': '1530', 'duration': 3},
                        {'name': 'L2', 'start_time': '1700', 'duration': 3},
                    ],
                    'Vivian': [
                        {'name': 'Flexi', 'start_time': '1600', 'duration': 2},
                        {'name': 'Lively', 'start_time': '1700', 'duration': 2},
                    ],
                    'Chris': [
                        {'name': 'L1', 'start_time': '1530', 'duration': 3},
                        {'name': 'L1', 'start_time': '1700', 'duration': 3},
                    ],
                },
                'Thursday': {
                    'Chris': [
                        {'name': 'L2', 'start_time': '1700', 'duration': 3},
                    ],
                    'Yenzen': [
                        {'name': 'L3', 'start_time': '1530', 'duration': 3},
                        {'name': 'L1', 'start_time': '1700', 'duration': 3},
                    ],
                    'Vivian': [
                        {'name': 'Jolly', 'start_time': '1030', 'duration': 2},
                        {'name': 'Bubbly', 'start_time': '1630', 'duration': 2},
                    ],
                }
            }
        }
    })