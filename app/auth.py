from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
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

        if review.judge.state in COURTS_BY_STATE:
            form.court.choices = COURTS_BY_STATE[review.judge.state]

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


@bp.route('/admin/delete_review/<int:review_id>', methods=['POST'])
@admin_required
def admin_delete_review(review_id):
    review = Review.query.get_or_404(review_id)
    admin_message = request.form.get('admin_message', '').strip() or None

    AdminLog.log_action(
        admin_user=current_user,
        action_type='delete_review',
        target_review=review,
        target_user=review.user if review.user else None,
        details=f'Deleted review {review_id} for judge {review.judge.full_name()}'
    )

    if review.user:
        try:
            from app.email_utils import send_user_content_action_notification
            send_user_content_action_notification(review.user, review, review.judge, 'deleted', admin_message)
        except Exception as e:
            current_app.logger.error(f"Failed to send delete review notification: {str(e)}")

    db.session.delete(review)
    db.session.commit()

    flash('Review deleted by admin.')
    return redirect(url_for('auth.admin_dashboard'))


@bp.route('/admin/delete_media_link/<int:media_link_id>', methods=['POST'])
@admin_required
def admin_delete_media_link(media_link_id):
    media_link = MediaLink.query.get_or_404(media_link_id)
    admin_message = request.form.get('admin_message', '').strip() or None

    AdminLog.log_action(
        admin_user=current_user,
        action_type='delete_media_link',
        target_media_link=media_link,
        target_user=media_link.user if media_link.user else None,
        details=f'Deleted media link {media_link_id} for judge {media_link.judge.full_name()}'
    )

    if media_link.user:
        try:
            from app.email_utils import send_user_content_action_notification
            send_user_content_action_notification(media_link.user, media_link, media_link.judge, 'deleted',
                                                  admin_message)
        except Exception as e:
            current_app.logger.error(f"Failed to send delete media link notification: {str(e)}")

    db.session.delete(media_link)
    db.session.commit()

    flash('Media link deleted by admin.')
    return redirect(url_for('auth.admin_dashboard'))


@bp.route('/admin/approve_media_link/<int:media_link_id>', methods=['POST'])
@admin_required
def admin_approve_media_link(media_link_id):
    media_link = MediaLink.query.get_or_404(media_link_id)
    admin_message = request.form.get('admin_message', '').strip() or None
    media_link.is_verified = True
    db.session.commit()

    AdminLog.log_action(
        admin_user=current_user,
        action_type='approve_media_link',
        target_media_link=media_link,
        target_user=media_link.user if media_link.user else None,
        details=f'Approved media link {media_link_id} for judge {media_link.judge.full_name()}'
    )

    if media_link.user:
        try:
            from app.email_utils import send_user_content_action_notification
            send_user_content_action_notification(media_link.user, media_link, media_link.judge, 'approved',
                                                  admin_message)
        except Exception as e:
            current_app.logger.error(f"Failed to send approve notification: {str(e)}")

    flash('Media link approved and is now visible to the public.')
    return redirect(url_for('auth.admin_dashboard'))


@bp.route('/admin/reject_media_link/<int:media_link_id>', methods=['POST'])
@admin_required
def admin_reject_media_link(media_link_id):
    media_link = MediaLink.query.get_or_404(media_link_id)
    admin_message = request.form.get('admin_message', '').strip() or None

    AdminLog.log_action(
        admin_user=current_user,
        action_type='reject_media_link',
        target_media_link=media_link,
        target_user=media_link.user if media_link.user else None,
        details=f'Rejected and deleted media link {media_link_id} for judge {media_link.judge.full_name()}'
    )

    if media_link.user:
        try:
            from app.email_utils import send_user_content_action_notification
            send_user_content_action_notification(media_link.user, media_link, media_link.judge, 'rejected',
                                                  admin_message)
        except Exception as e:
            current_app.logger.error(f"Failed to send reject notification: {str(e)}")

    db.session.delete(media_link)
    db.session.commit()

    flash('Media link rejected and deleted.')
    return redirect(url_for('auth.admin_dashboard'))


# ============================================================================
#  USER MANAGEMENT ROUTES
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
        admin_message = request.form.get('admin_message', '').strip() or None
        user.ban(current_user, ban_reason)

        AdminLog.log_action(
            admin_user=current_user,
            action_type='ban_user',
            target_user=user,
            details=f'Banned user {user.username} ({user.email}). Reason: {ban_reason}'
        )

        try:
            from app.email_utils import send_user_account_notification
            send_user_account_notification(user, 'banned', admin_message)
        except Exception as e:
            current_app.logger.error(f"Failed to send ban notification: {str(e)}")

        flash(f'User {user.username} has been banned.')
        return redirect(url_for('auth.view_user_activity', user_id=user.id))

    user = User.query.get_or_404(user_id)
    return render_template('admin_ban_user.html', user=user)


@bp.route('/admin/user/<int:user_id>/unban', methods=['GET', 'POST'])
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

    admin_message = request.form.get('admin_message', '').strip() or None

    try:
        from app.email_utils import send_user_account_notification
        send_user_account_notification(user, 'unbanned', admin_message)
    except Exception as e:
        current_app.logger.error(f"Failed to send unban notification: {str(e)}")

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

        # Send admin notification for flagged content
        try:
            from app.email_utils import send_admin_flag_notification
            judge = Judge.query.get_or_404(review.judge_id)
            send_admin_flag_notification(flag, review, judge)
        except Exception as e:
            current_app.logger.error(f"Failed to send flag notification: {str(e)}")

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

        # Send admin notification for flagged content
        try:
            from app.email_utils import send_admin_flag_notification
            judge = Judge.query.get_or_404(media_link.judge_id)
            send_admin_flag_notification(flag, media_link, judge)
        except Exception as e:
            current_app.logger.error(f"Failed to send flag notification: {str(e)}")

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


@bp.route('/admin/flag/<int:flag_id>/dismiss', methods=['GET', 'POST'])
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
    admin_message = request.form.get('admin_message', '').strip() or None

    if action == 'delete_content':
        if flag.review_id:
            review = Review.query.get(flag.review_id)
            if review:
                if review.user:
                    try:
                        from app.email_utils import send_user_content_action_notification
                        send_user_content_action_notification(review.user, review, review.judge, 'deleted',
                                                              admin_message)
                    except Exception as e:
                        current_app.logger.error(f"Failed to send delete notification: {str(e)}")
                db.session.delete(review)
                flag.resolution_action = 'content_deleted'
                AdminLog.log_action(current_user, 'delete_review', target_review=review)
        elif flag.media_link_id:
            media_link = MediaLink.query.get(flag.media_link_id)
            if media_link:
                if media_link.user:
                    try:
                        from app.email_utils import send_user_content_action_notification
                        send_user_content_action_notification(media_link.user, media_link, media_link.judge, 'deleted',
                                                              admin_message)
                    except Exception as e:
                        current_app.logger.error(f"Failed to send delete notification: {str(e)}")
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
            try:
                from app.email_utils import send_user_account_notification
                send_user_account_notification(user, 'banned', admin_message)
            except Exception as e:
                current_app.logger.error(f"Failed to send ban notification: {str(e)}")
            flash(f'User {user.username} banned.')

    return redirect(url_for('auth.moderation_queue'))


@bp.route('/admin/flag/<int:flag_id>/unban', methods=['POST'])
@admin_required
def unban_from_flag(flag_id):
    """Unban a user from the moderation queue"""
    flag = ContentFlag.query.get_or_404(flag_id)
    admin_message = request.form.get('admin_message', '').strip() or None

    # Get the user from the flag
    if flag.review_id:
        review = Review.query.get(flag.review_id)
        user = review.user if review else None
    elif flag.media_link_id:
        media_link = MediaLink.query.get(flag.media_link_id)
        user = media_link.user if media_link else None
    else:
        user = None

    if not user:
        flash('User not found.')
        return redirect(url_for('auth.moderation_queue'))

    if not user.is_banned:
        flash(f'User {user.username} is not currently banned.')
        return redirect(url_for('auth.moderation_queue'))

    # Unban the user
    user.unban()

    # Log the admin action
    AdminLog.log_action(
        admin_user=current_user,
        action_type='unban_user',
        target_user=user,
        details=f'Unbanned {user.username} from flag {flag.id} ({flag.flag_type})'
    )

    # Send notification email
    try:
        from app.email_utils import send_user_account_notification
        send_user_account_notification(user, 'unbanned', admin_message)
    except Exception as e:
        current_app.logger.error(f"Failed to send unban notification: {str(e)}")

    flash(f'User {user.username} has been unbanned.')
    return redirect(url_for('auth.moderation_queue'))


# ============================================================================
# ADMIN STATISTICS FUNCTIONALITY
# ============================================================================
@bp.route('/admin/statistics')
@admin_required
def admin_statistics():
    """Comprehensive admin statistics dashboard"""
    from datetime import datetime, timedelta
    from sqlalchemy import func, and_

    # Get date range parameters (default to last 8 weeks)
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')

    if start_date_str and end_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
        except:
            start_date = datetime.now() - timedelta(weeks=8)
            end_date = datetime.now()
    else:
        start_date = datetime.now() - timedelta(weeks=8)
        end_date = datetime.now()

    # Get adjustable list size parameters
    top_n = int(request.args.get('top_n', 10))

    # ========== SUMMARY STATS ==========
    total_users = User.query.filter_by(is_banned=False).count()
    total_reviews = Review.query.count()
    total_media_links = MediaLink.query.count()
    pending_verifications = MediaLink.query.filter_by(is_verified=False).count()

    # Overall average rating
    avg_rating_result = db.session.query(func.avg(Review.rating)).scalar()
    overall_avg_rating = round(avg_rating_result, 2) if avg_rating_result else 0

    # Total concern flags
    total_concerns = Review.query.filter(
        db.or_(
            Review.fairness_concern == True,
            Review.bias_concern == True,
            Review.temperament_concern == True
        )
    ).count()

    # ========== GROWTH METRICS ==========
    # Reviews in date range
    reviews_in_range = Review.query.filter(
        Review.created_at >= start_date,
        Review.created_at <= end_date
    ).count()

    # Media links in date range
    media_in_range = MediaLink.query.filter(
        MediaLink.created_at >= start_date,
        MediaLink.created_at <= end_date
    ).count()

    # New users in date range
    users_in_range = User.query.filter(
        User.created_at >= start_date,
        User.created_at <= end_date
    ).count()

    # Judges who received first review in range
    new_reviewed_judges = db.session.query(Judge.id).join(Review).group_by(Judge.id).having(
        func.min(Review.created_at) >= start_date,
        func.min(Review.created_at) <= end_date
    ).count()

    # Active contributors in date range
    active_contributors = db.session.query(func.count(func.distinct(Review.user_id))).filter(
        Review.created_at >= start_date,
        Review.created_at <= end_date
    ).scalar() or 0

    # Verifications completed in range
    verifications_in_range = MediaLink.query.filter(
        MediaLink.is_verified == True,
        MediaLink.created_at >= start_date,
        MediaLink.created_at <= end_date
    ).count()

    # ========== TOP LISTS ==========
    # Most reviewed judges
    most_reviewed = db.session.query(
        Judge,
        func.count(Review.id).label('review_count')
    ).join(Review).group_by(Judge.id).order_by(
        func.count(Review.id).desc()
    ).limit(top_n).all()

    # Most documented judges (by verified media links)
    most_documented = db.session.query(
        Judge,
        func.count(MediaLink.id).label('media_count')
    ).join(MediaLink).filter(
        MediaLink.is_verified == True
    ).group_by(Judge.id).order_by(
        func.count(MediaLink.id).desc()
    ).limit(top_n).all()

    # Highest rated judges (min 3 reviews)
    highest_rated = db.session.query(
        Judge,
        func.avg(Review.rating).label('avg_rating'),
        func.count(Review.id).label('review_count')
    ).join(Review).group_by(Judge.id).having(
        func.count(Review.id) >= 3
    ).order_by(func.avg(Review.rating).desc()).limit(top_n).all()

    # Lowest rated judges (min 3 reviews)
    lowest_rated = db.session.query(
        Judge,
        func.avg(Review.rating).label('avg_rating'),
        func.count(Review.id).label('review_count')
    ).join(Review).group_by(Judge.id).having(
        func.count(Review.id) >= 3
    ).order_by(func.avg(Review.rating).asc()).limit(top_n).all()

    # Most concerning judges
    most_concerning = db.session.query(
        Judge,
        func.count(Review.id).label('concern_count')
    ).join(Review).filter(
        db.or_(
            Review.fairness_concern == True,
            Review.bias_concern == True,
            Review.temperament_concern == True
        )
    ).group_by(Judge.id).order_by(
        func.count(Review.id).desc()
    ).limit(top_n).all()

    # Most active users
    most_active_users = db.session.query(
        User,
        func.count(Review.id).label('review_count')
    ).join(Review).group_by(User.id).order_by(
        func.count(Review.id).desc()
    ).limit(top_n).all()

    # Most flagged content
    most_flagged = ContentFlag.query.filter_by(
        is_resolved=False
    ).order_by(ContentFlag.created_at.desc()).limit(top_n).all()

    # ========== GEOGRAPHIC DISTRIBUTION ==========
    judges_by_state = db.session.query(
        Judge.state,
        func.count(Judge.id).label('judge_count'),
        func.count(Review.id).label('review_count'),
        func.count(MediaLink.id).label('media_count')
    ).outerjoin(Review).outerjoin(MediaLink).group_by(
        Judge.state
    ).order_by(Judge.state).all()

    # ========== RATING DISTRIBUTION ==========
    rating_dist = db.session.query(
        Review.rating,
        func.count(Review.id).label('count')
    ).group_by(Review.rating).order_by(Review.rating).all()

    rating_distribution = {i: 0 for i in range(1, 6)}
    for rating, count in rating_dist:
        rating_distribution[rating] = count

    # ========== CONCERN TYPE BREAKDOWN ==========
    fairness_count = Review.query.filter_by(fairness_concern=True).count()
    bias_count = Review.query.filter_by(bias_concern=True).count()
    temperament_count = Review.query.filter_by(temperament_concern=True).count()

    concern_breakdown = {
        'fairness': fairness_count,
        'bias': bias_count,
        'temperament': temperament_count
    }

    # Reviews with any concern
    reviews_with_concerns = Review.query.filter(
        db.or_(
            Review.fairness_concern == True,
            Review.bias_concern == True,
            Review.temperament_concern == True
        )
    ).count()

    # Multiple concerns (reviews with 2+ concern types)
    multiple_concerns = Review.query.filter(
        db.or_(
            db.and_(Review.fairness_concern == True, Review.bias_concern == True),
            db.and_(Review.fairness_concern == True, Review.temperament_concern == True),
            db.and_(Review.bias_concern == True, Review.temperament_concern == True)
        )
    ).count()

    # ========== TEMPORAL TRENDS (Last 12 months) ==========
    twelve_months_ago = datetime.now() - timedelta(days=365)

    # Reviews per month
    reviews_by_month = db.session.query(
        func.strftime('%Y-%m', Review.created_at).label('month'),
        func.count(Review.id).label('count')
    ).filter(Review.created_at >= twelve_months_ago).group_by('month').all()

    # Media links per month
    media_by_month = db.session.query(
        func.strftime('%Y-%m', MediaLink.created_at).label('month'),
        func.count(MediaLink.id).label('count')
    ).filter(MediaLink.created_at >= twelve_months_ago).group_by('month').all()

    # ========== FEDERAL VS STATE COMPARISON ==========
    federal_count = Judge.query.filter_by(is_federal=True).count()
    state_count = Judge.query.filter_by(is_federal=False).count()

    federal_avg_rating = db.session.query(
        func.avg(Review.rating)
    ).join(Judge).filter(Judge.is_federal == True).scalar()

    state_avg_rating = db.session.query(
        func.avg(Review.rating)
    ).join(Judge).filter(Judge.is_federal == False).scalar()

    federal_review_count = db.session.query(
        func.count(Review.id)
    ).join(Judge).filter(Judge.is_federal == True).scalar()

    state_review_count = db.session.query(
        func.count(Review.id)
    ).join(Judge).filter(Judge.is_federal == False).scalar()

    # ========== RETIRED VS ACTIVE COMPARISON ==========
    retired_count = Judge.query.filter_by(is_retired=True).count()
    active_count = Judge.query.filter_by(is_retired=False).count()

    retired_avg_rating = db.session.query(
        func.avg(Review.rating)
    ).join(Judge).filter(Judge.is_retired == True).scalar()

    active_avg_rating = db.session.query(
        func.avg(Review.rating)
    ).join(Judge).filter(Judge.is_retired == False).scalar()

    return render_template(
        'admin_statistics.html',
        # Summary stats
        total_users=total_users,
        total_reviews=total_reviews,
        total_media_links=total_media_links,
        pending_verifications=pending_verifications,
        overall_avg_rating=overall_avg_rating,
        total_concerns=total_concerns,
        # Growth metrics
        start_date=start_date,
        end_date=end_date,
        reviews_in_range=reviews_in_range,
        media_in_range=media_in_range,
        users_in_range=users_in_range,
        # Top lists
        top_n=top_n,
        most_reviewed=most_reviewed,
        most_documented=most_documented,
        highest_rated=highest_rated,
        lowest_rated=lowest_rated,
        most_concerning=most_concerning,
        most_active_users=most_active_users,
        most_flagged=most_flagged,
        # Geographic
        judges_by_state=judges_by_state,
        # Rating distribution
        rating_distribution=rating_distribution,
        # Concern breakdown
        concern_breakdown=concern_breakdown,
        # Temporal trends
        reviews_by_month=reviews_by_month,
        media_by_month=media_by_month,
        # Comparisons
        federal_count=federal_count,
        state_count=state_count,
        federal_avg_rating=round(federal_avg_rating, 2) if federal_avg_rating else 0,
        state_avg_rating=round(state_avg_rating, 2) if state_avg_rating else 0,
        federal_review_count=federal_review_count or 0,
        state_review_count=state_review_count or 0,
        retired_count=retired_count,
        active_count=active_count,
        retired_avg_rating=round(retired_avg_rating, 2) if retired_avg_rating else 0,
        active_avg_rating=round(active_avg_rating, 2) if active_avg_rating else 0,
        new_reviewed_judges=new_reviewed_judges,
        reviews_with_concerns=reviews_with_concerns,
        active_contributors=active_contributors,
        verifications_in_range=verifications_in_range,
        multiple_concerns=multiple_concerns
    )