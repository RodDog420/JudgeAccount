from flask import current_app, render_template_string
from flask_mail import Mail, Message
from datetime import datetime
import os

mail = Mail()

def init_mail(app):
    """Initialize Flask-Mail with the app"""
    mail.init_app(app)


def send_email(subject, recipient, html_body, text_body=None):
    """
    Send an email using Flask-Mail in a background thread.

    Args:
        subject (str): Email subject line
        recipient (str): Recipient email address
        html_body (str): HTML email content
        text_body (str, optional): Plain text fallback

    Returns:
        bool: True if dispatched successfully, False otherwise
    """
    from threading import Thread
    import re

    app = current_app._get_current_object()

    msg = Message(
        subject=subject,
        sender=app.config['MAIL_DEFAULT_SENDER'],
        recipients=[recipient]
    )
    msg.html = html_body
    msg.body = text_body if text_body else re.sub('<.*?>', '', html_body)

    def send_async(app, msg):
        with app.app_context():
            try:
                mail.send(msg)
                app.logger.info(f"Email sent: {subject} to {recipient}")
            except Exception as e:
                app.logger.error(f"Failed to send email: {subject} to {recipient} — {str(e)}")

    try:
        thread = Thread(target=send_async, args=[app, msg])
        thread.start()
        return True
    except Exception as e:
        current_app.logger.error(f"Failed to dispatch email thread: {str(e)}")
        return False


def send_password_reset_email(user):
    """
    Send a password reset email with a signed time-limited token.

    Args:
        user: User object requesting the reset
    """
    from itsdangerous import URLSafeTimedSerializer

    s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    token = s.dumps(user.id, salt='password-reset')
    reset_url = f"{current_app.config.get('BASE_URL', 'http://localhost:5000')}/reset_password/{token}"

    html_body = f"""
    <html>
    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                 line-height: 1.6; color: #333; background-color: #f4f4f4; margin: 0; padding: 20px;">
        <div style="max-width: 600px; margin: 0 auto; background-color: white;
                    border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
            <div style="background-color: #2c3e50; color: white; padding: 20px;
                        border-radius: 8px 8px 0 0; text-align: center;">
                <h1 style="margin: 0; font-size: 24px;">Password Reset Request</h1>
                <p style="margin: 5px 0 0 0; opacity: 0.9;">JudgeAccount</p>
            </div>
            <div style="padding: 30px;">
                <p style="font-size: 18px; margin-bottom: 20px;">Hi {user.username},</p>
                <p>We received a request to reset your password.
                   Click the button below to set a new password.</p>
                <p>This link will expire in <strong>15 minutes</strong>.</p>
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{reset_url}"
                       style="background-color: #3498db; color: white; padding: 12px 30px;
                              text-decoration: none; border-radius: 5px; font-size: 16px;">
                        Reset My Password
                    </a>
                </div>
                <p style="color: #7f8c8d; font-size: 14px;">
                    If you did not request a password reset, you can safely ignore this email.
                    Your password will not change.
                </p>
                <p style="color: #7f8c8d; font-size: 14px;">
                    If the button above does not work, copy and paste this link into your browser:
                    <br><a href="{reset_url}" style="color: #3498db;">{reset_url}</a>
                </p>
            </div>
            <div style="background-color: #2c3e50; color: white; padding: 15px;
                        border-radius: 0 0 8px 8px; text-align: center; font-size: 14px;">
                <p style="margin: 0;">JudgeAccount - Promoting Judicial Accountability</p>
            </div>
        </div>
    </body>
    </html>
    """

    return send_email(
        subject="Password Reset Request - JudgeAccount",
        recipient=user.email,
        html_body=html_body
    )


def send_admin_flag_notification(flag, content, judge):
    """
    Send notification to admin when content is flagged

    Args:
        flag: ContentFlag object
        content: The flagged content (Review or MediaLink)
        judge: Judge object the content is about
    """

    # Load HTML template from main templates folder
    template_path = os.path.join(os.path.dirname(__file__), 'templates', 'emails', 'admin_flag_notification.html')
    try:
        with open(template_path, 'r') as f:
            template = f.read()
    except FileNotFoundError:
        template = """
        <html><body>
        <h2>Content Flagged for Review</h2>
        <p><strong>Content Type:</strong> {{ content_type }}</p>
        <p><strong>Judge:</strong> {{ judge_name }}</p>
        <p><strong>Flag Reason:</strong> {{ flag_reason }}</p>
        <p><strong>Flagged By:</strong> {{ flagger_username }}</p>
        <p><a href="{{ review_url }}">Review Content</a></p>
        </body></html>
        """

    # Determine content type
    content_type = "Review" if hasattr(content, 'rating') else "Media Link"

    # Get today's flag count
    from app.models import ContentFlag
    total_flags_today = ContentFlag.query.filter(
        ContentFlag.created_at >= datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    ).count()

    # Template data
    template_data = {
        'content_type': content_type,
        'username': content.user.username if content.user else 'Anonymous',
        'judge_name': f"{judge.first_name} {judge.last_name}",
        'flag_reason': flag.flag_type,
        'flag_date': flag.created_at.strftime('%Y-%m-%d %H:%M UTC'),
        'additional_details': flag.description or '',
        'review_url': f"{current_app.config.get('BASE_URL', 'http://localhost:5000')}/admin/flags",
        'flagger_username': flag.flagger.username if flag.flagger else 'Anonymous',
        'total_flags_today': total_flags_today
    }

    html_body = render_template_string(template, **template_data)

    subject = f"Content Flagged: {content_type} about {judge.first_name} {judge.last_name}"

    return send_email(
        subject=subject,
        recipient=current_app.config['ADMIN_EMAIL'],
        html_body=html_body
    )


def send_user_content_issue_notification(user, content, judge, issue_type, admin_message):
    """
    Send notification to user when their content has issues

    Args:
        user: User object
        content: The content object (Review or MediaLink)
        judge: Judge object
        issue_type: String describing the issue
        admin_message: Message from admin explaining what needs to be fixed
    """

    template_path = os.path.join(os.path.dirname(__file__), 'templates', 'emails', 'user_content_issue.html')
    try:
        with open(template_path, 'r') as f:
            template = f.read()
    except FileNotFoundError:
        template = """
        <html><body>
        <h2>Your Submission Needs Attention</h2>
        <p>Hi {{ username }},</p>
        <p>Your {{ content_type }} submission requires some updates.</p>
        <p><strong>Issue:</strong> {{ issue_type }}</p>
        <p><strong>Admin Message:</strong> {{ admin_message }}</p>
        <p><a href="{{ edit_url }}">Update Your Submission</a></p>
        <p><em>Add Admin@JudgeAccount.com to your contacts for reliable email delivery.</em></p>
        </body></html>
        """

    content_type = "Review" if hasattr(content, 'rating') else "Media Link"
    if content_type == "Review":
        edit_url = f"{current_app.config.get('BASE_URL', 'http://localhost:5000')}/edit_review/{content.id}"
    else:
        edit_url = f"{current_app.config.get('BASE_URL', 'http://localhost:5000')}/edit_media_link/{content.id}"

    template_data = {
        'username': user.username,
        'content_type': content_type,
        'judge_name': f"{judge.first_name} {judge.last_name}",
        'submission_date': content.created_at.strftime('%Y-%m-%d'),
        'issue_type': issue_type,
        'admin_message': admin_message,
        'edit_url': edit_url
    }

    html_body = render_template_string(template, **template_data)

    subject = f"Action Required: Your {content_type} Submission on JudgeAccount"

    return send_email(
        subject=subject,
        recipient=user.email,
        html_body=html_body
    )


def send_admin_new_content_notification(content, judge):
    """
    Send notification to admin when new content is submitted for moderation

    Args:
        content: The new content (Review or MediaLink)
        judge: Judge object
    """

    content_type = "Review" if hasattr(content, 'rating') else "Media Link"
    base_url = current_app.config.get('BASE_URL', 'http://localhost:5000')

    html_body = f"""
    <html>
    <body style="font-family: Arial, sans-serif;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
            <h2 style="color: #3498db;">New {content_type} Submitted</h2>
            <div style="background: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0;">
                <p><strong>Content Type:</strong> {content_type}</p>
                <p><strong>Judge:</strong> {judge.first_name} {judge.last_name}</p>
                <p><strong>Submitted By:</strong> {content.user.username if content.user else 'Anonymous'}</p>
                <p><strong>Date:</strong> {content.created_at.strftime('%Y-%m-%d %H:%M UTC')}</p>
            </div>
            <div style="text-align: center; margin: 30px 0;">
                <a href="{base_url}/admin/dashboard"
                   style="background: #3498db; color: white; padding: 10px 20px;
                          text-decoration: none; border-radius: 5px;">
                    Review New Content
                </a>
            </div>
            <p style="color: #7f8c8d; font-size: 14px; text-align: center;">
                JudgeAccount Moderation System
            </p>
        </div>
    </body>
    </html>
    """

    subject = f"New {content_type} Submitted: {judge.first_name} {judge.last_name}"

    return send_email(
        subject=subject,
        recipient=current_app.config['ADMIN_EMAIL'],
        html_body=html_body
    )


def send_user_content_action_notification(user, content, judge, action_type, admin_message=None):
    """
    Send notification to user when admin takes action on their content.

    Args:
        user: User object
        content: The content object (Review or MediaLink)
        judge: Judge object
        action_type: 'deleted', 'rejected', or 'approved'
        admin_message: Optional message from admin
    """
    content_type = "Review" if hasattr(content, 'rating') else "Media Link"

    template_path = os.path.join(os.path.dirname(__file__), 'templates', 'emails', 'content_action_notification.html')
    try:
        with open(template_path, 'r') as f:
            template = f.read()
    except FileNotFoundError:
        template = """
        <html><body>
        <p>Hi {{ username }}, your {{ content_type }} about {{ judge_name }} has been {{ action_type }}.</p>
        {% if admin_message %}<p>{{ admin_message }}</p>{% endif %}
        </body></html>
        """

    template_data = {
        'username': user.username,
        'content_type': content_type,
        'judge_name': f"{judge.first_name} {judge.last_name}",
        'action_type': action_type,
        'admin_message': admin_message or '',
    }

    html_body = render_template_string(template, **template_data)

    if action_type == 'approved':
        subject = f"Your {content_type} Submission Has Been Approved - JudgeAccount"
    else:
        subject = f"Your {content_type} Submission Has Been {action_type.capitalize()} - JudgeAccount"

    return send_email(
        subject=subject,
        recipient=user.email,
        html_body=html_body
    )


def send_user_account_notification(user, action_type, admin_message=None):
    """
    Send notification to user about their account status change.

    Args:
        user: User object
        action_type: 'banned' or 'unbanned'
        admin_message: Optional message from admin
    """
    if action_type == 'banned':
        subject = "Account Status Notification"
        heading = "Account Suspended"
        body = "Your account has been suspended and you will no longer be able to log in or submit content."
    else:
        subject = "Your JudgeAccount Account Has Been Reinstated"
        heading = "Account Reinstated"
        body = "Your account suspension has been lifted. You may now log in and use JudgeAccount normally."

    optional_message = f"""
        <div style="background-color: #f8f9fa; padding: 20px; border-radius: 6px;
                    border-left: 4px solid #3498db; margin-bottom: 25px;">
            <p style="margin: 0 0 10px 0; font-weight: 600;">Message from our moderation team:</p>
            <p style="margin: 0;">{admin_message}</p>
        </div>
    """ if admin_message else ""

    header_color = "#e74c3c" if action_type == 'banned' else "#27ae60"

    html_body = f"""
    <html>
    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                 line-height: 1.6; color: #333; background-color: #f4f4f4; margin: 0; padding: 20px;">
        <div style="max-width: 600px; margin: 0 auto; background-color: white;
                    border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
            <div style="background-color: {header_color}; color: white; padding: 20px;
                        border-radius: 8px 8px 0 0; text-align: center;">
                <h1 style="margin: 0; font-size: 24px;">{heading}</h1>
                <p style="margin: 5px 0 0 0; opacity: 0.9;">Account Status Notification</p>
            </div>
            <div style="padding: 30px;">
                <p style="font-size: 18px; margin-bottom: 20px;">Hi {user.username},</p>
                <p style="margin-bottom: 20px;">{body}</p>
                {optional_message}
                <p style="font-size: 14px; color: #7f8c8d; margin-bottom: 0;">
                    If you have questions, please contact us through the website.
                </p>
            </div>
            <div style="background-color: #2c3e50; color: white; padding: 15px;
                        border-radius: 0 0 8px 8px; text-align: center; font-size: 14px;">
                <p style="margin: 0;">JudgeAccount - Promoting Judicial Accountability</p>
                <p style="margin: 5px 0 0 0; opacity: 0.8;">
                    This is an automated notification from our moderation team.
                </p>
            </div>
        </div>
    </body>
    </html>
    """

    return send_email(
        subject=subject,
        recipient=user.email,
        html_body=html_body
    )