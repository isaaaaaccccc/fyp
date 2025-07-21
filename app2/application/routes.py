from flask import Blueprint, render_template, request, flash, redirect, jsonify, get_flashed_messages
from application import db, bcrypt
from application.models import User
from flask_login import login_user, logout_user, login_required
from .forms import CoachFilter, CoachDetails
from .models import Coach, Level, Branch, CoachBranch, CoachOffday, CoachPreference
from .services.timetabling_service import TimetablingService
import traceback
from datetime import datetime


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

@pages_bp.route('/database/coach')
def coach_db():
    return render_template('coach_db.html', filter=CoachFilter(), details=CoachDetails())

# Timetable generation using the sophisticated algorithm
@api_bp.route('/generate', methods=['GET'])
def generate():
    """Generate timetable using the integrated scheduling algorithm."""
    try:
        print(f"Timetable generation requested at {datetime.now()}")
        
        # Initialize the timetabling service
        timetabling_service = TimetablingService()
        
        # Generate the timetable
        schedule = timetabling_service.generate_timetable()
        
        # Validate the generated schedule
        validation_results = timetabling_service.validate_schedule(schedule)
        
        # Generate summary
        summary = timetabling_service.get_schedule_summary(schedule)
        summary['generation_time'] = datetime.now().isoformat()
        
        response = {
            'success': True,
            'schedule': schedule,
            'validation': validation_results,
            'summary': summary,
            'generated_at': datetime.now().isoformat()
        }
        
        # For compatibility with frontend, also include the schedule data at the root level
        response.update(schedule)
        
        print(f"Timetable generation completed successfully")
        return jsonify(response)
        
    except Exception as e:
        error_message = str(e)
        print(f"Timetable generation failed: {error_message}")
        print(f"Traceback: {traceback.format_exc()}")
        
        # Fallback to basic hardcoded schedule in case of error
        fallback_schedule = {
            'CCK': {
                'coaches': ['Chris', 'Yenzen'],
                'schedule': {
                    'Tuesday': {
                        'Chris': [
                            {'name': 'L1', 'start_time': '1530', 'duration': 3}
                        ],
                        'Yenzen': [
                            {'name': 'L2', 'start_time': '1530', 'duration': 3}
                        ]
                    }
                }
            }
        }
        
        return jsonify({
            'success': False,
            'error': error_message,
            'fallback_schedule': fallback_schedule,
            'generated_at': datetime.now().isoformat()
        }), 500

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