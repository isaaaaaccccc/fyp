from flask import Blueprint, render_template, request, flash, redirect, jsonify, get_flashed_messages, url_for
from werkzeug.utils import secure_filename
from application import db, bcrypt
from application.models import User, Coach, Level, Branch, CoachBranch, CoachOffday, CoachPreference, Availability, BranchConfig, Enrollment, PopularTimeslot
from flask_login import login_user, logout_user, login_required
from .forms import CoachFilter, CoachDetails, DataUploadForm
from .data_processor import load_database_driven
from .timetable_scheduler import execute_enhanced_strict_constraint_scheduling
import pandas as pd
import os
import json

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
    
    if request.method == 'GET':
        return render_template('data_upload.html', form=form)
    
    # Handle POST request
    print("🚀 Data upload POST request received")
    print(f"📋 Request files: {list(request.files.keys())}")
    print(f"📋 Form validation: {form.validate_on_submit()}")
    
    # Check if this is an AJAX request
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.content_type == 'application/json'
    
    if not form.validate_on_submit():
        print(f"❌ Form validation failed: {form.errors}")
        if is_ajax:
            return jsonify({
                'success': False,
                'message': 'Form validation failed. Please check your files and try again.',
                'errors': form.errors
            }), 400
        else:
            flash('Form validation failed. Please check your files and try again.', 'error')
            return render_template('data_upload.html', form=form)
    
    try:
        upload_results = []
        processed_files = []
        
        print("✅ Form validation passed, processing files...")
        
        # Process each file type
        file_processors = [
            ('availability_file', process_availability_file),
            ('branch_config_file', process_branch_config_file),
            ('coaches_file', process_coaches_file),
            ('enrollment_file', process_enrollment_file),
            ('popular_timeslots_file', process_popular_timeslots_file)
        ]
        
        for field_name, processor_func in file_processors:
            field = getattr(form, field_name)
            if field.data and hasattr(field.data, 'filename') and field.data.filename:
                try:
                    print(f"📁 Processing {field_name}: {field.data.filename}")
                    # Reset file pointer to beginning
                    field.data.seek(0)
                    result = processor_func(field.data)
                    upload_results.append(result)
                    processed_files.append({
                        'field': field_name,
                        'filename': field.data.filename,
                        'result': result
                    })
                    print(f"✅ {field_name} result: {result}")
                except Exception as e:
                    print(f"❌ Error processing {field_name}: {str(e)}")
                    raise Exception(f"Error processing {field.data.filename}: {str(e)}")
        
        if upload_results:
            # Commit all changes
            db.session.commit()
            success_message = f'Successfully processed {len(upload_results)} file(s)!'
            print(f"✅ {success_message}")
            
            if is_ajax:
                return jsonify({
                    'success': True,
                    'message': success_message,
                    'processed_files': processed_files,
                    'file_count': len(upload_results)
                })
            else:
                flash(success_message, 'success')
                return redirect(url_for('pages.data_upload'))
        else:
            error_message = 'No files were uploaded. Please select at least one CSV file.'
            print(f"❌ {error_message}")
            
            if is_ajax:
                return jsonify({
                    'success': False,
                    'message': error_message,
                    'processed_files': [],
                    'file_count': 0
                }), 400
            else:
                flash(error_message, 'warning')
                return render_template('data_upload.html', form=form)
                
    except Exception as e:
        db.session.rollback()
        error_msg = f'Error processing files: {str(e)}'
        print(f"❌ Exception occurred: {error_msg}")
        import traceback
        traceback.print_exc()
        
        if is_ajax:
            return jsonify({
                'success': False,
                'message': error_msg,
                'processed_files': [],
                'file_count': 0
            }), 500
        else:
            flash(error_msg, 'error')
            return render_template('data_upload.html', form=form)

# API Routes for Timetable Generation
@api_bp.route('/generate-timetable/', methods=['POST'])
def generate_timetable():
    """Generate timetable using the scheduling algorithm"""
    try:
        print("🚀 Starting timetable generation...")
        
        # Load data from database
        print("📊 Loading data from database...")
        data = load_database_driven()
        
        # Run the scheduling algorithm
        print("⚙️ Running enhanced strict constraint scheduling...")
        results = execute_enhanced_strict_constraint_scheduling(data)
        
        # Format for timetable display
        formatted_schedule = format_schedule_for_display(results['schedule'])
        
        return jsonify({
            'success': True,
            'message': 'Timetable generated successfully',
            'schedule': formatted_schedule,
            'statistics': results['statistics'],
            'total_classes': len(results['schedule']),
            'coverage_percentage': results['statistics']['coverage_percentage']
        })
        
    except Exception as e:
        import traceback
        error_msg = f"Error generating timetable: {str(e)}"
        print(f"❌ {error_msg}")
        traceback.print_exc()
        
        return jsonify({
            'success': False,
            'message': error_msg,
            'error': str(e)
        }), 500

@api_bp.route('/export-timetable/', methods=['GET'])
def export_timetable():
    """Export current timetable to CSV"""
    try:
        # Load data from database
        data = load_database_driven()
        
        # Run the scheduling algorithm
        results = execute_enhanced_strict_constraint_scheduling(data)
        
        # Create CSV
        df = pd.DataFrame(results['schedule'])
        
        # Save to static folder for download
        csv_path = os.path.join('application', 'static', 'exports', 'timetable.csv')
        os.makedirs(os.path.dirname(csv_path), exist_ok=True)
        df.to_csv(csv_path, index=False)
        
        return jsonify({
            'success': True,
            'message': 'Timetable exported successfully',
            'download_url': '/static/exports/timetable.csv',
            'filename': 'timetable.csv'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f"Error exporting timetable: {str(e)}"
        }), 500

def format_schedule_for_display(schedule):
    """Format schedule data for timetable.js display"""
    formatted_classes = []
    
    # Day mapping for proper ordering
    day_order = {'TUE': 1, 'WED': 2, 'THU': 3, 'FRI': 4, 'SAT': 5, 'SUN': 6}
    
    # Branch color mapping
    branch_colors = {
        'BB': '#FF6B6B',    # Red
        'CCK': '#4ECDC4',   # Teal
        'CH': '#45B7D1',    # Blue
        'HG': '#96CEB4',    # Green
        'KT': '#FFEAA7',    # Yellow
        'PR': '#DDA0DD'     # Purple
    }
    
    for entry in schedule:
        # Convert to format expected by timetable.js
        formatted_entry = {
            'id': f"class_{entry.get('id', len(formatted_classes))}",
            'branch': entry['Branch'],
            'level': entry['Gymnastics Level'],
            'day': entry['Day'],
            'dayOrder': day_order.get(entry['Day'], 7),
            'startTime': entry['Start Time'],
            'endTime': entry['End Time'],
            'duration': entry.get('Duration (min)', 60),
            'coach': {
                'id': entry['Coach ID'],
                'name': entry['Coach Name'],
                'status': entry['Coach Status']
            },
            'students': entry['Students'],
            'capacity': entry['Capacity'],
            'isPopular': entry.get('Popular Slot', 'No') == 'Yes',
            'isMerged': entry.get('Merged', 'No') == 'Yes',
            'mergedWith': entry.get('Merged With', ''),
            'color': branch_colors.get(entry['Branch'], '#95A5A6'),
            'utilization': round((entry['Students'] / entry['Capacity']) * 100, 1) if entry['Capacity'] > 0 else 0
        }
        
        formatted_classes.append(formatted_entry)
    
    # Sort by day and time
    formatted_classes.sort(key=lambda x: (x['dayOrder'], x['startTime']))
    
    return formatted_classes

# File processing functions (same as before but with better error handling)
def process_availability_file(file):
    """Process availability CSV file"""
    try:
        df = pd.read_csv(file)
        print(f"📊 Loaded {len(df)} rows from availability CSV")
        
        if df.empty:
            raise ValueError("CSV file is empty")
        
        # Validate required columns
        required_columns = ['availability_id', 'coach_id', 'day', 'period', 'available']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise ValueError(f"Missing required columns: {', '.join(missing_columns)}")
        
        with db.session.no_autoflush:
            # Clear existing availability data
            deleted_count = db.session.query(Availability).delete()
            print(f"🗑️ Deleted {deleted_count} existing availability records")
            
            processed_count = 0
            for _, row in df.iterrows():
                try:
                    # Handle NaN values
                    restriction_reason = row.get('restriction_reason')
                    if pd.isna(restriction_reason):
                        restriction_reason = None
                    
                    # Create new record
                    availability = Availability(
                        original_availability_id=int(row['availability_id']),
                        coach_id=int(row['coach_id']),
                        day=str(row['day']).strip(),
                        period=str(row['period']).strip(),
                        available=bool(row['available']),
                        restriction_reason=restriction_reason
                    )
                    db.session.add(availability)
                    processed_count += 1
                except Exception as e:
                    print(f"❌ Error processing row {processed_count + 1}: {e}")
                    continue
        
        return f"Processed {processed_count} availability records"
    except Exception as e:
        print(f"❌ Error in process_availability_file: {e}")
        raise

def process_branch_config_file(file):
    """Process branch config CSV file"""
    try:
        df = pd.read_csv(file)
        print(f"📊 Loaded {len(df)} rows from branch config CSV")
        
        if df.empty:
            raise ValueError("CSV file is empty")
        
        # Validate required columns
        required_columns = ['branch', 'max_classes_per_slot']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise ValueError(f"Missing required columns: {', '.join(missing_columns)}")
        
        with db.session.no_autoflush:
            # Clear existing branch config data
            deleted_count = db.session.query(BranchConfig).delete()
            print(f"🗑️ Deleted {deleted_count} existing branch config records")
            
            processed_count = 0
            for _, row in df.iterrows():
                try:
                    config = BranchConfig(
                        branch=str(row['branch']).strip(),
                        max_classes_per_slot=int(row['max_classes_per_slot'])
                    )
                    db.session.add(config)
                    processed_count += 1
                except Exception as e:
                    print(f"❌ Error processing row {processed_count + 1}: {e}")
                    continue
        
        return f"Processed {processed_count} branch configurations"
    except Exception as e:
        print(f"❌ Error in process_branch_config_file: {e}")
        raise

def process_coaches_file(file):
    """Process coaches CSV file"""
    try:
        df = pd.read_csv(file)
        print(f"📊 Loaded {len(df)} rows from coaches CSV")
        
        if df.empty:
            raise ValueError("CSV file is empty")
        
        # Validate required columns
        required_columns = ['coach_id', 'coach_name', 'residential_area', 'status']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise ValueError(f"Missing required columns: {', '.join(missing_columns)}")
        
        processed_count = 0
        with db.session.no_autoflush:
            for _, row in df.iterrows():
                try:
                    coach_id = int(row['coach_id'])
                    existing_coach = Coach.query.filter_by(id=coach_id).first()
                    
                    # Handle position field
                    position = str(row['position']) if 'position' in row and not pd.isna(row['position']) else 'Part time'
                    
                    if existing_coach:
                        # Update existing coach
                        existing_coach.name = str(row['coach_name']).strip()
                        existing_coach.residential_area = str(row['residential_area']).strip()
                        existing_coach.position = position.strip()
                        existing_coach.status = str(row['status']).strip()
                    else:
                        # Create new coach
                        coach = Coach(
                            id=coach_id,
                            name=str(row['coach_name']).strip(),
                            residential_area=str(row['residential_area']).strip(),
                            position=position.strip(),
                            status=str(row['status']).strip()
                        )
                        db.session.add(coach)
                    
                    processed_count += 1
                except Exception as e:
                    print(f"❌ Error processing coach row {processed_count + 1}: {e}")
                    continue
        
        return f"Processed {processed_count} coach records"
    except Exception as e:
        print(f"❌ Error in process_coaches_file: {e}")
        raise

def process_enrollment_file(file):
    """Process enrollment CSV file"""
    try:
        df = pd.read_csv(file)
        print(f"📊 Loaded {len(df)} rows from enrollment CSV")
        
        if df.empty:
            raise ValueError("CSV file is empty")
        
        # Validate required columns
        required_columns = ['Branch', 'Level Category Base', 'Count']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise ValueError(f"Missing required columns: {', '.join(missing_columns)}")
        
        with db.session.no_autoflush:
            # Clear existing enrollment data
            deleted_count = db.session.query(Enrollment).delete()
            print(f"🗑️ Deleted {deleted_count} existing enrollment records")
            
            processed_count = 0
            for _, row in df.iterrows():
                try:
                    enrollment = Enrollment(
                        branch=str(row['Branch']).strip(),
                        level_category_base=str(row['Level Category Base']).strip(),
                        count=int(row['Count'])
                    )
                    db.session.add(enrollment)
                    processed_count += 1
                except Exception as e:
                    print(f"❌ Error processing row {processed_count + 1}: {e}")
                    continue
        
        return f"Processed {processed_count} enrollment records"
    except Exception as e:
        print(f"❌ Error in process_enrollment_file: {e}")
        raise

def process_popular_timeslots_file(file):
    """Process popular timeslots CSV file"""
    try:
        df = pd.read_csv(file)
        print(f"📊 Loaded {len(df)} rows from popular timeslots CSV")
        
        if df.empty:
            raise ValueError("CSV file is empty")
        
        # Validate required columns
        required_columns = ['time_slot', 'day', 'level']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise ValueError(f"Missing required columns: {', '.join(missing_columns)}")
        
        with db.session.no_autoflush:
            # Clear existing popular timeslots data
            deleted_count = db.session.query(PopularTimeslot).delete()
            print(f"🗑️ Deleted {deleted_count} existing popular timeslot records")
            
            processed_count = 0
            for _, row in df.iterrows():
                try:
                    timeslot = PopularTimeslot(
                        time_slot=str(row['time_slot']).strip(),
                        day=str(row['day']).strip(),
                        level=str(row['level']).strip()
                    )
                    db.session.add(timeslot)
                    processed_count += 1
                except Exception as e:
                    print(f"❌ Error processing row {processed_count + 1}: {e}")
                    continue
        
        return f"Processed {processed_count} popular timeslot records"
    except Exception as e:
        print(f"❌ Error in process_popular_timeslots_file: {e}")
        raise

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

@api_bp.route('/generate/', methods=['GET'])
def generate():
    return jsonify({'message': 'Timetable generation placeholder'})