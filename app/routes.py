from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.models import Judge, Review, MediaLink, User, ContentFlag
from app.forms import ReviewForm, MediaLinkForm
from app.court_data import STATES, COURTS_BY_STATE

bp = Blueprint('main', __name__)



@bp.route('/index', methods=['GET', 'POST'])
def index():
    from app.forms import SearchForm
    form = SearchForm()

    # Populate state filter choices
    form.filter_state.choices = [('', 'All States')] + STATES

    # Start with base query
    query = Judge.query

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

        # Apply state filter
        if form.filter_state.data:
            query = query.filter(Judge.state == form.filter_state.data)

        # Apply federal filter
        if form.filter_federal.data == 'federal':
            query = query.filter(Judge.is_federal == True)
        elif form.filter_federal.data == 'state':
            query = query.filter(Judge.is_federal == False)

        # Apply retired filter
        if form.filter_retired.data == 'active':
            query = query.filter(Judge.is_retired == False)
        elif form.filter_retired.data == 'retired':
            query = query.filter(Judge.is_retired == True)

        # Get all results
        judges = query.all()

        # Apply content filter (must be done after getting results)
        if form.filter_content.data == 'has_reviews':
            judges = [j for j in judges if j.review_count() > 0]
        elif form.filter_content.data == 'has_media':
            judges = [j for j in judges if j.media_link_count() > 0]
        elif form.filter_content.data == 'has_both':
            judges = [j for j in judges if j.review_count() > 0 and j.media_link_count() > 0]

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
        judges = query.all()
        judges.sort(key=lambda j: (j.last_name.lower(), j.first_name.lower()))

    return render_template('index.html', judges=judges, form=form)


@bp.route('/judge/<int:judge_id>')
def judge(judge_id):
    judge = Judge.query.get_or_404(judge_id)
    reviews = judge.reviews.all()
    media_links = judge.media_links

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

        if request.method == 'POST':
            print("=== DEBUG POST ===")
            print(f"judge_id from args: {request.args.get('judge_id', type=int)}")
            print(f"judge_id from form: {request.form.get('prefilled_judge_id', type=int)}")
            print(f"prefilled_judge: {prefilled_judge}")
            print(f"All form data: {request.form}")
            print("=== END DEBUG ===")
        # If judge was pre-filled, use it
        if prefilled_judge:
            # Only validate review fields
            if form.rating.data and form.court_date.data and form.review_text.data:
                judge = prefilled_judge
            else:
                flash('Please fill out all required review fields.')
                return render_template('submit_review.html', form=form, courts_by_state=COURTS_BY_STATE,
                                       prefilled_judge=prefilled_judge)
        elif form.validate_on_submit():
            # Normal flow: find or create judge
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
            # Validation failed
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

        flash('Review submitted successfully!')
        return redirect(url_for('main.judge', judge_id=judge.id))

    return render_template('submit_review.html', form=form, courts_by_state=COURTS_BY_STATE,
                           prefilled_judge=prefilled_judge)


@bp.route('/submit_media_link', methods=['GET', 'POST'])
@login_required
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
        # If judge was pre-filled, use it
        if prefilled_judge:
            # Only validate media link fields
            if form.headline.data and form.news_source.data and form.url.data and form.publication_date.data and form.summary.data:
                judge = prefilled_judge
            else:
                flash('Please fill out all required media link fields.')
                return render_template('submit_media.html', form=form, courts_by_state=COURTS_BY_STATE,
                                       prefilled_judge=prefilled_judge)
        elif form.validate_on_submit():
            # Normal flow: find or create judge
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
            # Validation failed
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

        flash(
            'Media link submitted successfully! It is pending verification and will appear once approved by our moderation team.')
        return redirect(url_for('main.judge', judge_id=judge.id))

    return render_template('submit_media.html', form=form, courts_by_state=COURTS_BY_STATE,
                           prefilled_judge=prefilled_judge)


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
    return redirect(url_for("main.about"), code=301)


@bp.route('/robots.txt')
def robots():
    from flask import send_from_directory
    return send_from_directory('static', 'robots.txt', mimetype='text/plain')


@bp.route('/sitemap.xml')
def sitemap_xml():
    from flask import Response
    from datetime import datetime

    # Get all judges for individual pages
    judges = Judge.query.all()

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