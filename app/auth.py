from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, current_user, login_required
from urllib.parse import urlparse
from functools import wraps
from app import db
from app.models import User, Review, Judge, MediaLink, BannedUser, AdminLog, ContentFlag
from app.forms import LoginForm, RegistrationForm, FlagContentForm
from flask_wtf.csrf import generate_csrf

bp = Blueprint('auth', __name__)


# ============================================================================
# DECORATOR FOR ADMIN-ONLY ROUTES
# ============================================================================

def admin_required(f):
    """Decorator to require admin privileges"""

    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin:
            flash('Access denied. Admin privileges required.')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)

    return decorated_function


# ============================================================================
# AUTHENTICATION ROUTES
# ============================================================================

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password')
            return redirect(url_for('auth.login'))

        # NEW: Check if user is banned
        if user.is_banned:
            flash('Your account has been suspended. Please contact support if you believe this is an error.')
            return redirect(url_for('auth.login'))

        login_user(user, remember=form.remember_me.data)

        # NEW: Update last login time
        user.last_login = db.func.now()
        user.last_activity = db.func.now()
        db.session.commit()

        next_page = request.args.get('next')
        if not next_page or urlparse(next_page).netloc != '':
            next_page = url_for('main.index')
        return redirect(next_page)

    return render_template('login.html', form=form)


@bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    form = RegistrationForm()
    if form.validate_on_submit():
        # NEW: Check if username or email is banned
        if BannedUser.is_banned(username=form.username.data, email=form.email.data):
            flash('This username or email address is not eligible for registration.')
            return redirect(url_for('auth.register'))

        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Congratulations, you are now registered! Please log in.')
        return redirect(url_for('auth.login'))

    return render_template('register.html', form=form)


@bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('main.index'))


# ============================================================================
# USER DASHBOARD ROUTES
# ============================================================================

@bp.route('/dashboard')
@login_required
def dashboard():
    reviews = Review.query.filter_by(user_id=current_user.id).order_by(Review.created_at.desc()).all()
    media_links = MediaLink.query.filter_by(user_id=current_user.id).order_by(MediaLink.created_at.desc()).all()

    # NEW: Update last activity
    current_user.last_activity = db.func.now()
    db.session.commit()

    return render_template('dashboard.html', reviews=reviews, media_links=media_links)


@bp.route('/edit_review/<int:review_id>', methods=['GET', 'POST'])
@login_required
def edit_review(review_id):
    from app.forms import ReviewForm

    review = Review.query.get_or_404(review_id)

    if review.user_id != current_user.id:
        flash('You can only edit your own reviews.')
        return redirect(url_for('main.index'))

    form = ReviewForm()
    from app.court_data import STATES, COURTS_BY_STATE
    form.state.choices = STATES
    form.court.choices = []

    if request.method == 'POST' and form.validate_on_submit():
        review.rating = form.rating.data
        review.fairness_concern = form.fairness_concern.data
        review.bias_concern = form.bias_concern.data
        review.temperament_concern = form.temperament_concern.data
        review.review_text = form.review_text.data
        review.court_date = form.court_date.data
        db.session.commit()

        flash('Review updated successfully!')
        return redirect(url_for('auth.dashboard'))

    if request.method == 'GET':
        form.judge_first_name.data = review.judge.first_name
        form.judge_last_name.data = review.judge.last_name
        form.state.data = review.judge.state
        form.court.data = review.judge.court
        form.city.data = review.judge.city
        form.is_federal.data = review.judge.is_federal
        form.rating.data = review.rating
        form.fairness_concern.data = review.fairness_concern
        form.bias_concern.data = review.bias_concern
        form.temperament_concern.data = review.temperament_concern
        form.review_text.data = review.review_text
        form.court_date.data = review.court_date

    return render_template('edit_review.html', form=form, review=review, courts_by_state=COURTS_BY_STATE)


@bp.route('/delete_review/<int:review_id>')
@login_required
def delete_review(review_id):
    review = Review.query.get_or_404(review_id)

    if review.user_id != current_user.id:
        flash('You can only delete your own reviews.')
        return redirect(url_for('main.index'))

    db.session.delete(review)
    db.session.commit()

    flash('Review deleted successfully.')
    return redirect(url_for('auth.dashboard'))


@bp.route('/edit_media_link/<int:media_link_id>', methods=['GET', 'POST'])
@login_required
def edit_media_link(media_link_id):
    from app.forms import MediaLinkForm

    media_link = MediaLink.query.get_or_404(media_link_id)

    if media_link.user_id != current_user.id:
        flash('You can only edit your own media links.')
        return redirect(url_for('main.index'))

    form = MediaLinkForm()
    from app.court_data import STATES, COURTS_BY_STATE
    form.state.choices = STATES
    form.court.choices = []

    if form.state.data:
        form.court.choices = COURTS_BY_STATE.get(form.state.data, [])

    if request.method == 'POST':
        if form.headline.data and form.news_source.data and form.url.data and form.publication_date.data and form.summary.data:
            media_link.headline = form.headline.data
            media_link.news_source = form.news_source.data
            media_link.url = form.url.data
            media_link.publication_date = form.publication_date.data
            media_link.summary = form.summary.data
            media_link.is_verified = False
            db.session.commit()

            flash('Media link updated successfully! It will be re-verified by our team.')
            return redirect(url_for('auth.dashboard'))
        else:
            flash('Please fill out all required fields.')

    if request.method == 'GET':
        form.judge_first_name.data = media_link.judge.first_name
        form.judge_last_name.data = media_link.judge.last_name
        form.state.data = media_link.judge.state
        form.court.data = media_link.judge.court
        form.city.data = media_link.judge.city
        form.is_federal.data = media_link.judge.is_federal
        form.headline.data = media_link.headline
        form.news_source.data = media_link.news_source
        form.url.data = media_link.url
        form.publication_date.data = media_link.publication_date
        form.summary.data = media_link.summary

    return render_template('edit_media_link.html', form=form, media_link=media_link, courts_by_state=COURTS_BY_STATE)


@bp.route('/delete_media_link/<int:media_link_id>')
@login_required
def delete_media_link(media_link_id):
    media_link = MediaLink.query.get_or_404(media_link_id)

    if media_link.user_id != current_user.id:
        flash('You can only delete your own media links.')
        return redirect(url_for('main.index'))

    db.session.delete(media_link)
    db.session.commit()

    flash('Media link deleted successfully.')
    return redirect(url_for('auth.dashboard'))


# ============================================================================
# ADMIN DASHBOARD ROUTES (Original Content Moderation)
# ============================================================================

@bp.route('/admin', methods=['GET', 'POST'])
@admin_required
def admin_dashboard():
    from app.forms import AdminSearchForm

    form = AdminSearchForm()

    review_query = Review.query
    media_query = MediaLink.query

    if form.validate_on_submit():
        if form.search_judge.data:
            search_term = form.search_judge.data
            judge_filter = db.or_(
                Judge.first_name.ilike(f'%{search_term}%'),
                Judge.last_name.ilike(f'%{search_term}%'),
                db.func.concat(Judge.first_name, ' ', Judge.last_name).ilike(f'%{search_term}%')
            )
            review_query = review_query.join(Judge).filter(judge_filter)
            media_query = media_query.join(Judge).filter(judge_filter)

        if form.search_content.data:
            review_query = review_query.filter(Review.review_text.ilike(f'%{form.search_content.data}%'))
            media_query = media_query.filter(MediaLink.summary.ilike(f'%{form.search_content.data}%'))

        if form.filter_username.data:
            review_query = review_query.join(User).filter(User.username.ilike(f'%{form.filter_username.data}%'))
            media_query = media_query.join(User).filter(User.username.ilike(f'%{form.filter_username.data}%'))

        if form.filter_rating.data:
            review_query = review_query.filter(Review.rating == int(form.filter_rating.data))

        if form.filter_concerns.data == 'any':
            review_query = review_query.filter(
                db.or_(
                    Review.fairness_concern == True,
                    Review.bias_concern == True,
                    Review.temperament_concern == True
                )
            )
        elif form.filter_concerns.data == 'fairness':
            review_query = review_query.filter(Review.fairness_concern == True)
        elif form.filter_concerns.data == 'bias':
            review_query = review_query.filter(Review.bias_concern == True)
        elif form.filter_concerns.data == 'temperament':
            review_query = review_query.filter(Review.temperament_concern == True)

        all_reviews = review_query.all()
        all_media_links = media_query.all()

        if form.sort_by.data == 'newest':
            all_reviews.sort(key=lambda r: r.created_at, reverse=True)
            all_media_links.sort(key=lambda m: m.created_at, reverse=True)
        elif form.sort_by.data == 'oldest':
            all_reviews.sort(key=lambda r: r.created_at)
            all_media_links.sort(key=lambda m: m.created_at)
        elif form.sort_by.data == 'rating_high':
            all_reviews.sort(key=lambda r: r.rating, reverse=True)
        elif form.sort_by.data == 'rating_low':
            all_reviews.sort(key=lambda r: r.rating)
    else:
        all_reviews = review_query.order_by(Review.created_at.desc()).all()
        all_media_links = media_query.order_by(MediaLink.created_at.desc()).all()

    return render_template('admin_dashboard.html', reviews=all_reviews, media_links=all_media_links, form=form)


@bp.route('/admin/delete_review/<int:review_id>')
@admin_required
def admin_delete_review(review_id):
    review = Review.query.get_or_404(review_id)

    # NEW: Log the deletion
    AdminLog.log_action(
        admin_user=current_user,
        action_type='delete_review',
        target_review=review,
        target_user=review.user if review.user else None,
        details=f'Deleted review {review_id} for judge {review.judge.full_name()}'
    )

    db.session.delete(review)
    db.session.commit()

    flash('Review deleted by admin.')
    return redirect(url_for('auth.admin_dashboard'))


@bp.route('/admin/delete_media_link/<int:media_link_id>')
@admin_required
def admin_delete_media_link(media_link_id):
    media_link = MediaLink.query.get_or_404(media_link_id)

    # NEW: Log the deletion
    AdminLog.log_action(
        admin_user=current_user,
        action_type='delete_media_link',
        target_media_link=media_link,
        target_user=media_link.user if media_link.user else None,
        details=f'Deleted media link {media_link_id} for judge {media_link.judge.full_name()}'
    )

    db.session.delete(media_link)
    db.session.commit()

    flash('Media link deleted by admin.')
    return redirect(url_for('auth.admin_dashboard'))


@bp.route('/admin/approve_media_link/<int:media_link_id>')
@admin_required
def admin_approve_media_link(media_link_id):
    media_link = MediaLink.query.get_or_404(media_link_id)
    media_link.is_verified = True
    db.session.commit()

    # NEW: Log the approval
    AdminLog.log_action(
        admin_user=current_user,
        action_type='approve_media_link',
        target_media_link=media_link,
        target_user=media_link.user if media_link.user else None,
        details=f'Approved media link {media_link_id} for judge {media_link.judge.full_name()}'
    )

    flash('Media link approved and is now visible to the public.')
    return redirect(url_for('auth.admin_dashboard'))


@bp.route('/admin/reject_media_link/<int:media_link_id>')
@admin_required
def admin_reject_media_link(media_link_id):
    media_link = MediaLink.query.get_or_404(media_link_id)

    # NEW: Log the rejection
    AdminLog.log_action(
        admin_user=current_user,
        action_type='reject_media_link',
        target_media_link=media_link,
        target_user=media_link.user if media_link.user else None,
        details=f'Rejected and deleted media link {media_link_id} for judge {media_link.judge.full_name()}'
    )

    db.session.delete(media_link)
    db.session.commit()

    flash('Media link rejected and deleted.')
    return redirect(url_for('auth.admin_dashboard'))


# ============================================================================
# NEW: USER MANAGEMENT ROUTES
# ============================================================================

@bp.route('/admin/users')
@admin_required
def manage_users():
    """View all users with sorting and filtering options"""
    sort_by = request.args.get('sort', 'username_asc')
    filter_status = request.args.get('status', 'all')
    search_query = request.args.get('search', '')

    query = User.query

    if filter_status == 'active':
        query = query.filter_by(is_banned=False, is_admin=False)
    elif filter_status == 'banned':
        query = query.filter_by(is_banned=True)
    elif filter_status == 'admin':
        query = query.filter_by(is_admin=True)

    if search_query:
        search_term = f'%{search_query}%'
        query = query.filter(
            db.or_(
                User.username.ilike(search_term),
                User.email.ilike(search_term)
            )
        )

    users = query.all()

    user_data = []
    for user in users:
        user_data.append({
            'user': user,
            'review_count': user.get_review_count(),
            'media_link_count': user.get_media_link_count(),
            'verified_media_count': user.get_verified_media_count(),
        })

    if sort_by == 'username_asc':
        user_data.sort(key=lambda x: x['user'].username.lower())
    elif sort_by == 'username_desc':
        user_data.sort(key=lambda x: x['user'].username.lower(), reverse=True)
    elif sort_by == 'email_asc':
        user_data.sort(key=lambda x: x['user'].email.lower())
    elif sort_by == 'join_date_desc':
        user_data.sort(key=lambda x: x['user'].created_at, reverse=True)
    elif sort_by == 'join_date_asc':
        user_data.sort(key=lambda x: x['user'].created_at)
    elif sort_by == 'reviews_desc':
        user_data.sort(key=lambda x: x['review_count'], reverse=True)
    elif sort_by == 'media_desc':
        user_data.sort(key=lambda x: x['media_link_count'], reverse=True)
    elif sort_by == 'last_activity_desc':
        from datetime import datetime
        user_data.sort(key=lambda x: x['user'].last_activity or datetime.min, reverse=True)

    return render_template('admin_users.html',
                           user_data=user_data,
                           sort_by=sort_by,
                           filter_status=filter_status,
                           search_query=search_query)


@bp.route('/admin/user/<int:user_id>')
@admin_required
def view_user_activity(user_id):
    """View detailed activity for a specific user"""
    user = User.query.get_or_404(user_id)

    reviews = Review.query.filter_by(user_id=user.id).order_by(Review.created_at.desc()).all()
    media_links = MediaLink.query.filter_by(user_id=user.id).order_by(MediaLink.created_at.desc()).all()
    admin_logs = AdminLog.query.filter_by(target_user_id=user.id).order_by(AdminLog.timestamp.desc()).limit(20).all()

    return render_template('admin_user_detail.html',
                           user=user,
                           reviews=reviews,
                           media_links=media_links,
                           admin_logs=admin_logs)


@bp.route('/admin/user/<int:user_id>/ban', methods=['GET', 'POST'])
@admin_required
def ban_user(user_id):
    """Ban a user"""
    if request.method == 'POST':
        user = User.query.get_or_404(user_id)

        if user.id == current_user.id:
            flash('You cannot ban yourself.')
            return redirect(url_for('auth.manage_users'))

        if user.is_admin:
            flash('You cannot ban another administrator.')
            return redirect(url_for('auth.manage_users'))

        ban_reason = request.form.get('ban_reason', 'No reason provided')
        user.ban(current_user, ban_reason)

        AdminLog.log_action(
            admin_user=current_user,
            action_type='ban_user',
            target_user=user,
            details=f'Banned user {user.username} ({user.email}). Reason: {ban_reason}'
        )

        flash(f'User {user.username} has been banned.')
        return redirect(url_for('auth.view_user_activity', user_id=user.id))

    user = User.query.get_or_404(user_id)
    return render_template('admin_ban_user.html', user=user)


@bp.route('/admin/user/<int:user_id>/unban')
@admin_required
def unban_user(user_id):
    """Unban a user"""
    user = User.query.get_or_404(user_id)

    if not user.is_banned:
        flash('This user is not banned.')
        return redirect(url_for('auth.view_user_activity', user_id=user.id))

    user.unban()

    AdminLog.log_action(
        admin_user=current_user,
        action_type='unban_user',
        target_user=user,
        details=f'Unbanned user {user.username} ({user.email})'
    )

    flash(f'User {user.username} has been unbanned.')
    return redirect(url_for('auth.view_user_activity', user_id=user.id))


@bp.route('/admin/user/<int:user_id>/delete', methods=['GET', 'POST'])
@admin_required
def delete_user(user_id):
    """Permanently delete a user"""
    if request.method == 'POST':
        user = User.query.get_or_404(user_id)

        if user.id == current_user.id:
            flash('You cannot delete yourself.')
            return redirect(url_for('auth.manage_users'))

        if user.is_admin:
            flash('You cannot delete another administrator.')
            return redirect(url_for('auth.manage_users'))

        username = user.username
        email = user.email

        if not user.is_banned:
            delete_reason = request.form.get('delete_reason', 'Account deleted by admin')
            user.ban(current_user, delete_reason)

        AdminLog.log_action(
            admin_user=current_user,
            action_type='delete_user',
            target_user=user,
            details=f'Deleted user {username} ({email})'
        )

        db.session.delete(user)
        db.session.commit()

        flash(f'User {username} has been permanently deleted.')
        return redirect(url_for('auth.manage_users'))

    user = User.query.get_or_404(user_id)
    review_count = user.get_review_count()
    media_count = user.get_media_link_count()

    return render_template('admin_delete_user.html',
                           user=user,
                           review_count=review_count,
                           media_count=media_count)


@bp.route('/admin/user/<int:user_id>/note', methods=['GET', 'POST'])
@admin_required
def add_admin_note(user_id):
    """Add or update admin notes for a user"""
    if request.method == 'POST':
        user = User.query.get_or_404(user_id)

        admin_note = request.form.get('admin_note', '')
        user.admin_notes = admin_note
        db.session.commit()

        AdminLog.log_action(
            admin_user=current_user,
            action_type='add_admin_note',
            target_user=user,
            details=f'Updated admin notes for {user.username}'
        )

        flash('Admin notes updated.')
        return redirect(url_for('auth.view_user_activity', user_id=user.id))

    user = User.query.get_or_404(user_id)
    return render_template('admin_add_note.html', user=user)


@bp.route('/admin/banned-users')
@admin_required
def view_banned_users():
    """View all banned users"""
    show_unbanned = request.args.get('show_unbanned', 'false') == 'true'

    if show_unbanned:
        banned_users = BannedUser.query.order_by(BannedUser.banned_at.desc()).all()
    else:
        banned_users = BannedUser.query.filter_by(is_unbanned=False).order_by(BannedUser.banned_at.desc()).all()

    return render_template('admin_banned_users.html',
                           banned_users=banned_users,
                           show_unbanned=show_unbanned)


@bp.route('/admin/users/bulk', methods=['POST'])
@admin_required
def bulk_actions():
    """Handle bulk actions on multiple users"""
    action = request.form.get('bulk_action')
    user_ids = request.form.getlist('user_ids[]')

    if not user_ids:
        flash('No users selected.')
        return redirect(url_for('auth.manage_users'))

    user_ids = [int(uid) for uid in user_ids]

    if current_user.id in user_ids:
        flash('You cannot perform bulk actions on yourself.')
        return redirect(url_for('auth.manage_users'))

    users = User.query.filter(User.id.in_(user_ids)).all()

    if any(user.is_admin for user in users):
        flash('Bulk actions cannot be performed on administrators.')
        return redirect(url_for('auth.manage_users'))

    if action == 'ban':
        ban_reason = request.form.get('bulk_ban_reason', 'Bulk ban by admin')
        for user in users:
            if not user.is_banned:
                user.ban(current_user, ban_reason)
                AdminLog.log_action(
                    admin_user=current_user,
                    action_type='ban_user',
                    target_user=user,
                    details=f'Bulk banned user. Reason: {ban_reason}'
                )
        flash(f'{len(users)} user(s) have been banned.')

    elif action == 'delete':
        delete_reason = request.form.get('bulk_delete_reason', 'Bulk delete by admin')
        for user in users:
            if not user.is_banned:
                user.ban(current_user, delete_reason)
            AdminLog.log_action(
                admin_user=current_user,
                action_type='delete_user',
                target_user=user,
                details=f'Bulk deleted user'
            )
            db.session.delete(user)
        db.session.commit()
        flash(f'{len(users)} user(s) have been deleted.')

    return redirect(url_for('auth.manage_users'))


@bp.route('/flag/review/<int:review_id>', methods=['GET', 'POST'])
@login_required
def flag_review(review_id):
    """Flag a review as inappropriate"""
    review = Review.query.get_or_404(review_id)

    # Prevent self-flagging
    if review.user_id == current_user.id:
        flash('You cannot report your own content.')
        return redirect(url_for('main.judge', judge_id=review.judge_id))

    # Check if user already flagged this
    existing = ContentFlag.query.filter_by(
        user_id=current_user.id,
        review_id=review_id,
        is_resolved=False
    ).first()

    if existing:
        flash('You have already reported this review.')
        return redirect(url_for('main.judge', judge_id=review.judge_id))

    form = FlagContentForm()

    if form.validate_on_submit():
        flag = ContentFlag(
            user_id=current_user.id,
            review_id=review_id,
            flag_type=form.flag_type.data,
            description=form.description.data
        )
        db.session.add(flag)
        db.session.commit()

        flash('Thank you for your report. Our moderation team will review it.')
        return redirect(url_for('main.judge', judge_id=review.judge_id))

    return render_template('flag_content.html', form=form, content_type='review', content=review)


@bp.route('/flag/media/<int:media_link_id>', methods=['GET', 'POST'])
@login_required
def flag_media_link(media_link_id):
    """Flag a media link as inappropriate"""
    media_link = MediaLink.query.get_or_404(media_link_id)

    if media_link.user_id == current_user.id:
        flash('You cannot report your own content.')
        return redirect(url_for('main.judge', judge_id=media_link.judge_id))

    existing = ContentFlag.query.filter_by(
        user_id=current_user.id,
        media_link_id=media_link_id,
        is_resolved=False
    ).first()

    if existing:
        flash('You have already reported this media link.')
        return redirect(url_for('main.judge', judge_id=media_link.judge_id))

    form = FlagContentForm()

    if form.validate_on_submit():
        flag = ContentFlag(
            user_id=current_user.id,
            media_link_id=media_link_id,
            flag_type=form.flag_type.data,
            description=form.description.data
        )
        db.session.add(flag)
        db.session.commit()

        flash('Thank you for your report. Our moderation team will review it.')
        return redirect(url_for('main.judge', judge_id=media_link.judge_id))

    return render_template('flag_content.html', form=form, content_type='media_link', content=media_link)


@bp.route('/admin/flags')
@admin_required
def moderation_queue():
    """View all flagged content"""
    show_resolved = request.args.get('show_resolved', 'false') == 'true'

    if show_resolved:
        flags = ContentFlag.query.order_by(ContentFlag.created_at.desc()).all()
    else:
        flags = ContentFlag.query.filter_by(is_resolved=False).order_by(ContentFlag.created_at.desc()).all()

    return render_template('moderation_queue.html', flags=flags, show_resolved=show_resolved)


@bp.route('/admin/flag/<int:flag_id>/dismiss')
@admin_required
def dismiss_flag(flag_id):
    """Dismiss a flag as not violating rules"""
    flag = ContentFlag.query.get_or_404(flag_id)

    flag.is_resolved = True
    flag.resolved_by_id = current_user.id
    flag.resolved_at = db.func.now()
    flag.resolution_action = 'dismissed'
    db.session.commit()

    AdminLog.log_action(
        admin_user=current_user,
        action_type='dismiss_flag',
        details=f'Dismissed {flag.flag_type} flag on {"review" if flag.review_id else "media link"}'
    )

    flash('Flag dismissed.')
    return redirect(url_for('auth.moderation_queue'))


@bp.route('/admin/flag/<int:flag_id>/action', methods=['POST'])
@admin_required
def flag_action(flag_id):
    """Take action on flagged content"""
    flag = ContentFlag.query.get_or_404(flag_id)
    action = request.form.get('action')

    if action == 'delete_content':
        if flag.review_id:
            review = Review.query.get(flag.review_id)
            db.session.delete(review)
            flag.resolution_action = 'content_deleted'
            AdminLog.log_action(current_user, 'delete_review', target_review=review)
        elif flag.media_link_id:
            media_link = MediaLink.query.get(flag.media_link_id)
            db.session.delete(media_link)
            flag.resolution_action = 'content_deleted'
            AdminLog.log_action(current_user, 'delete_media_link', target_media_link=media_link)

        flag.is_resolved = True
        flag.resolved_by_id = current_user.id
        flag.resolved_at = db.func.now()
        db.session.commit()
        flash('Flagged content deleted.')

    elif action == 'ban_user':
        if flag.review_id:
            user = Review.query.get(flag.review_id).user
        elif flag.media_link_id:
            user = MediaLink.query.get(flag.media_link_id).user

        if user and not user.is_admin:
            user.ban(current_user, f'Content flagged as {flag.flag_type}')
            flag.is_resolved = True
            flag.resolved_by_id = current_user.id
            flag.resolved_at = db.func.now()
            flag.resolution_action = 'user_banned'
            db.session.commit()
            flash(f'User {user.username} banned.')

    return redirect(url_for('auth.moderation_queue'))
