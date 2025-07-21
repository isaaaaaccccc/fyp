"""
Branch management routes for CRUD operations.
"""
from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from application import db
from application.models import Branch, CoachBranch
from wtforms import StringField, IntegerField, validators
from wtforms.form import Form


branch_bp = Blueprint('branch', __name__, url_prefix='/database/branch')


class BranchForm(Form):
    """Form for branch creation and editing."""
    name = StringField('Branch Name', [
        validators.Length(min=1, max=32),
        validators.DataRequired()
    ])
    abbrv = StringField('Abbreviation', [
        validators.Length(min=1, max=4),
        validators.DataRequired()
    ])
    max_classes = IntegerField('Max Classes Per Slot', [
        validators.NumberRange(min=1, max=20),
        validators.DataRequired()
    ])


@branch_bp.route('/')
def branch_page():
    """Display the branch management page."""
    branches = db.session.query(Branch).all()
    return render_template('branches.html', branches=branches, form=BranchForm())


@branch_bp.route('/api/list')
def api_list_branches():
    """API endpoint to get all branches."""
    branches = db.session.query(Branch).all()
    return jsonify([{
        'id': branch.id,
        'name': branch.name,
        'abbrv': branch.abbrv,
        'max_classes': branch.max_classes,
        'coach_count': len(branch.assigned_coaches)
    } for branch in branches])


@branch_bp.route('/api/create', methods=['POST'])
def api_create_branch():
    """API endpoint to create a new branch."""
    try:
        data = request.get_json()
        
        # Validate input
        if not data.get('name') or not data.get('abbrv'):
            return jsonify({'success': False, 'error': 'Name and abbreviation are required'})
        
        # Check for duplicates
        existing_name = db.session.query(Branch).filter_by(name=data['name']).first()
        if existing_name:
            return jsonify({'success': False, 'error': 'Branch name already exists'})
        
        existing_abbrv = db.session.query(Branch).filter_by(abbrv=data['abbrv']).first()
        if existing_abbrv:
            return jsonify({'success': False, 'error': 'Branch abbreviation already exists'})
        
        # Create new branch
        branch = Branch(
            name=data['name'].strip(),
            abbrv=data['abbrv'].strip().upper(),
            max_classes=int(data.get('max_classes', 4))
        )
        
        db.session.add(branch)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'branch': {
                'id': branch.id,
                'name': branch.name,
                'abbrv': branch.abbrv,
                'max_classes': branch.max_classes,
                'coach_count': 0
            },
            'message': 'Branch created successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': f'Error creating branch: {str(e)}'})


@branch_bp.route('/api/<int:branch_id>')
def api_get_branch(branch_id):
    """API endpoint to get a specific branch."""
    branch = db.session.query(Branch).filter_by(id=branch_id).first()
    
    if not branch:
        return jsonify({'success': False, 'error': 'Branch not found'}), 404
    
    return jsonify({
        'success': True,
        'branch': {
            'id': branch.id,
            'name': branch.name,
            'abbrv': branch.abbrv,
            'max_classes': branch.max_classes,
            'coach_count': len(branch.assigned_coaches),
            'assigned_coaches': [cb.coach.name for cb in branch.assigned_coaches]
        }
    })


@branch_bp.route('/api/<int:branch_id>/update', methods=['PUT'])
def api_update_branch(branch_id):
    """API endpoint to update a branch."""
    try:
        branch = db.session.query(Branch).filter_by(id=branch_id).first()
        
        if not branch:
            return jsonify({'success': False, 'error': 'Branch not found'}), 404
        
        data = request.get_json()
        
        # Validate input
        if not data.get('name') or not data.get('abbrv'):
            return jsonify({'success': False, 'error': 'Name and abbreviation are required'})
        
        # Check for duplicates (excluding current branch)
        existing_name = db.session.query(Branch).filter(
            Branch.name == data['name'],
            Branch.id != branch_id
        ).first()
        if existing_name:
            return jsonify({'success': False, 'error': 'Branch name already exists'})
        
        existing_abbrv = db.session.query(Branch).filter(
            Branch.abbrv == data['abbrv'],
            Branch.id != branch_id
        ).first()
        if existing_abbrv:
            return jsonify({'success': False, 'error': 'Branch abbreviation already exists'})
        
        # Update branch
        branch.name = data['name'].strip()
        branch.abbrv = data['abbrv'].strip().upper()
        branch.max_classes = int(data.get('max_classes', branch.max_classes))
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'branch': {
                'id': branch.id,
                'name': branch.name,
                'abbrv': branch.abbrv,
                'max_classes': branch.max_classes,
                'coach_count': len(branch.assigned_coaches)
            },
            'message': 'Branch updated successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': f'Error updating branch: {str(e)}'})


@branch_bp.route('/api/<int:branch_id>/delete', methods=['DELETE'])
def api_delete_branch(branch_id):
    """API endpoint to delete a branch."""
    try:
        branch = db.session.query(Branch).filter_by(id=branch_id).first()
        
        if not branch:
            return jsonify({'success': False, 'error': 'Branch not found'}), 404
        
        # Check if branch has assigned coaches
        if branch.assigned_coaches:
            return jsonify({
                'success': False, 
                'error': f'Cannot delete branch. {len(branch.assigned_coaches)} coaches are assigned to this branch.'
            })
        
        # Delete the branch
        db.session.delete(branch)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Branch deleted successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': f'Error deleting branch: {str(e)}'})


@branch_bp.route('/api/<int:branch_id>/coaches')
def api_get_branch_coaches(branch_id):
    """API endpoint to get coaches assigned to a branch."""
    branch = db.session.query(Branch).filter_by(id=branch_id).first()
    
    if not branch:
        return jsonify({'success': False, 'error': 'Branch not found'}), 404
    
    coaches = []
    for cb in branch.assigned_coaches:
        coach = cb.coach
        coaches.append({
            'id': coach.id,
            'name': coach.name,
            'position': coach.position,
            'status': coach.status,
            'residential_area': coach.residential_area
        })
    
    return jsonify({
        'success': True,
        'coaches': coaches,
        'branch': {
            'id': branch.id,
            'name': branch.name,
            'abbrv': branch.abbrv
        }
    })


@branch_bp.route('/api/statistics')
def api_branch_statistics():
    """API endpoint to get branch statistics."""
    try:
        branches = db.session.query(Branch).all()
        
        stats = {
            'total_branches': len(branches),
            'total_capacity': sum(b.max_classes for b in branches),
            'branches_with_coaches': len([b for b in branches if b.assigned_coaches]),
            'branch_details': []
        }
        
        for branch in branches:
            stats['branch_details'].append({
                'name': branch.name,
                'abbrv': branch.abbrv,
                'max_classes': branch.max_classes,
                'coach_count': len(branch.assigned_coaches),
                'utilization': len(branch.assigned_coaches) / max(1, branch.max_classes) * 100
            })
        
        return jsonify({
            'success': True,
            'statistics': stats
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': f'Error getting statistics: {str(e)}'})