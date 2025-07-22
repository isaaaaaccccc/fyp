from flask import Blueprint, render_template, request, flash, redirect, jsonify, get_flashed_messages
from application import db, bcrypt
from application.models import User
from flask_login import login_user, logout_user, login_required
from .forms import CoachFilter, CoachDetails
from .models import Coach, Level, Branch, CoachBranch, CoachOffday, CoachPreference


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

# To replace with timetable generation algorithm
@api_bp.route('/generate', methods=['GET'])
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
                        {'name': 'Bubbly', 'start_time': '1730', 'duration': 2},
                    ],
                    'Cheng Hong': [
                        {'name': 'Bubbly', 'start_time': '1630', 'duration': 2},
                        {'name': 'Bubbly', 'start_time': '1730', 'duration': 2},
                    ],
                },
                'Friday': {
                    'Chris': [
                        {'name': 'L3', 'start_time': '1530', 'duration': 3},
                        {'name': 'L3', 'start_time': '1700', 'duration': 3},
                    ],
                    'Yenzen': [
                        {'name': 'L1', 'start_time': '1530', 'duration': 3},
                        {'name': 'L2', 'start_time': '1730', 'duration': 3},
                    ],
                    'Vivian': [
                        {'name': 'Tots', 'start_time': '1100', 'duration': 2},
                        {'name': 'Jolly', 'start_time': '1600', 'duration': 2},
                        {'name': 'Lively', 'start_time': '1700', 'duration': 2},
                        {'name': 'Flexi', 'start_time': '1800', 'duration': 2},
                    ],
                    'Cheng Hong': [
                        {'name': 'L1', 'start_time': '1530', 'duration': 3},
                        {'name': 'Flexi', 'start_time': '1800', 'duration': 2},
                    ],
                },
                'Saturday': {
                    'Chris': [
                        {'name': 'L4', 'start_time': '1400', 'duration': 3},
                        {'name': 'Flexi', 'start_time': '1630', 'duration': 2},
                    ],
                    'Yenzen': [
                        {'name': 'L1', 'start_time': '0900', 'duration': 3},
                        {'name': 'L1', 'start_time': '1030', 'duration': 3},
                        {'name': 'L3', 'start_time': '1230', 'duration': 3},
                        {'name': 'L1', 'start_time': '1400', 'duration': 3},
                        {'name': 'L2', 'start_time': '1700', 'duration': 3},
                    ],
                    'Vivian': [
                        {'name': 'Bubbly', 'start_time': '0930', 'duration': 2},
                        {'name': 'Jolly', 'start_time': '1030', 'duration': 2},
                        {'name': 'Jolly', 'start_time': '1130', 'duration': 2},
                        {'name': 'Bubbly', 'start_time': '1530', 'duration': 2},
                        {'name': 'Bubbly', 'start_time': '1630', 'duration': 2},
                    ],
                    'Cheng Hong': [
                        {'name': 'Flexi', 'start_time': '0930', 'duration': 2},
                        {'name': 'Bubbly', 'start_time': '1130', 'duration': 2},
                        {'name': 'L1', 'start_time': '1230', 'duration': 3},
                        {'name': 'L1', 'start_time': '1530', 'duration': 3},
                        {'name': 'Lively', 'start_time': '1730', 'duration': 2,}
                    ],
                    'Francis': [
                        {'name': 'Lively', 'start_time': '0930', 'duration': 2},
                        {'name': 'Flexi', 'start_time': '1030', 'duration': 2},
                        {'name': 'Lively', 'start_time': '1130', 'duration': 2},
                    ],
                    'Eugene': [
                        {'name': 'L3', 'start_time': '1400', 'duration': 3},
                        {'name': 'L3', 'start_time': '1530', 'duration': 3},
                    ]
                },
                'Sunday': {
                    'Chris': [
                        {'name': 'L3', 'start_time': '1230', 'duration': 3},
                        {'name': 'L3', 'start_time': '1400', 'duration': 3},
                        {'name': 'Lively', 'start_time': '1630', 'duration': 2},
                    ],
                    'Yenzen': [
                        {'name': 'L1', 'start_time': '0900', 'duration': 3},
                        {'name': 'L1', 'start_time': '1030', 'duration': 3},
                        {'name': 'L2', 'start_time': '1230', 'duration': 3},
                        {'name': 'L2', 'start_time': '1400', 'duration': 3},
                        {'name': 'Bubbly', 'start_time': '1630', 'duration': 2},
                    ],
                    'Vivian': [
                        {'name': 'Jolly', 'start_time': '0930', 'duration': 2},
                        {'name': 'Bubbly', 'start_time': '1030', 'duration': 2},
                        {'name': 'Bubbly', 'start_time': '1130', 'duration': 2},
                        {'name': 'Tots', 'start_time': '1530', 'duration': 2},
                        {'name': 'Jolly', 'start_time': '1630', 'duration': 2},
                    ],
                    'Cheng Hong': [
                        {'name': 'Bubbly', 'start_time': '0930', 'duration': 2},
                        {'name': 'Flexi', 'start_time': '1130', 'duration': 2},
                        {'name': 'L1', 'start_time': '1230', 'duration': 3},
                        {'name': 'L1', 'start_time': '1400', 'duration': 3},
                        {'name': 'L1', 'start_time': '1530', 'duration': 3},
                    ],
                    'Francis': [
                        {'name': 'Lively', 'start_time': '0930', 'duration': 2},
                        {'name': 'Lively', 'start_time': '1030', 'duration': 2},
                        {'name': 'Lively', 'start_time': '1130', 'duration': 2},
                    ],
                    'Eugene': [
                        {'name': 'Flexi', 'start_time': '1530', 'duration': 2},
                    ]
                },
            }
        },
        'HG': {
            'coaches': ['Xiao You', 'Amirul', 'Brandon', 'Gwen', 'Eunicia'],
            'schedule': {
                'Tuesday': {
                    'Xiao You': [
                        {'name': 'Jolly', 'start_time': '0930', 'duration': 2},
                        {'name': 'Bubbly', 'start_time': '1030', 'duration': 2},
                        {'name': 'Bubbly', 'start_time': '1130', 'duration': 2},
                        {'name': 'Tots', 'start_time': '1530', 'duration': 2},
                        {'name': 'Jolly', 'start_time': '1630', 'duration': 2}
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