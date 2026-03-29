from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from wtforms.validators import ValidationError
from app import db, limiter
from app.models import Judge, Review, MediaLink, User, ContentFlag
from app.forms import ReviewForm, MediaLinkForm
from app.court_data import STATES, COURTS_BY_STATE

bp = Blueprint('main', __name__)


@bp.route('/health')
def health():
    """Health check endpoint for Render and uptime monitoring."""
    try:
        db.session.execute(db.text('SELECT 1'))
        return {'status': 'ok', 'database': 'ok'}, 200
    except Exception as e:
        current_app.logger.error(f"Health check failed: {e}")
        return {'status': 'error', 'database': 'unavailable'}, 500


@bp.route('/index', methods=['GET', 'POST'])
def index():
    from app.forms import SearchForm
    form = SearchForm()

    # Populate state filter choices
    form.filter_state.choices = [('', 'All States')] + STATES

    # Start with base query
    query = Judge.query

    # Track active filters for display
    active_filters = []

    if form.validate_on_submit():
        # Apply search filter
        if form.search_query.data:
            search_query = form.search_query.data
            query = query.filter(
                db.or_(
                    Judge.first_name.ilike(f'%{search_query}%'),
                    Judge.last_name.ilike(f'%{search_query}%'),
                    Judge.court.ilike(f'%{search_query}%'),
                    Judge.city.ilike(f'%{search_query}%'),
                    Judge.state.ilike(f'%{search_query}%'),
                    db.func.concat(Judge.first_name, ' ', Judge.last_name).ilike(f'%{search_query}%')
                )
            )
            active_filters.append(('search', f'Search: "{search_query}"'))

        # Apply state filter
        if form.filter_state.data:
            query = query.filter(Judge.state == form.filter_state.data)
            active_filters.append(('state', f'State: {form.filter_state.data}'))

        # Apply federal filter
        if form.filter_federal.data == 'federal':
            query = query.filter(Judge.is_federal == True)
            active_filters.append(('federal', 'Federal Judges'))
        elif form.filter_federal.data == 'state':
            query = query.filter(Judge.is_federal == False)
            active_filters.append(('federal', 'State Judges'))

        # Apply retired filter
        if form.filter_retired.data == 'active':
            query = query.filter(Judge.is_retired == False)
            active_filters.append(('retired', 'Active Only'))
        elif form.filter_retired.data == 'retired':
            query = query.filter(Judge.is_retired == True)
            active_filters.append(('retired', 'Retired Only'))

        # Get results with cap
        judges = query.limit(500).all()

        # Apply content filter (must be done after getting results)
        if form.filter_content.data == 'has_reviews':
            judges = [j for j in judges if j.review_count() > 0]
            active_filters.append(('content', 'Has Reviews'))
        elif form.filter_content.data == 'has_media':
            judges = [j for j in judges if j.media_link_count() > 0]
            active_filters.append(('content', 'Has Media'))
        elif form.filter_content.data == 'has_both':
            judges = [j for j in judges if j.review_count() > 0 and j.media_link_count() > 0]
            active_filters.append(('content', 'Has Reviews & Media'))

        # Apply sorting
        if form.sort_by.data == 'name_asc':
            judges.sort(key=lambda j: (j.last_name.lower(), j.first_name.lower()))
        elif form.sort_by.data == 'name_desc':
            judges.sort(key=lambda j: (j.last_name.lower(), j.first_name.lower()), reverse=True)
        elif form.sort_by.data == 'rating_desc':
            judges.sort(key=lambda j: j.average_rating(), reverse=True)
        elif form.sort_by.data == 'rating_asc':
            judges.sort(key=lambda j: j.average_rating())
        elif form.sort_by.data == 'reviews_desc':
            judges.sort(key=lambda j: j.review_count(), reverse=True)
        elif form.sort_by.data == 'reviews_asc':
            judges.sort(key=lambda j: j.review_count())
        elif form.sort_by.data == 'media_desc':
            judges.sort(key=lambda j: j.media_link_count(), reverse=True)
        elif form.sort_by.data == 'documented_desc':
            judges.sort(key=lambda j: (j.review_count() + j.media_link_count()), reverse=True)
    else:
        judges = query.limit(500).all()
        judges.sort(key=lambda j: (j.last_name.lower(), j.first_name.lower()))

    return render_template('index.html', judges=judges, form=form, active_filters=active_filters)


@bp.route('/judge/<int:judge_id>')
def judge(judge_id):
    judge = Judge.query.get_or_404(judge_id)
    reviews = judge.reviews.limit(200).all()
    media_links = judge.media_links.limit(200).all() if hasattr(judge.media_links, 'limit') else judge.media_links[:200]

    # Check for pending flags on each review
    for review in reviews:
        pending_flag = ContentFlag.query.filter_by(
            review_id=review.id,
            is_resolved=False
        ).first()
        review.has_pending_flag = pending_flag is not None

    # Check for pending flags on each media link
    for media_link in media_links:
        pending_flag = ContentFlag.query.filter_by(
            media_link_id=media_link.id,
            is_resolved=False
        ).first()
        media_link.has_pending_flag = pending_flag is not None

    return render_template('judge.html', judge=judge, reviews=reviews, media_links=media_links)


@bp.route('/submit_review', methods=['GET', 'POST'])
@login_required
@limiter.limit("10 per hour")
def submit_review():
    form = ReviewForm()

    form.state.choices = [('', 'Select a state...')] + STATES
    form.court.choices = []  # Will be populated by JavaScript

    # Check if judge_id is provided in URL (GET) or hidden field (POST)
    judge_id = request.args.get('judge_id', type=int) or request.form.get('prefilled_judge_id', type=int)
    prefilled_judge = None

    if judge_id:
        prefilled_judge = Judge.query.get(judge_id)
        if prefilled_judge and request.method == 'GET':
            form.judge_first_name.data = prefilled_judge.first_name
            form.judge_last_name.data = prefilled_judge.last_name
            form.state.data = prefilled_judge.state
            form.court.data = prefilled_judge.court
            form.city.data = prefilled_judge.city
            form.is_federal.data = prefilled_judge.is_federal
            form.is_retired.data = prefilled_judge.is_retired

    # Populate court choices dynamically
    if form.state.data or (prefilled_judge and prefilled_judge.state):
        state = form.state.data or prefilled_judge.state
        form.court.choices = COURTS_BY_STATE.get(state, [])

    if request.method == 'POST':
        if prefilled_judge:
            # PREFILLED JUDGE PATH: Custom validation for review fields
            validation_errors = []

            # Validate review fields
            if not form.rating.data:
                validation_errors.append("Rating is required.")

            if not form.court_date.data:
                validation_errors.append("Date of Court Appearance is required.")
            else:
                # Check if court date is in the future
                from datetime import date
                if form.court_date.data > date.today():
                    validation_errors.append(
                        "Date of Court Appearance cannot be in the future. Please enter the actual date of your court appearance.")

            if not form.review_text.data or not form.review_text.data.strip():
                validation_errors.append("Your Review is required.")
            elif len(form.review_text.data) < 10:
                validation_errors.append("Your Review must be at least 10 characters.")
            elif len(form.review_text.data) > 5000:
                validation_errors.append("Your Review must be 5000 characters or fewer.")

            # If validation passed, use prefilled judge
            if not validation_errors:
                judge = prefilled_judge
            else:
                # Show validation errors and preserve prefilled judge data
                for error in validation_errors:
                    flash(error, 'error')  # Red banner messages
                # Repopulate judge fields from prefilled_judge to preserve data
                form.judge_first_name.data = prefilled_judge.first_name
                form.judge_last_name.data = prefilled_judge.last_name
                form.state.data = prefilled_judge.state
                form.court.data = prefilled_judge.court
                form.city.data = prefilled_judge.city
                form.is_federal.data = prefilled_judge.is_federal
                form.is_retired.data = prefilled_judge.is_retired
                # Keep court choices populated for prefilled judge
                form.court.choices = COURTS_BY_STATE.get(prefilled_judge.state, [])
                return render_template('submit_review.html', form=form, courts_by_state=COURTS_BY_STATE,
                                       prefilled_judge=prefilled_judge)

        else:
            # NEW JUDGE PATH: Custom validation with red banner messages (consistent UX)
            validation_errors = []

            # Validate judge information fields
            if not form.judge_first_name.data or not form.judge_first_name.data.strip():
                validation_errors.append("Judge First Name is required.")
            elif len(form.judge_first_name.data) > 30:
                validation_errors.append("Judge First Name must be 30 characters or fewer.")

            if not form.judge_last_name.data or not form.judge_last_name.data.strip():
                validation_errors.append("Judge Last Name is required.")
            elif len(form.judge_last_name.data) > 50:
                validation_errors.append("Judge Last Name must be 50 characters or fewer.")

            if not form.state.data:
                validation_errors.append("State is required.")

            if not form.court.data:
                validation_errors.append("Court is required.")

            if not form.city.data or not form.city.data.strip():
                validation_errors.append("City is required.")
            elif len(form.city.data) > 100:
                validation_errors.append("City must be 100 characters or fewer.")

            # Validate review fields
            if not form.rating.data:
                validation_errors.append("Rating is required.")

            if not form.court_date.data:
                validation_errors.append("Date of Court Appearance is required.")
            else:
                # Check if court date is in the future
                from datetime import date
                if form.court_date.data > date.today():
                    validation_errors.append(
                        "Date of Court Appearance cannot be in the future. Please enter the actual date of your court appearance.")

            if not form.review_text.data or not form.review_text.data.strip():
                validation_errors.append("Your Review is required.")
            elif len(form.review_text.data) < 10:
                validation_errors.append("Your Review must be at least 10 characters.")
            elif len(form.review_text.data) > 5000:
                validation_errors.append("Your Review must be 5000 characters or fewer.")

            # If validation passed, create/find judge and proceed
            if not validation_errors:
                judge = Judge.query.filter_by(
                    first_name=form.judge_first_name.data,
                    last_name=form.judge_last_name.data,
                    court=form.court.data
                ).first()

                if not judge:
                    judge = Judge(
                        first_name=form.judge_first_name.data,
                        last_name=form.judge_last_name.data,
                        court=form.court.data,
                        city=form.city.data,
                        state=form.state.data,
                        is_federal=form.is_federal.data,
                        is_retired=form.is_retired.data
                    )
                    db.session.add(judge)
                    db.session.commit()
            else:
                # Show validation errors using flash banner messages (consistent with media links)
                for error in validation_errors:
                    flash(error, 'error')  # Red banner messages at top
                return render_template('submit_review.html', form=form, courts_by_state=COURTS_BY_STATE,
                                       prefilled_judge=prefilled_judge)

        # Check if user has already reviewed this judge
        if current_user.is_authenticated:
            existing_review = Review.query.filter_by(
                judge_id=judge.id,
                user_id=current_user.id
            ).first()

            if existing_review:
                flash('You have already reviewed this judge. You can edit your existing review from your dashboard.')
                return redirect(url_for('main.judge', judge_id=judge.id))

        review = Review(
            judge_id=judge.id,
            user_id=current_user.id if current_user.is_authenticated else None,
            rating=form.rating.data,
            fairness_concern=form.fairness_concern.data,
            bias_concern=form.bias_concern.data,
            temperament_concern=form.temperament_concern.data,
            review_text=form.review_text.data,
            court_date=form.court_date.data
        )
        db.session.add(review)
        db.session.commit()

        # Send admin notification for new review
        try:
            from app.email_utils import send_admin_new_content_notification
            send_admin_new_content_notification(review, judge)
        except Exception as e:
            current_app.logger.error(f"Failed to send new review notification: {str(e)}")

        flash('Review submitted successfully!')
        return redirect(url_for('main.judge', judge_id=judge.id))

    return render_template('submit_review.html', form=form, courts_by_state=COURTS_BY_STATE,
                           prefilled_judge=prefilled_judge)


@bp.route('/submit_media_link', methods=['GET', 'POST'])
@login_required
@limiter.limit("10 per hour")
def submit_media_link():
    form = MediaLinkForm()

    form.state.choices = [('', 'Select a state...')] + STATES
    form.court.choices = []  # Will be populated by JavaScript

    # Check if judge_id is provided in URL (GET) or hidden field (POST)
    judge_id = request.args.get('judge_id', type=int) or request.form.get('prefilled_judge_id', type=int)
    prefilled_judge = None

    if judge_id:
        prefilled_judge = Judge.query.get(judge_id)
        if prefilled_judge and request.method == 'GET':
            form.judge_first_name.data = prefilled_judge.first_name
            form.judge_last_name.data = prefilled_judge.last_name
            form.state.data = prefilled_judge.state
            form.court.data = prefilled_judge.court
            form.city.data = prefilled_judge.city
            form.is_federal.data = prefilled_judge.is_federal
            form.is_retired.data = prefilled_judge.is_retired

    # Populate court choices dynamically
    if form.state.data or (prefilled_judge and prefilled_judge.state):
        state = form.state.data or prefilled_judge.state
        form.court.choices = COURTS_BY_STATE.get(state, [])

    if request.method == 'POST':
        if prefilled_judge:
            # PREFILLED JUDGE PATH: Custom validation to avoid disabled field issues
            validation_errors = []

            # Manually validate required media link fields
            if not form.headline.data or not form.headline.data.strip():
                validation_errors.append("Article/Report Headline is required.")
            elif len(form.headline.data) < 5:
                validation_errors.append("Article/Report Headline must be at least 5 characters.")

            if not form.news_source.data or not form.news_source.data.strip():
                validation_errors.append("News Source is required.")
            elif len(form.news_source.data) < 2:
                validation_errors.append("News Source must be at least 2 characters.")

            if not form.url.data or not form.url.data.strip():
                validation_errors.append("URL is required.")

            if not form.publication_date.data:
                validation_errors.append("Publication Date is required.")
            else:
                # Check if publication date is in the future
                from datetime import date
                if form.publication_date.data > date.today():
                    validation_errors.append(
                        "Publication Date cannot be in the future. Please enter the actual date the article was published.")

            if not form.summary.data or not form.summary.data.strip():
                validation_errors.append("Brief Summary is required.")
            elif len(form.summary.data) < 20:
                validation_errors.append("Brief Summary must be at least 20 characters.")

            # Run URL validation directly if URL field has data
            if form.url.data and form.url.data.strip():
                try:
                    form.validate_url(form.url)
                except ValidationError as e:
                    validation_errors.append(str(e))

            # If validation passed, use prefilled judge
            if not validation_errors:
                judge = prefilled_judge
            else:
                # Show validation errors and preserve prefilled judge data
                for error in validation_errors:
                    flash(error, 'error')  # Use 'error' category for red styling
                # Repopulate judge fields from prefilled_judge to preserve data
                form.judge_first_name.data = prefilled_judge.first_name
                form.judge_last_name.data = prefilled_judge.last_name
                form.state.data = prefilled_judge.state
                form.court.data = prefilled_judge.court
                form.city.data = prefilled_judge.city
                form.is_federal.data = prefilled_judge.is_federal
                form.is_retired.data = prefilled_judge.is_retired
                # Keep court choices populated for prefilled judge
                form.court.choices = COURTS_BY_STATE.get(prefilled_judge.state, [])
                return render_template('submit_media.html', form=form, courts_by_state=COURTS_BY_STATE,
                                       prefilled_judge=prefilled_judge)

        else:
            # NEW JUDGE PATH: Custom validation to use flash banner messages (consistent UX)
            validation_errors = []

            # Validate judge information fields
            if not form.judge_first_name.data or not form.judge_first_name.data.strip():
                validation_errors.append("Judge First Name is required.")
            elif len(form.judge_first_name.data) > 30:
                validation_errors.append("Judge First Name must be 30 characters or fewer.")

            if not form.judge_last_name.data or not form.judge_last_name.data.strip():
                validation_errors.append("Judge Last Name is required.")
            elif len(form.judge_last_name.data) > 50:
                validation_errors.append("Judge Last Name must be 50 characters or fewer.")

            if not form.state.data:
                validation_errors.append("State is required.")

            if not form.court.data:
                validation_errors.append("Court is required.")

            if not form.city.data or not form.city.data.strip():
                validation_errors.append("City is required.")
            elif len(form.city.data) > 100:
                validation_errors.append("City must be 100 characters or fewer.")

            # Validate media link fields
            if not form.headline.data or not form.headline.data.strip():
                validation_errors.append("Article/Report Headline is required.")
            elif len(form.headline.data) < 5:
                validation_errors.append("Article/Report Headline must be at least 5 characters.")
            elif len(form.headline.data) > 500:
                validation_errors.append("Article/Report Headline must be 500 characters or fewer.")

            if not form.news_source.data or not form.news_source.data.strip():
                validation_errors.append("News Source is required.")
            elif len(form.news_source.data) < 2:
                validation_errors.append("News Source must be at least 2 characters.")
            elif len(form.news_source.data) > 200:
                validation_errors.append("News Source must be 200 characters or fewer.")

            if not form.url.data or not form.url.data.strip():
                validation_errors.append("URL is required.")
            elif len(form.url.data) > 1000:
                validation_errors.append("URL must be 1000 characters or fewer.")

            if not form.publication_date.data:
                validation_errors.append("Publication Date is required.")
            else:
                # Check if publication date is in the future
                from datetime import date
                if form.publication_date.data > date.today():
                    validation_errors.append(
                        "Publication Date cannot be in the future. Please enter the actual date the article was published.")

            if not form.summary.data or not form.summary.data.strip():
                validation_errors.append("Brief Summary is required.")
            elif len(form.summary.data) < 20:
                validation_errors.append("Brief Summary must be at least 20 characters.")
            elif len(form.summary.data) > 2000:
                validation_errors.append("Brief Summary must be 2000 characters or fewer.")

            # Run URL validation directly if URL field has data and basic validation passed
            if form.url.data and form.url.data.strip() and not any("URL" in error for error in validation_errors):
                try:
                    # Run basic URL format validation first
                    from wtforms.validators import URL
                    url_validator = URL()
                    url_validator(form, form.url)

                    # Then run our custom security validation
                    form.validate_url(form.url)
                except ValidationError as e:
                    validation_errors.append(str(e))

            # If validation passed, create/find judge and proceed
            if not validation_errors:
                judge = Judge.query.filter_by(
                    first_name=form.judge_first_name.data,
                    last_name=form.judge_last_name.data,
                    court=form.court.data
                ).first()

                if not judge:
                    judge = Judge(
                        first_name=form.judge_first_name.data,
                        last_name=form.judge_last_name.data,
                        court=form.court.data,
                        city=form.city.data,
                        state=form.state.data,
                        is_federal=form.is_federal.data,
                        is_retired=form.is_retired.data
                    )
                    db.session.add(judge)
                    db.session.commit()
            else:
                # Show validation errors using flash banner messages (consistent with prefilled judges)
                for error in validation_errors:
                    flash(error, 'error')  # Red banner messages at top
                return render_template('submit_media.html', form=form, courts_by_state=COURTS_BY_STATE,
                                       prefilled_judge=prefilled_judge)

        # Check for duplicate URL for this judge
        existing_link = MediaLink.query.filter_by(
            judge_id=judge.id,
            url=form.url.data
        ).first()

        if existing_link:
            flash('This URL has already been submitted for this judge.')
            return redirect(url_for('main.judge', judge_id=judge.id))

        # Create media link
        media_link = MediaLink(
            judge_id=judge.id,
            user_id=current_user.id if current_user.is_authenticated else None,
            headline=form.headline.data,
            news_source=form.news_source.data,
            url=form.url.data,
            publication_date=form.publication_date.data,
            summary=form.summary.data,
            is_verified=False  # Requires admin approval
        )
        db.session.add(media_link)
        db.session.commit()

        # Send admin notification for new media link
        try:
            from app.email_utils import send_admin_new_content_notification
            send_admin_new_content_notification(media_link, judge)
        except Exception as e:
            current_app.logger.error(f"Failed to send new media link notification: {str(e)}")

        flash(
            'Media link submitted successfully! It is pending verification and will appear once approved by our moderation team.')
        return redirect(url_for('main.judge', judge_id=judge.id))

    return render_template('submit_media.html', form=form, courts_by_state=COURTS_BY_STATE,
                           prefilled_judge=prefilled_judge)


@bp.route('/admin/notify_user_issue/<content_type>/<int:content_id>', methods=['POST'])
@login_required
def admin_notify_user_issue(content_type, content_id):
    """Admin route to send issue notifications to users about their content"""
    if not current_user.is_admin:
        from flask import abort
        abort(403)

    # Get content and related objects
    if content_type == 'review':
        content = Review.query.get_or_404(content_id)
    else:
        content = MediaLink.query.get_or_404(content_id)

    judge = Judge.query.get_or_404(content.judge_id)
    user = User.query.get_or_404(content.user_id)

    # Get form data from admin panel
    issue_type = request.form.get('issue_type', 'Content requires clarification')
    admin_message = request.form.get('admin_message', 'Please review and update your submission.')

    try:
        from app.email_utils import send_user_content_issue_notification
        send_user_content_issue_notification(user, content, judge, issue_type, admin_message)
        flash(f'Issue notification sent to {user.username}', 'success')
    except Exception as e:
        flash('Failed to send notification to user', 'error')
        current_app.logger.error(f"Failed to send user notification: {str(e)}")

    return redirect(url_for('auth.admin_dashboard'))


@bp.route('/guidelines')
def guidelines():
    return render_template('guidelines.html')


@bp.route('/privacy')
def privacy_policy():
    return render_template('privacy_policy.html')


@bp.route('/terms')
def terms_of_service():
    return render_template('terms_of_service.html')


@bp.route('/contact')
def contact():
    return render_template('contact.html')


@bp.route('/sitemap')
def sitemap():
    return render_template('sitemap.html')


@bp.route('/support')
def support():
    return render_template('support.html')


@bp.route('/')
def home():
    """About/Landing page explaining the platform"""
    return render_template('about.html')


@bp.route('/about')
def about():
    """Redirect old about URL to canonical homepage"""
    return redirect(url_for("main.home"), code=301)


@bp.route('/robots.txt')
def robots():
    from flask import send_from_directory
    return send_from_directory('static', 'robots.txt', mimetype='text/plain')


@bp.route('/sitemap.xml')
def sitemap_xml():
    from flask import Response
    from datetime import datetime

    # Get all judges for individual pages — capped to prevent memory spike
    judges = Judge.query.limit(5000).all()

    # Static pages
    pages = [
        {'loc': url_for('main.about', _external=True), 'priority': '1.0', 'changefreq': 'monthly'},
        {'loc': url_for('main.index', _external=True), 'priority': '0.9', 'changefreq': 'daily'},
        {'loc': url_for('main.guidelines', _external=True), 'priority': '0.8', 'changefreq': 'monthly'},
        {'loc': url_for('main.submit_review', _external=True), 'priority': '0.9', 'changefreq': 'monthly'},
        {'loc': url_for('main.submit_media_link', _external=True), 'priority': '0.9', 'changefreq': 'monthly'},
        {'loc': url_for('main.privacy_policy', _external=True), 'priority': '0.3', 'changefreq': 'yearly'},
        {'loc': url_for('main.terms_of_service', _external=True), 'priority': '0.3', 'changefreq': 'yearly'},
        {'loc': url_for('main.contact', _external=True), 'priority': '0.5', 'changefreq': 'monthly'},
        {'loc': url_for('main.sitemap', _external=True), 'priority': '0.4', 'changefreq': 'monthly'},
        {'loc': url_for('main.support', _external=True), 'priority': '0.6', 'changefreq': 'monthly'},
        {'loc': url_for('main.recall_judge_parisien', _external=True), 'priority': '0.9', 'changefreq': 'monthly'},
    ]

    # Add judge pages
    for judge in judges:
        pages.append({
            'loc': url_for('main.judge', judge_id=judge.id, _external=True),
            'priority': '0.7',
            'changefreq': 'weekly'
        })

    sitemap_xml = render_template('sitemap.xml', pages=pages, today=datetime.now())
    response = Response(sitemap_xml, mimetype='application/xml')
    return response


@bp.route('/recall-judge-parisien')
def recall_judge_parisien():
    return render_template('recall_judge_parisien.html')