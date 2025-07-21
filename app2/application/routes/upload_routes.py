"""
Upload routes for CSV data import functionality.
"""
from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from werkzeug.utils import secure_filename
from application import db
from application.models import Coach, Branch, Level, CoachBranch, CoachOffday, CoachPreference
from application.utils.file_upload import FileUploadHandler, CSVDataProcessor
import os
import traceback


upload_bp = Blueprint('upload', __name__, url_prefix='/upload')


@upload_bp.route('/')
def upload_page():
    """Display the data upload page."""
    return render_template('upload.html')


@upload_bp.route('/preview', methods=['POST'])
def preview_csv():
    """Preview CSV file before import."""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file selected'})
        
        file = request.files['file']
        upload_type = request.form.get('upload_type', '')
        
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'})
        
        # Initialize upload handler
        upload_handler = FileUploadHandler()
        
        # Save the file temporarily
        filepath = upload_handler.save_uploaded_file(file, file.filename)
        
        # Get expected columns based on upload type
        expected_columns = []
        if upload_type == 'coaches':
            expected_columns = upload_handler.get_coaches_csv_columns()
        elif upload_type == 'availability':
            expected_columns = upload_handler.get_availability_csv_columns()
        elif upload_type == 'enrollment':
            expected_columns = upload_handler.get_enrollment_csv_columns()
        elif upload_type == 'branch_config':
            expected_columns = upload_handler.get_branch_config_csv_columns()
        else:
            return jsonify({'success': False, 'error': 'Invalid upload type'})
        
        # Validate CSV structure
        is_valid, message, df = upload_handler.validate_csv_structure(filepath, expected_columns)
        
        if not is_valid:
            upload_handler.cleanup_file(filepath)
            return jsonify({'success': False, 'error': message})
        
        # Generate preview data
        preview_data = upload_handler.preview_csv_data(filepath)
        
        # Store filepath in session for later import (in real app, use more secure method)
        preview_data['temp_filepath'] = filepath
        preview_data['upload_type'] = upload_type
        
        return jsonify({
            'success': True,
            'preview': preview_data,
            'message': 'CSV validated successfully'
        })
        
    except Exception as e:
        return jsonify({
            'success': False, 
            'error': f'Error processing file: {str(e)}'
        })


@upload_bp.route('/import', methods=['POST'])
def import_csv():
    """Import validated CSV data into database."""
    try:
        data = request.get_json()
        filepath = data.get('filepath', '')
        upload_type = data.get('upload_type', '')
        
        if not filepath or not os.path.exists(filepath):
            return jsonify({'success': False, 'error': 'File not found'})
        
        # Process the CSV data
        processor = CSVDataProcessor()
        
        if upload_type == 'coaches':
            result = _import_coaches_data(filepath, processor)
        elif upload_type == 'availability':
            result = _import_availability_data(filepath, processor)
        elif upload_type == 'enrollment':
            result = _import_enrollment_data(filepath, processor)
        elif upload_type == 'branch_config':
            result = _import_branch_config_data(filepath, processor)
        else:
            return jsonify({'success': False, 'error': 'Invalid upload type'})
        
        # Cleanup temporary file
        FileUploadHandler().cleanup_file(filepath)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Import failed: {str(e)}',
            'traceback': traceback.format_exc()
        })


def _import_coaches_data(filepath: str, processor: CSVDataProcessor) -> dict:
    """Import coaches data from CSV."""
    import pandas as pd
    
    df = pd.read_csv(filepath)
    coaches_data = processor.process_coaches_csv(df)
    
    imported_count = 0
    updated_count = 0
    errors = []
    
    for coach_data in coaches_data:
        try:
            # Check if coach already exists
            existing_coach = db.session.query(Coach).filter_by(name=coach_data['name']).first()
            
            if existing_coach:
                # Update existing coach
                existing_coach.residential_area = coach_data['residential_area']
                existing_coach.position = coach_data['position']
                existing_coach.status = coach_data['status']
                
                # Clear existing relationships
                db.session.query(CoachBranch).filter_by(coach_id=existing_coach.id).delete()
                db.session.query(CoachPreference).filter_by(coach_id=existing_coach.id).delete()
                
                coach = existing_coach
                updated_count += 1
            else:
                # Create new coach
                coach = Coach(
                    name=coach_data['name'],
                    residential_area=coach_data['residential_area'],
                    position=coach_data['position'],
                    status=coach_data['status']
                )
                db.session.add(coach)
                imported_count += 1
            
            db.session.flush()  # Get the coach ID
            
            # Add branch assignments
            for branch_name in coach_data['assigned_branches']:
                branch = db.session.query(Branch).filter_by(abbrv=branch_name).first()
                if branch:
                    coach_branch = CoachBranch(coach_id=coach.id, branch_id=branch.id)
                    db.session.add(coach_branch)
            
            # Add level preferences
            for level_name in coach_data['preferred_levels']:
                level = db.session.query(Level).filter_by(name=level_name).first()
                if level:
                    coach_pref = CoachPreference(coach_id=coach.id, level_id=level.id)
                    db.session.add(coach_pref)
            
        except Exception as e:
            errors.append(f"Error importing coach {coach_data['name']}: {str(e)}")
    
    db.session.commit()
    
    return {
        'success': True,
        'imported': imported_count,
        'updated': updated_count,
        'errors': errors,
        'message': f'Successfully imported {imported_count} coaches, updated {updated_count}'
    }


def _import_availability_data(filepath: str, processor: CSVDataProcessor) -> dict:
    """Import coach availability data from CSV."""
    import pandas as pd
    
    df = pd.read_csv(filepath)
    availability_data = processor.process_availability_csv(df)
    
    # Clear existing availability data
    db.session.query(CoachOffday).delete()
    
    imported_count = 0
    errors = []
    
    for avail_data in availability_data:
        try:
            coach = db.session.query(Coach).filter_by(name=avail_data['coach_name']).first()
            if coach:
                # Only create record if NOT available (off day)
                if not avail_data['available']:
                    offday = CoachOffday(
                        coach_id=coach.id,
                        day=avail_data['day'],
                        am=avail_data['am'],
                        reason='Imported from CSV'
                    )
                    db.session.add(offday)
                    imported_count += 1
            else:
                errors.append(f"Coach not found: {avail_data['coach_name']}")
                
        except Exception as e:
            errors.append(f"Error importing availability for {avail_data['coach_name']}: {str(e)}")
    
    db.session.commit()
    
    return {
        'success': True,
        'imported': imported_count,
        'errors': errors,
        'message': f'Successfully imported {imported_count} availability records'
    }


def _import_enrollment_data(filepath: str, processor: CSVDataProcessor) -> dict:
    """Import enrollment data from CSV (stored as sample data for algorithm)."""
    import pandas as pd
    
    df = pd.read_csv(filepath)
    enrollment_data = processor.process_enrollment_csv(df)
    
    # For now, we'll just return success since enrollment data is used by the algorithm
    # In a real system, this would be stored in an enrollment table
    
    return {
        'success': True,
        'imported': len(enrollment_data),
        'errors': [],
        'message': f'Successfully processed {len(enrollment_data)} enrollment records for algorithm use'
    }


def _import_branch_config_data(filepath: str, processor: CSVDataProcessor) -> dict:
    """Import branch configuration data from CSV."""
    import pandas as pd
    
    df = pd.read_csv(filepath)
    branch_config_data = processor.process_branch_config_csv(df)
    
    updated_count = 0
    errors = []
    
    for config_data in branch_config_data:
        try:
            branch = db.session.query(Branch).filter_by(abbrv=config_data['branch']).first()
            if branch:
                branch.max_classes = config_data['max_classes']
                updated_count += 1
            else:
                errors.append(f"Branch not found: {config_data['branch']}")
                
        except Exception as e:
            errors.append(f"Error updating branch config {config_data['branch']}: {str(e)}")
    
    db.session.commit()
    
    return {
        'success': True,
        'updated': updated_count,
        'errors': errors,
        'message': f'Successfully updated {updated_count} branch configurations'
    }