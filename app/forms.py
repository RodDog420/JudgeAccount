from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, IntegerField, BooleanField, SelectField, DateField, SubmitField, \
    URLField, RadioField
from wtforms.validators import DataRequired, Length, NumberRange, ValidationError, Optional, URL, EqualTo
from urllib.parse import urlparse
from app.court_data import SHORTENED_URL_DOMAINS


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
    search_submit = SubmitField('Filter Search')


class ReviewForm(FlaskForm):
    judge_first_name = StringField('Judge First Name', validators=[DataRequired(), Length(min=1, max=30)])
    judge_last_name = StringField('Judge Last Name', validators=[DataRequired(), Length(min=1, max=50)])

    state = SelectField('State', choices=[], validators=[DataRequired()])
    court = SelectField('Court', choices=[], validators=[DataRequired()])
    city = StringField('City', validators=[DataRequired(), Length(min=1, max=100)])

    is_federal = BooleanField('Federal')
    is_retired = BooleanField('Retired')

    rating = RadioField('Rating',
                        choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5')],
                        coerce=int,
                        validators=[DataRequired()])

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

    def validate_url(self, url):
        """Comprehensive URL validation for security and anti-phishing"""
        # Parse URL and extract domain
        parsed_url = urlparse(url.data)
        domain = parsed_url.netloc.lower()

        # Remove www. prefix for consistent checking
        if domain.startswith('www.'):
            domain = domain[4:]

        # Check for shortened URLs
        if domain in SHORTENED_URL_DOMAINS:
            raise ValidationError('Shortened URLs not allowed - please provide the direct link')

        # Anti-phishing: Check for suspicious domain patterns
        self._check_phishing_patterns(domain)

        # OWASP/RFC 3986 security checks
        self._check_url_security(parsed_url, url.data)

    def _check_phishing_patterns(self, domain):
        """Detect anti-phishing patterns in domain names"""
        # Define legitimate domains to check against
        legitimate_domains = {
            'google', 'facebook', 'twitter', 'microsoft', 'apple', 'amazon', 'netflix',
            'paypal', 'ebay', 'instagram', 'linkedin', 'youtube', 'reddit', 'wikipedia',
            'nytimes', 'washingtonpost', 'cnn', 'bbc', 'reuters', 'bloomberg', 'wsj'
        }

        # Character substitution mapping (what attackers use -> legitimate character)
        substitutions = {
            '0': 'o', '1': 'l', '3': 'e', '4': 'a', '5': 's', '7': 't',
            '@': 'a', '$': 's', '!': 'i', '6': 'g', '8': 'b'
        }

        # Check for character substitution attacks
        for legit_domain in legitimate_domains:
            if self._is_suspicious_variant(domain, legit_domain, substitutions):
                raise ValidationError('URL appears to be from a suspicious domain')

        # Check for suspicious TLD combinations with brand names
        suspicious_tlds = {'.tk', '.ml', '.ga', '.cf', '.top', '.click', '.download'}
        domain_parts = domain.split('.')
        if len(domain_parts) >= 2:
            tld = '.' + domain_parts[-1]
            if tld in suspicious_tlds:
                for legit_domain in legitimate_domains:
                    if legit_domain in domain.lower():
                        raise ValidationError('URL appears to be from a suspicious domain')

    def _is_suspicious_variant(self, test_domain, legit_domain, substitutions):
        """Check if test_domain is a suspicious variant of legit_domain"""
        # Convert suspicious characters back to legitimate ones
        normalized = test_domain
        for suspicious, legitimate in substitutions.items():
            normalized = normalized.replace(suspicious, legitimate)

        # Check if normalized domain closely matches legitimate domain
        # Allow for minor variations but catch obvious spoofs
        if legit_domain in normalized and len(normalized) <= len(legit_domain) + 3:
            # Additional checks to avoid false positives
            if normalized != legit_domain and test_domain != legit_domain:
                return True
        return False

    def _check_url_security(self, parsed_url, original_url):
        """OWASP and RFC 3986 security validation"""
        # Check for valid scheme
        if parsed_url.scheme not in ['http', 'https']:
            raise ValidationError('URL format is invalid')

        # Check for malformed domains
        if not parsed_url.netloc:
            raise ValidationError('URL format is invalid')

        # Check for dangerous characters in URL
        dangerous_chars = ['<', '>', '"', "'", '&', ';', '(', ')', '{', '}']
        if any(char in original_url for char in dangerous_chars):
            raise ValidationError('URL format is invalid')

        # Check for excessively long domains (potential buffer overflow attempts)
        if len(parsed_url.netloc) > 253:  # RFC limit
            raise ValidationError('URL format is invalid')

        # Check for multiple subdomains (common in phishing)
        domain_parts = parsed_url.netloc.split('.')
        if len(domain_parts) > 5:  # Allow some flexibility but catch excessive subdomains
            raise ValidationError('URL appears to be from a suspicious domain')


class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=64)])
    email = StringField('Email', validators=[DataRequired(), Length(max=120)])
    password = StringField('Password', validators=[DataRequired(), Length(min=8)])
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
    search_content = StringField('Search Review & Media Link Summaries', validators=[Length(max=200)])
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
                               render_kw={
                                   "placeholder": "Internal notes about this user (warnings, patterns, etc.)..."})
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


class ResetPasswordRequestForm(FlaskForm):
    """Form for requesting a password reset email"""
    email = StringField('Email Address', validators=[DataRequired(), Length(max=120)])
    submit = SubmitField('Send Reset Link')


class ResetPasswordForm(FlaskForm):
    """Form for setting a new password via reset link"""
    password = StringField('New Password', validators=[DataRequired(), Length(min=8)])
    password2 = StringField('Confirm New Password', validators=[DataRequired(), EqualTo('password', message='Passwords must match.')])
    submit = SubmitField('Reset Password')