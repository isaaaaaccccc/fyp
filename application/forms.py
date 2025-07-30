from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileRequired
from wtforms.fields import StringField, PasswordField, SubmitField, RadioField, IntegerField, FloatField, SelectField, SelectMultipleField, BooleanField, SubmitField, TextAreaField, TextAreaField
from wtforms_sqlalchemy.fields import QuerySelectField, QuerySelectMultipleField
from wtforms.validators import DataRequired, Length, NumberRange, Optional

from application import db
from .models import Branch, Coach, Level

# Optional
class CoachFilter(FlaskForm):
    name = StringField(label='Name')
    branch = QuerySelectField(
        label='Branch',
        query_factory=lambda: Branch.query.all(),
        get_label='name',
        allow_blank=True, blank_text='All', blank_value=''
    )
    position = SelectField(
        label='Position',
        choices=[('', 'All'), ('Branch Manager', 'Branch Manager'), ('Admin cum coach', 'Admin cum coach'), ('Senior Coach', 'Senior Coach'), ('Junior Coach', 'Junior Coach'), ('Part time', 'Part time')],
        default=''
    )
    level = QuerySelectField(
        label='Preferred Level',
        query_factory=lambda: Level.query.all(),
        get_label='alias',
        allow_blank=True, blank_text='All', blank_value=''
    )

def CoachDetails(*args, **kwargs):
    class DetailsForm(FlaskForm):
        editName = StringField(label='Name')
        editResidence = StringField(label='Area of Residence')
        editPosition = SelectField(
            label='Position',
            choices=[('Branch Manager', 'Branch Manager'), ('Admin cum coach', 'Admin cum coach'), ('Senior Coach', 'Senior Coach'), ('Junior Coach', 'Junior Coach'), ('Part time', 'Part time')],
        )
        submit = SubmitField('Save Changes')
    
    # Store field NAMES instead of field objects
    DetailsForm.editBranch_names = []
    DetailsForm.editLevel_names = []
    DetailsForm.editOffdays_names = []

    # Add branch fields
    for branch in Branch.query.all():
        field_name = f'editBranch_{branch.id}'
        field = BooleanField(label=branch.abbrv)
        setattr(DetailsForm, field_name, field)
        DetailsForm.editBranch_names.append(field_name)

    # Add level fields
    for level in Level.query.all():
        field_name = f'editLevel_{level.id}'
        field = BooleanField(label=level.alias)
        setattr(DetailsForm, field_name, field)
        DetailsForm.editLevel_names.append(field_name)

    # Add offday fields in tabular format
    DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    for half in ['AM', 'PM']:
        row = []
        for day in DAYS:
            field_name = f'editOffday_{day}_{half}'
            field = BooleanField(label=f'Off')
            setattr(DetailsForm, field_name, field)
            row.append(field_name)
        DetailsForm.editOffdays_names.append(row)

    # Add properties to access bound fields
    @property
    def editBranch(self):
        return [getattr(self, name) for name in self.editBranch_names]
    
    @property
    def editLevel(self):
        return [getattr(self, name) for name in self.editLevel_names]
    
    @property
    def editOffday(self):
        return [[getattr(self, name) for name in row] for row in self.editOffdays_names]
    
    # Bind properties to the class
    DetailsForm.editBranch = editBranch
    DetailsForm.editLevel = editLevel
    DetailsForm.editOffday = editOffday
    
    return DetailsForm(*args, **kwargs)

class AlgorithmConfig(FlaskForm):
    # Daily Limits
    weekend_daily_limit = IntegerField("Weekend Daily Limit", validators=[DataRequired(), NumberRange(min=0)], default=5)
    weekday_daily_limit = IntegerField("Weekday Daily Limit", validators=[DataRequired(), NumberRange(min=0)], default=3)
    weekend_daily_hours = IntegerField("Weekend Daily Hours (min)", validators=[DataRequired(), NumberRange(min=0)], default=480)
    weekday_daily_hours = IntegerField("Weekday Daily Hours (min)", validators=[DataRequired(), NumberRange(min=0)], default=240)

    # Weekly Limits by Coach Type
    full_time_weekly_max = IntegerField("Full-Time Weekly Max", validators=[DataRequired(), NumberRange(min=0)], default=25)
    part_time_weekly_max = IntegerField("Part-Time Weekly Max", validators=[DataRequired(), NumberRange(min=0)], default=15)
    manager_weekly_max = IntegerField("Manager Weekly Max", validators=[DataRequired(), NumberRange(min=0)], default=3)

    # Class Management Rules
    consecutive_limit = IntegerField("Max Consecutive Classes", validators=[DataRequired(), NumberRange(min=1)], default=3)
    min_break_minutes = IntegerField("Min Break Between Classes (min)", validators=[DataRequired(), NumberRange(min=0)], default=60)
    level_merge_distance = IntegerField("Max Level Merge Distance", validators=[DataRequired(), NumberRange(min=0)], default=1)
    min_merge_size = IntegerField("Min Merge Size", validators=[DataRequired(), NumberRange(min=0)], default=3)

    # Algorithm Behavior
    max_iterations = IntegerField("Max Iterations", validators=[DataRequired(), NumberRange(min=1)], default=60)
    use_all_slots_after = IntegerField("Use All Slots After Iteration", validators=[DataRequired(), NumberRange(min=0)], default=15)
    shuffle_interval = IntegerField("Shuffle Interval", validators=[DataRequired(), NumberRange(min=1)], default=5)
    max_assignment_attempts = IntegerField("Max Assignment Attempts", validators=[DataRequired(), NumberRange(min=1)], default=20)

    # Scoring Weights
    popular_slot_bonus = IntegerField("Popular Slot Bonus", validators=[DataRequired()], default=20)
    peak_hours_bonus = IntegerField("Peak Hours Bonus", validators=[DataRequired()], default=15)
    good_hours_bonus = IntegerField("Good Hours Bonus", validators=[DataRequired()], default=10)
    weekend_bias = IntegerField("Weekend Bias", default=5)
    weekday_bias = IntegerField("Weekday Bias", default=0)
    underutilized_coach_bonus = IntegerField("Underutilized Coach Bonus", default=8)
    capacity_multiplier = FloatField("Capacity Multiplier", validators=[DataRequired()], default=2.0)

    # Priority Weights
    advance_level_boost = FloatField("Advance Level Boost", validators=[DataRequired()], default=2.0)
    scarcity_weight = FloatField("Scarcity Weight", validators=[DataRequired()], default=0.5)
    complexity_weight = FloatField("Complexity Weight", validators=[DataRequired()], default=0.3)
    size_weight = FloatField("Size Weight", validators=[DataRequired()], default=0.2)

    pass

class DataUploadForm(FlaskForm):
    availability_file = FileField(
        'Availability CSV',
        validators=[FileAllowed(['csv'], 'CSV files only!')]
    )
    branch_config_file = FileField(
        'Branch Config CSV',
        validators=[FileAllowed(['csv'], 'CSV files only!')]
    )
    coaches_file = FileField(
        'Coaches CSV',
        validators=[FileAllowed(['csv'], 'CSV files only!')]
    )
    enrollment_file = FileField(
        'Enrollment CSV',
        validators=[FileAllowed(['csv'], 'CSV files only!')]
    )
    popular_timeslots_file = FileField(
        'Popular Timeslots CSV',
        validators=[FileAllowed(['csv'], 'CSV files only!')]
    )
    submit = SubmitField('Upload Files')
    
class BranchFilter(FlaskForm):
    """Form for filtering branches"""
    name = StringField('Branch Name', validators=[Optional()])
    max_classes = SelectField('Max Classes', choices=[
        ('', 'All'),
        ('4', '4 or fewer'),
        ('5', '5 or fewer'),
        ('6', '6 or fewer'),
        ('more', 'More than 6')
    ], validators=[Optional()])
    submit = SubmitField('Filter')

class BranchForm(FlaskForm):
    """Form for adding/editing branches"""
    name = StringField('Branch Name', validators=[
        DataRequired(),
        Length(min=2, max=32, message='Branch name must be between 2 and 32 characters')
    ])
    abbrv = StringField('Abbreviation', validators=[
        DataRequired(),
        Length(min=1, max=4, message='Abbreviation must be between 1 and 4 characters')
    ])
    max_classes = IntegerField('Maximum Classes Per Slot', validators=[
        DataRequired(),
        NumberRange(min=1, max=10, message='Maximum classes must be between 1 and 10')
    ])
    submit = SubmitField('Save')