from flask import Blueprint, render_template, request, flash, redirect, jsonify, get_flashed_messages, url_for
from werkzeug.utils import secure_filename
import pandas as pd
import os
from application import db, bcrypt
from application.models import User, Coach, Level, Branch, CoachBranch, CoachOffday, CoachPreference, PopularTimeslots, EnrollmentCounts, BranchConfig, CoachAvailability
from flask_login import login_user, logout_user, login_required
from .forms import CoachFilter, CoachDetails, CSVUploadForm
from .timetabling_service import TimetablingService


pages_bp = Blueprint('pages', __name__)
api_bp = Blueprint('apis', __name__, url_prefix='/api')

@pages_bp.route('/')
def index():
    return render_template('index.html')

@pages_bp.route('/auth')
def auth():
    return render_template('auth.html')

@pages_bp.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@pages_bp.route('/timetable')
def timetable():
    return render_template('timetable.html')

@pages_bp.route('/upload')
def upload():
    return render_template('upload.html', form=CSVUploadForm())

@pages_bp.route('/upload', methods=['POST'])
def upload_csv():
    form = CSVUploadForm()
    
    if form.validate_on_submit():
        try:
            # Process uploaded files
            results = {}
            
            if form.availability_csv.data:
                results['availability'] = process_availability_csv(form.availability_csv.data)
            
            if form.branch_config_csv.data:
                results['branch_config'] = process_branch_config_csv(form.branch_config_csv.data)
            
            if form.coaches_csv.data:
                results['coaches'] = process_coaches_csv(form.coaches_csv.data)
            
            if form.enrollment_csv.data:
                results['enrollment'] = process_enrollment_csv(form.enrollment_csv.data)
            
            if form.popular_timeslots_csv.data:
                results['popular_timeslots'] = process_popular_timeslots_csv(form.popular_timeslots_csv.data)
            
            db.session.commit()
            
            flash(f'Successfully uploaded and processed {len(results)} file(s)', 'success')
            return redirect(url_for('pages.timetable'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error processing CSV files: {str(e)}', 'error')
    
    return render_template('upload.html', form=form)

def process_availability_csv(file):
    """Process availability.csv file"""
    df = pd.read_csv(file)
    
    # Clear existing availability data
    CoachAvailability.query.delete()
    
    for _, row in df.iterrows():
        availability = CoachAvailability(
            coach_id=row['coach_id'],
            day=row['day'],
            period=row['period'],
            available=row['available'],
            restriction_reason=row.get('restriction_reason', '')
        )
        db.session.add(availability)
    
    return f"Processed {len(df)} availability records"

def process_branch_config_csv(file):
    """Process branch_config.csv file"""
    df = pd.read_csv(file)
    
    # Clear existing branch config data
    BranchConfig.query.delete()
    
    for _, row in df.iterrows():
        config = BranchConfig(
            branch=row['branch'],
            max_classes_per_slot=row['max_classes_per_slot']
        )
        db.session.add(config)
    
    return f"Processed {len(df)} branch config records"

def process_coaches_csv(file):
    """Process coaches.csv file"""
    df = pd.read_csv(file)
    
    # Clear existing coach data
    Coach.query.delete()
    CoachBranch.query.delete()
    CoachPreference.query.delete()
    
    # Get qualification columns
    qual_columns = ['BearyTots', 'Jolly', 'Bubbly', 'Lively', 'Flexi', 
                   'Level_1', 'Level_2', 'Level_3', 'Level_4', 'Advance', 'Free']
    
    for _, row in df.iterrows():
        coach = Coach(
            id=row['coach_id'],
            name=row['coach_name'],
            residential_area=row['residential_area'],
            position=row['position'],
            status=row['status']
        )
        db.session.add(coach)
        db.session.flush()  # Get the coach ID
        
        # Add branch assignment
        branch = Branch.query.filter_by(abbrv=row['assigned_branch']).first()
        if branch:
            coach_branch = CoachBranch(coach_id=coach.id, branch_id=branch.id)
            db.session.add(coach_branch)
        
        # Add qualifications
        for qual_col in qual_columns:
            if qual_col in df.columns and row.get(qual_col, False):
                # Map column names to level names
                level_name = qual_col.replace('Level_', 'L').replace('BearyTots', 'Tots')
                level = Level.query.filter_by(name=level_name).first()
                if level:
                    preference = CoachPreference(coach_id=coach.id, level_id=level.id)
                    db.session.add(preference)
    
    return f"Processed {len(df)} coach records"

def process_enrollment_csv(file):
    """Process enrollment.csv file"""
    df = pd.read_csv(file)
    
    # Clear existing enrollment data
    EnrollmentCounts.query.delete()
    
    for _, row in df.iterrows():
        enrollment = EnrollmentCounts(
            branch=row['Branch'],
            level_category_base=row['Level Category Base'],
            count=row['Count']
        )
        db.session.add(enrollment)
    
    return f"Processed {len(df)} enrollment records"

def process_popular_timeslots_csv(file):
    """Process popular_timeslots.csv file"""
    df = pd.read_csv(file)
    
    # Clear existing popular timeslots data
    PopularTimeslots.query.delete()
    
    for _, row in df.iterrows():
        timeslot = PopularTimeslots(
            time_slot=row['time_slot'],
            day=row['day'],
            level=row['level']
        )
        db.session.add(timeslot)
    
    return f"Processed {len(df)} popular timeslot records"

@pages_bp.route('/database/coach')
def coach_db():
    return render_template('coach_db.html', filter=CoachFilter(), details=CoachDetails())

# Updated generate endpoint to use real timetabling algorithm
@api_bp.route('/generate', methods=['GET'])
def generate():
    try:
        service = TimetablingService()
        result = service.generate_timetable()
        return jsonify(result)
    except Exception as e:
        # Return fallback data in case of errors
        return jsonify({
            'error': str(e),
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
                    }
                }
            }
        })

@api_bp.route('/coach')
def coach():
    form = CoachFilter(request.args)
    query = db.session.query(Coach)

    if form.name.data:
        query = query.filter(Coach.name.ilike(f"%{form.name.data}%"))
    if form.branch.data:
        query = query.join(Coach.assigned_branches).filter(CoachBranch.branch_id == form.branch.data.id)
    if form.position.data:
        query = query.filter(Coach.position == form.position.data)
    if form.level.data:
        query = query.join(Coach.preferred_levels).filter_by(level_id=form.level.data.id)

    print(query)
    coaches = query.all()

    return jsonify([{
        'id': coach.id,
        'name': coach.name,
        'residential_area': coach.residential_area,
        'position': coach.position,
        'status': coach.status,
        'assigned_branches': [cb.branch.abbrv for cb in coach.assigned_branches],
        'offdays': [{
            'day': cd.day,
            'am': cd.am,
            'reason': cd.reason
        } for cd in coach.offdays],
        'preferred_levels': [cl.level.name for cl in coach.preferred_levels]
    } for coach in coaches])

@api_bp.route('/coach/<int:id>')
def coach_by_id(id):
    coach = db.session.query(Coach).filter(Coach.id == id).first()

    return jsonify({
        'id': coach.id,
        'name': coach.name,
        'residential_area': coach.residential_area,
        'position': coach.position,
        'status': coach.status,
        'assigned_branches': [cb.branch.abbrv for cb in coach.assigned_branches],
        'offdays': [{
            'day': cd.day,
            'am': cd.am,
            'reason': cd.reason
        } for cd in coach.offdays],
        'preferred_levels': [cl.level.name for cl in coach.preferred_levels]
    })