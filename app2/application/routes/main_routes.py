from flask import Blueprint, render_template, request, flash, redirect, jsonify, get_flashed_messages
from application import db, bcrypt
from application.models import User
from flask_login import login_user, logout_user, login_required
from application.forms import CoachFilter, CoachDetails
from application.models import Coach, Level, Branch, CoachBranch, CoachOffday, CoachPreference
from application.services.timetabling_service import TimetablingService
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
        
        # Get algorithm type from query parameters (default to enhanced)
        algorithm_type = request.args.get('algorithm', 'enhanced')
        use_csv_export = request.args.get('use_csv', 'true').lower() == 'true'
        
        print(f"Algorithm type: {algorithm_type}, Use CSV: {use_csv_export}")
        
        if algorithm_type == 'enhanced':
            # Use the new Enhanced Strict Constraint Scheduler
            from application.services.enhanced_timetabling_service import EnhancedTimetablingService
            
            enhanced_service = EnhancedTimetablingService(use_csv_export=use_csv_export)
            response = enhanced_service.generate_timetable(algorithm_type='enhanced')
            
        else:
            # Use the legacy algorithm
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
                'generated_at': datetime.now().isoformat(),
                'algorithm_type': 'legacy'
            }
            
            # For compatibility with frontend, also include the schedule data at the root level
            response.update(schedule)
        
        print(f"Timetable generation completed successfully using {algorithm_type} algorithm")
        return jsonify(response)
        
    except Exception as e:
        error_message = str(e)
        print(f"Timetable generation failed: {error_message}")
        print(f"Traceback: {traceback.format_exc()}")
        
        # Try fallback to legacy algorithm if enhanced fails
        try:
            if algorithm_type == 'enhanced':
                print("Enhanced algorithm failed, trying legacy fallback...")
                timetabling_service = TimetablingService()
                schedule = timetabling_service.generate_timetable()
                
                response = {
                    'success': True,
                    'schedule': schedule,
                    'validation': {'valid': True, 'warnings': ['Used legacy fallback']},
                    'summary': {'generation_time': datetime.now().isoformat()},
                    'generated_at': datetime.now().isoformat(),
                    'algorithm_type': 'legacy_fallback',
                    'note': 'Enhanced algorithm failed, used legacy as fallback'
                }
                response.update(schedule)
                return jsonify(response)
        except Exception as fallback_error:
            print(f"Legacy fallback also failed: {fallback_error}")
        
        # Ultimate fallback to basic hardcoded schedule
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
            'generated_at': datetime.now().isoformat(),
            'algorithm_type': 'hardcoded_fallback'
        }), 500

# Enhanced timetable generation endpoint with detailed configuration
@api_bp.route('/generate/enhanced', methods=['GET', 'POST'])
def generate_enhanced():
    """Generate timetable using the Enhanced Strict Constraint Scheduler with configuration options."""
    try:
        print(f"Enhanced timetable generation requested at {datetime.now()}")
        
        # Get configuration from request
        if request.method == 'POST':
            config = request.get_json() or {}
        else:
            config = {}
        
        use_csv_export = config.get('use_csv_export', True)
        workload_limits = config.get('workload_limits', {})
        algorithm_params = config.get('algorithm_params', {})
        
        print(f"Enhanced algorithm configuration: {config}")
        
        # Initialize enhanced service
        from application.services.enhanced_timetabling_service import EnhancedTimetablingService
        
        enhanced_service = EnhancedTimetablingService(use_csv_export=use_csv_export)
        
        # Update configuration if provided
        if workload_limits or algorithm_params:
            current_config = enhanced_service.get_algorithm_configuration()
            if workload_limits:
                current_config['workload_limits'].update(workload_limits)
            if algorithm_params:
                current_config['algorithm'].update(algorithm_params)
            enhanced_service.update_algorithm_configuration(current_config)
        
        # Generate enhanced timetable
        response = enhanced_service.generate_timetable(algorithm_type='enhanced')
        
        # Add configuration info to response
        response['configuration_used'] = enhanced_service.get_algorithm_configuration()
        response['supported_features'] = enhanced_service.get_supported_features()
        
        print(f"Enhanced timetable generation completed successfully")
        return jsonify(response)
        
    except Exception as e:
        error_message = str(e)
        print(f"Enhanced timetable generation failed: {error_message}")
        print(f"Traceback: {traceback.format_exc()}")
        
        return jsonify({
            'success': False,
            'error': error_message,
            'algorithm_type': 'enhanced',
            'generated_at': datetime.now().isoformat()
        }), 500

# Algorithm information endpoint
@api_bp.route('/algorithms', methods=['GET'])
def get_algorithms():
    """Get information about available scheduling algorithms."""
    try:
        from application.services.enhanced_timetabling_service import EnhancedTimetablingService
        
        enhanced_service = EnhancedTimetablingService()
        
        algorithms = {
            'enhanced': {
                'name': 'Enhanced Strict Constraint Scheduler',
                'version': '1.0',
                'description': 'Advanced 6-phase optimization algorithm with strict constraint compliance',
                'features': enhanced_service.get_supported_features(),
                'configuration': enhanced_service.get_algorithm_configuration(),
                'endpoint': '/api/generate/enhanced'
            },
            'legacy': {
                'name': 'Legacy Scheduler',
                'version': '1.0',
                'description': 'Original scheduling algorithm with basic optimization',
                'features': ['Basic optimization', 'Coverage maximization'],
                'endpoint': '/api/generate?algorithm=legacy'
            }
        }
        
        return jsonify({
            'success': True,
            'algorithms': algorithms,
            'default': 'enhanced'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
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