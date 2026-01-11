from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, IntegerField, BooleanField, SelectField, DateField, SubmitField, URLField
from wtforms.validators import DataRequired, Length, NumberRange, ValidationError, Optional, URL


class SearchForm(FlaskForm):
    search_query = StringField('Search Judges', validators=[Length(max=100)])
    filter_state = SelectField('Filter by State', choices=[('', 'All States')])
    filter_federal = SelectField('Judge Type', choices=[
        ('', 'All Judges'),
        ('federal', 'Federal Court Judges'),
        ('state', 'State Court Judges')
    ])
    filter_retired = SelectField('Retired Status', choices=[
        ('', 'All Judges'),
        ('active', 'Active Judges Only'),
        ('retired', 'Retired Judges Only')
    ])
    filter_content = SelectField('Content Filter', choices=[
        ('', 'All Judges'),
        ('has_reviews', 'Judges with Reviews'),
        ('has_media', 'Judges with Media Links'),
        ('has_both', 'Judges with Both')
    ])
    sort_by = SelectField('Sort By', choices=[
        ('name_asc', 'Name (A-Z)'),
        ('name_desc', 'Name (Z-A)'),
        ('rating_desc', 'Rating (High to Low)'),
        ('rating_asc', 'Rating (Low to High)'),
        ('reviews_desc', 'Most Reviews'),
        ('reviews_asc', 'Fewest Reviews'),
        ('media_desc', 'Most Media Links'),
        ('documented_desc', 'Most Documented')
    ])
    search_submit = SubmitField('Search & Filter')

class ReviewForm(FlaskForm):
    judge_first_name = StringField('Judge First Name', validators=[DataRequired(), Length(min=1, max=30)])
    judge_last_name = StringField('Judge Last Name', validators=[DataRequired(), Length(min=1, max=50)])
    
    state = SelectField('State', choices=[], validators=[DataRequired()])
    court = SelectField('Court', choices=[], validators=[DataRequired()])
    city = StringField('City', validators=[DataRequired(), Length(min=1, max=100)])
    
    is_federal = BooleanField('Federal Judge')
    is_retired = BooleanField('Retired Judge')
    
    rating = IntegerField('Rating (1-5)', validators=[DataRequired(), NumberRange(min=1, max=5)])
    
    fairness_concern = BooleanField('Fairness Concern')
    bias_concern = BooleanField('Bias Concern')
    temperament_concern = BooleanField('Temperament Concern')
    
    review_text = TextAreaField('Your Review', validators=[DataRequired(), Length(min=10)])
    court_date = DateField('Date of Court Appearance', validators=[DataRequired()])
    
    submit = SubmitField('Submit Review')


class MediaLinkForm(FlaskForm):
    # Judge Information
    judge_first_name = StringField('Judge First Name', validators=[DataRequired(), Length(min=1, max=30)])
    judge_last_name = StringField('Judge Last Name', validators=[DataRequired(), Length(min=1, max=50)])
    
    state = SelectField('State', choices=[], validators=[DataRequired()])
    court = SelectField('Court', choices=[], validators=[DataRequired()])
    city = StringField('City', validators=[DataRequired(), Length(min=1, max=100)])
    
    is_federal = BooleanField('Federal Judge')
    is_retired = BooleanField('Retired Judge')
    
    # Media Link Information
    headline = StringField('Article/Report Headline', validators=[DataRequired(), Length(min=5, max=500)])
    news_source = StringField('News Source', validators=[DataRequired(), Length(min=2, max=200)])
    url = URLField('URL', validators=[DataRequired(), URL(), Length(max=1000)])
    publication_date = DateField('Publication Date', validators=[DataRequired()])
    summary = TextAreaField('Brief Summary', validators=[DataRequired(), Length(min=20, max=2000)])
    
    submit = SubmitField('Submit Media Link')
    

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=64)])
    email = StringField('Email', validators=[DataRequired(), Length(max=120)])
    password = StringField('Password', validators=[DataRequired(), Length(min=6)])
    password2 = StringField('Confirm Password', validators=[DataRequired(), Length(min=6)])
    submit = SubmitField('Register')
    
    def validate_username(self, username):
        from app.models import User
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Username already taken. Please choose a different one.')
    
    def validate_email(self, email):
        from app.models import User
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Email already registered. Please use a different one.')
    
    def validate_password2(self, password2):
        if self.password.data != password2.data:
            raise ValidationError('Passwords must match.')


class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = StringField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Log In')
    

class AdminSearchForm(FlaskForm):
    search_judge = StringField('Search Judge Name', validators=[Length(max=100)])
    search_content = StringField('Search Review Content', validators=[Length(max=200)])
    filter_username = StringField('Filter by Username', validators=[Length(max=64)])
    filter_rating = SelectField('Rating', choices=[
        ('', 'All Ratings'),
        ('1', '1 Star'),
        ('2', '2 Stars'),
        ('3', '3 Stars'),
        ('4', '4 Stars'),
        ('5', '5 Stars')
    ])
    filter_concerns = SelectField('Concerns', choices=[
        ('', 'All Reviews'),
        ('any', 'Any Concern Flagged'),
        ('fairness', 'Fairness Concern'),
        ('bias', 'Bias Concern'),
        ('temperament', 'Temperament Concern')
    ])
    sort_by = SelectField('Sort By', choices=[
        ('newest', 'Newest First'),
        ('oldest', 'Oldest First'),
        ('rating_high', 'Rating: High to Low'),
        ('rating_low', 'Rating: Low to High')
    ])
    admin_submit = SubmitField('Search & Filter')


class AdminUserSearchForm(FlaskForm):
    """Form for searching and filtering users in admin panel"""
    search = StringField('Search Users', validators=[Length(max=100)])
    status = SelectField('Status', choices=[
        ('all', 'All Users'),
        ('active', 'Active Users'),
        ('banned', 'Banned Users'),
        ('admin', 'Administrators')
    ])
    sort = SelectField('Sort By', choices=[
        ('username_asc', 'Username (A-Z)'),
        ('username_desc', 'Username (Z-A)'),
        ('email_asc', 'Email (A-Z)'),
        ('join_date_desc', 'Newest First'),
        ('join_date_asc', 'Oldest First'),
        ('reviews_desc', 'Most Reviews'),
        ('media_desc', 'Most Media Links'),
        ('last_activity_desc', 'Recently Active')
    ])
    submit = SubmitField('Filter')


class BanUserForm(FlaskForm):
    """Form for banning a user"""
    ban_reason = TextAreaField('Reason for Ban',
                              validators=[DataRequired(), Length(min=10, max=500)],
                              render_kw={"placeholder": "Explain why this user is being banned..."})
    submit = SubmitField('Ban User')


class DeleteUserForm(FlaskForm):
    """Form for deleting a user"""
    delete_reason = TextAreaField('Reason for Deletion',
                                 validators=[DataRequired(), Length(min=10, max=500)],
                                 render_kw={"placeholder": "Explain why this user is being deleted..."})
    confirm_delete = BooleanField('I understand this action is permanent',
                                 validators=[DataRequired()])
    submit = SubmitField('Delete User Permanently')


class AdminNoteForm(FlaskForm):
    """Form for adding/editing admin notes on a user"""
    admin_note = TextAreaField('Admin Notes',
                              validators=[Optional(), Length(max=2000)],
                              render_kw={"placeholder": "Internal notes about this user (warnings, patterns, etc.)..."})
    submit = SubmitField('Save Notes')


class BulkActionForm(FlaskForm):
    """Form for bulk actions on users"""
    bulk_action = SelectField('Action', choices=[
        ('', 'Select Action'),
        ('ban', 'Ban Selected Users'),
        ('delete', 'Delete Selected Users')
    ], validators=[DataRequired()])
    bulk_reason = TextAreaField('Reason',
                               validators=[DataRequired(), Length(min=10, max=500)],
                               render_kw={"placeholder": "Reason for this bulk action..."})
    submit = SubmitField('Execute Bulk Action')


class FlagContentForm(FlaskForm):
    """Form for flagging inappropriate content"""
    flag_type = SelectField('Reason for Report', choices=[
        ('spam', 'Spam'),
        ('inappropriate', 'Inappropriate Content'),
        ('harassment', 'Harassment'),
        ('off-topic', 'Off-Topic'),
        ('misinformation', 'Misinformation'),
        ('conflict', 'Conflict of Interest'),
        ('other', 'Other')
    ], validators=[DataRequired()])
    description = TextAreaField('Additional Details (Optional)',
                               validators=[Optional(), Length(max=500)],
                               render_kw={"placeholder": "Provide more context about why you're reporting this..."})
    submit = SubmitField('Submit Report')


