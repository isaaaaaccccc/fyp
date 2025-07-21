from flask_wtf import FlaskForm
from wtforms.fields import StringField, PasswordField, SubmitField, RadioField, IntegerField, SelectField, SelectMultipleField, BooleanField
from wtforms_sqlalchemy.fields import QuerySelectField, QuerySelectMultipleField

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
        get_label='name',
        allow_blank=True, blank_text='All', blank_value=''
    )

class CoachDetails(FlaskForm):
    editName = StringField(label='Name')
    editResidence = StringField(label='Area of Residence')
    editPosition = SelectField(
        label='Position',
        choices=[('Branch Manager', 'Branch Manager'), ('Admin cum coach', 'Admin cum coach'), ('Senior Coach', 'Senior Coach'), ('Junior Coach', 'Junior Coach'), ('Part time', 'Part time')],
    )
    submit = SubmitField('Save Changes')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # TODO TypeError: 'UnboundField' object is not callable
        # Assigned branches
        self.editBranch = []
        for branch in Branch.query.all():
            field_name = f'branch_{branch.abbrv}'
            field = BooleanField(label=branch.name)
            setattr(self, field_name, field)
            self.editBranch.append((field_name, branch))

        # Preferred levels
        self.editLevel = []
        for level in Level.query.all():
            field_name = f'level_{level.id}'
            field = BooleanField(label=level.name)
            setattr(self, field_name, field)
            self.editLevel.append((field_name, level))

        # Half/Full Offdays
        self.DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        for day in self.DAYS:
            for half in ['AM', 'PM']:
                field_name = f'editOffday_{day}_{half}'
                field = BooleanField(label=f'{day} {half}')
                setattr(self, field_name, field)
