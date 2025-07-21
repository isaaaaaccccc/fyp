"""
Level management routes for CRUD operations.
"""
from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from application import db
from application.models import Level, CoachPreference
from wtforms import StringField, IntegerField, validators
from wtforms.form import Form


level_bp = Blueprint('level', __name__, url_prefix='/database/level')


class LevelForm(Form):
    """Form for level creation and editing."""
    name = StringField('Level Name', [
        validators.Length(min=1, max=32),
        validators.DataRequired()
    ])
    max_students = IntegerField('Max Students', [
        validators.NumberRange(min=1, max=50),
        validators.DataRequired()
    ])
    duration = IntegerField('Duration (30-min slots)', [
        validators.NumberRange(min=1, max=6),
        validators.DataRequired()
    ])


@level_bp.route('/')
def level_page():
    """Display the level management page."""
    levels = db.session.query(Level).all()
    return render_template('levels.html', levels=levels, form=LevelForm())


@level_bp.route('/api/list')
def api_list_levels():
    """API endpoint to get all levels."""
    levels = db.session.query(Level).all()
    return jsonify([{
        'id': level.id,
        'name': level.name,
        'max_students': level.max_students,
        'duration': level.duration,
        'duration_minutes': level.duration * 30,  # Convert to minutes for display
        'coach_count': len(level.preferred_by_coaches)
    } for level in levels])


@level_bp.route('/api/create', methods=['POST'])
def api_create_level():
    """API endpoint to create a new level."""
    try:
        data = request.get_json()
        
        # Validate input
        if not data.get('name'):
            return jsonify({'success': False, 'error': 'Level name is required'})
        
        # Check for duplicates
        existing_level = db.session.query(Level).filter_by(name=data['name']).first()
        if existing_level:
            return jsonify({'success': False, 'error': 'Level name already exists'})
        
        # Create new level
        level = Level(
            name=data['name'].strip(),
            max_students=int(data.get('max_students', 10)),
            duration=int(data.get('duration', 2))  # Default 2 slots = 60 minutes
        )
        
        db.session.add(level)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'level': {
                'id': level.id,
                'name': level.name,
                'max_students': level.max_students,
                'duration': level.duration,
                'duration_minutes': level.duration * 30,
                'coach_count': 0
            },
            'message': 'Level created successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': f'Error creating level: {str(e)}'})


@level_bp.route('/api/<int:level_id>')
def api_get_level(level_id):
    """API endpoint to get a specific level."""
    level = db.session.query(Level).filter_by(id=level_id).first()
    
    if not level:
        return jsonify({'success': False, 'error': 'Level not found'}), 404
    
    return jsonify({
        'success': True,
        'level': {
            'id': level.id,
            'name': level.name,
            'max_students': level.max_students,
            'duration': level.duration,
            'duration_minutes': level.duration * 30,
            'coach_count': len(level.preferred_by_coaches),
            'preferred_by_coaches': [cp.coach.name for cp in level.preferred_by_coaches]
        }
    })


@level_bp.route('/api/<int:level_id>/update', methods=['PUT'])
def api_update_level(level_id):
    """API endpoint to update a level."""
    try:
        level = db.session.query(Level).filter_by(id=level_id).first()
        
        if not level:
            return jsonify({'success': False, 'error': 'Level not found'}), 404
        
        data = request.get_json()
        
        # Validate input
        if not data.get('name'):
            return jsonify({'success': False, 'error': 'Level name is required'})
        
        # Check for duplicates (excluding current level)
        existing_level = db.session.query(Level).filter(
            Level.name == data['name'],
            Level.id != level_id
        ).first()
        if existing_level:
            return jsonify({'success': False, 'error': 'Level name already exists'})
        
        # Update level
        level.name = data['name'].strip()
        level.max_students = int(data.get('max_students', level.max_students))
        level.duration = int(data.get('duration', level.duration))
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'level': {
                'id': level.id,
                'name': level.name,
                'max_students': level.max_students,
                'duration': level.duration,
                'duration_minutes': level.duration * 30,
                'coach_count': len(level.preferred_by_coaches)
            },
            'message': 'Level updated successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': f'Error updating level: {str(e)}'})


@level_bp.route('/api/<int:level_id>/delete', methods=['DELETE'])
def api_delete_level(level_id):
    """API endpoint to delete a level."""
    try:
        level = db.session.query(Level).filter_by(id=level_id).first()
        
        if not level:
            return jsonify({'success': False, 'error': 'Level not found'}), 404
        
        # Check if level has coaches assigned
        if level.preferred_by_coaches:
            return jsonify({
                'success': False, 
                'error': f'Cannot delete level. {len(level.preferred_by_coaches)} coaches prefer this level.'
            })
        
        # Delete the level
        db.session.delete(level)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Level deleted successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': f'Error deleting level: {str(e)}'})


@level_bp.route('/api/<int:level_id>/coaches')
def api_get_level_coaches(level_id):
    """API endpoint to get coaches who prefer this level."""
    level = db.session.query(Level).filter_by(id=level_id).first()
    
    if not level:
        return jsonify({'success': False, 'error': 'Level not found'}), 404
    
    coaches = []
    for cp in level.preferred_by_coaches:
        coach = cp.coach
        coaches.append({
            'id': coach.id,
            'name': coach.name,
            'position': coach.position,
            'status': coach.status,
            'residential_area': coach.residential_area,
            'assigned_branches': [cb.branch.abbrv for cb in coach.assigned_branches]
        })
    
    return jsonify({
        'success': True,
        'coaches': coaches,
        'level': {
            'id': level.id,
            'name': level.name,
            'max_students': level.max_students,
            'duration': level.duration
        }
    })


@level_bp.route('/api/statistics')
def api_level_statistics():
    """API endpoint to get level statistics."""
    try:
        levels = db.session.query(Level).all()
        
        stats = {
            'total_levels': len(levels),
            'total_capacity': sum(l.max_students for l in levels),
            'levels_with_coaches': len([l for l in levels if l.preferred_by_coaches]),
            'level_details': []
        }
        
        for level in levels:
            stats['level_details'].append({
                'name': level.name,
                'max_students': level.max_students,
                'duration': level.duration,
                'duration_minutes': level.duration * 30,
                'coach_count': len(level.preferred_by_coaches),
                'capacity_per_hour': level.max_students * (60 / (level.duration * 30))
            })
        
        return jsonify({
            'success': True,
            'statistics': stats
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': f'Error getting statistics: {str(e)}'})


@level_bp.route('/api/hierarchy')
def api_level_hierarchy():
    """API endpoint to get level hierarchy information."""
    try:
        # Define the standard hierarchy from the algorithm
        hierarchy = [
            'Tots', 'Jolly', 'Bubbly', 'Lively', 'Flexi', 
            'L1', 'L2', 'L3', 'L4', 'Advance', 'Free'
        ]
        
        levels = db.session.query(Level).all()
        
        hierarchy_info = []
        for i, level_name in enumerate(hierarchy):
            level = next((l for l in levels if l.name == level_name), None)
            if level:
                hierarchy_info.append({
                    'name': level.name,
                    'position': i + 1,
                    'max_students': level.max_students,
                    'duration': level.duration,
                    'coach_count': len(level.preferred_by_coaches),
                    'exists': True
                })
            else:
                hierarchy_info.append({
                    'name': level_name,
                    'position': i + 1,
                    'exists': False
                })
        
        return jsonify({
            'success': True,
            'hierarchy': hierarchy_info,
            'total_defined': len([h for h in hierarchy_info if h['exists']])
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': f'Error getting hierarchy: {str(e)}'})