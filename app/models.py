from app import db
from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash


class Judge(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    first_name = db.Column(db.String(30), nullable=False)
    last_name = db.Column(db.String(50), nullable=False, index=True)
    court = db.Column(db.String(150), nullable=False, index=True)
    city = db.Column(db.String(30), nullable=False, index=True)
    state = db.Column(db.String(2), nullable=False, index=True)
    is_federal = db.Column(db.Boolean, default=False, index=True)
    is_retired = db.Column(db.Boolean, default=False, index=True)

    __table_args__ = (
        db.UniqueConstraint('first_name', 'last_name', 'court', name='unique_judge'),
    )

    reviews = db.relationship('Review', backref='judge', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Judge {self.first_name} {self.last_name}>'

    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    def average_rating(self):
        reviews_list = self.reviews.all()
        if not reviews_list:
            return 0
        return sum(r.rating for r in reviews_list) / len(reviews_list)

    def review_count(self):
        return self.reviews.count()

    def media_link_count(self):
        return MediaLink.query.filter_by(judge_id=self.id, is_verified=True).count()


class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    judge_id = db.Column(db.Integer, db.ForeignKey('judge.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

    # Rating and concerns
    rating = db.Column(db.Integer, nullable=False)
    fairness_concern = db.Column(db.Boolean, default=False)
    bias_concern = db.Column(db.Boolean, default=False)
    temperament_concern = db.Column(db.Boolean, default=False)

    # Review content
    review_text = db.Column(db.Text, nullable=False)
    court_date = db.Column(db.Date, nullable=False)

    # Timestamp
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Review {self.id} for Judge {self.judge_id}>'


class MediaLink(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    judge_id = db.Column(db.Integer, db.ForeignKey('judge.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

    # Media Link Details
    headline = db.Column(db.String(500), nullable=False)
    news_source = db.Column(db.String(200), nullable=False)
    url = db.Column(db.String(1000), nullable=False)
    publication_date = db.Column(db.Date, nullable=False)
    summary = db.Column(db.Text, nullable=False)

    # Moderation
    is_verified = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    judge = db.relationship('Judge', backref='media_links')
    user = db.relationship('User', backref='media_links', foreign_keys=[user_id])

    def __repr__(self):
        return f'<MediaLink {self.headline}>'


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    is_admin = db.Column(db.Boolean, default=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # NEW: Ban tracking
    is_banned = db.Column(db.Boolean, default=False, nullable=False, index=True)
    ban_reason = db.Column(db.Text)
    banned_at = db.Column(db.DateTime)
    banned_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    # NEW: Activity tracking
    last_login = db.Column(db.DateTime)
    last_activity = db.Column(db.DateTime)

    # NEW: Admin notes for internal tracking
    admin_notes = db.Column(db.Text)

    # Relationships
    reviews = db.relationship('Review', backref='user', lazy='dynamic',
                              foreign_keys='Review.user_id')
    # media_links relationship already defined in MediaLink model

    # Self-referential relationship for banned_by
    banned_users = db.relationship('User',
                                   backref=db.backref('banned_by', remote_side=[id]),
                                   foreign_keys=[banned_by_id])

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    # NEW: Helper methods for user management
    def get_review_count(self):
        """Get total number of reviews by this user"""
        return self.reviews.count()

    def get_media_link_count(self):
        """Get total number of media links by this user"""
        return MediaLink.query.filter_by(user_id=self.id).count()

    def get_verified_media_count(self):
        """Get count of verified media links"""
        return MediaLink.query.filter_by(user_id=self.id, is_verified=True).count()

    def update_last_activity(self):
        """Update the last activity timestamp"""
        self.last_activity = datetime.utcnow()
        db.session.commit()

    def ban(self, banned_by_user, reason):
        """Ban this user"""
        self.is_banned = True
        self.ban_reason = reason
        self.banned_at = datetime.utcnow()
        self.banned_by_id = banned_by_user.id

        # Add to banned_users table to prevent re-registration
        banned_record = BannedUser(
            username=self.username,
            email=self.email,
            user_id=self.id,
            ban_reason=reason,
            banned_by_id=banned_by_user.id
        )
        db.session.add(banned_record)
        db.session.commit()

    def unban(self):
        """Unban this user"""
        self.is_banned = False
        self.ban_reason = None
        self.banned_at = None
        self.banned_by_id = None

        # Mark as unbanned in banned_users table (don't delete - keep history)
        banned_record = BannedUser.query.filter_by(
            username=self.username,
            email=self.email,
            is_unbanned=False
        ).first()
        if banned_record:
            banned_record.is_unbanned = True
            banned_record.unbanned_at = datetime.utcnow()

        db.session.commit()

    def __repr__(self):
        return f'<User {self.username}>'


class BannedUser(db.Model):
    """
    Track banned users to prevent re-registration with same username/email.
    This table persists even if the User record is deleted.
    """
    __tablename__ = 'banned_user'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), nullable=False, index=True)
    email = db.Column(db.String(120), nullable=False, index=True)
    user_id = db.Column(db.Integer)  # Original user ID (may be null if user deleted)

    # Ban details
    ban_reason = db.Column(db.Text, nullable=False)
    banned_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    banned_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Unban tracking
    is_unbanned = db.Column(db.Boolean, default=False, nullable=False, index=True)
    unbanned_at = db.Column(db.DateTime)
    unban_reason = db.Column(db.Text)

    # Relationships
    banned_by = db.relationship('User', foreign_keys=[banned_by_id])

    @staticmethod
    def is_banned(username=None, email=None):
        """
        Check if a username or email is currently banned.
        Returns True if banned, False otherwise.
        """
        query = BannedUser.query.filter_by(is_unbanned=False)

        conditions = []
        if username:
            conditions.append(db.func.lower(BannedUser.username) == username.lower())
        if email:
            conditions.append(db.func.lower(BannedUser.email) == email.lower())

        if conditions:
            query = query.filter(db.or_(*conditions))
            return query.first() is not None

        return False

    def __repr__(self):
        status = "UNBANNED" if self.is_unbanned else "BANNED"
        return f'<BannedUser {self.username} ({self.email}) - {status}>'


class AdminLog(db.Model):
    """
    Track all admin actions for accountability and audit trail.
    """
    __tablename__ = 'admin_log'

    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    action_type = db.Column(db.String(50), nullable=False, index=True)
    # Action types: 'ban_user', 'unban_user', 'delete_user', 'delete_review',
    #               'delete_media_link', 'approve_media_link', 'reject_media_link',
    #               'add_admin_note', 'edit_content'

    target_user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    target_review_id = db.Column(db.Integer, db.ForeignKey('review.id'))
    target_media_link_id = db.Column(db.Integer, db.ForeignKey('media_link.id'))

    details = db.Column(db.Text)  # JSON or text description of the action
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    admin = db.relationship('User', foreign_keys=[admin_id])
    target_user = db.relationship('User', foreign_keys=[target_user_id])
    target_review = db.relationship('Review', foreign_keys=[target_review_id])
    target_media_link = db.relationship('MediaLink', foreign_keys=[target_media_link_id])

    @staticmethod
    def log_action(admin_user, action_type, details=None, target_user=None,
                   target_review=None, target_media_link=None):
        """
        Create a new admin log entry.
        """
        log_entry = AdminLog(
            admin_id=admin_user.id,
            action_type=action_type,
            target_user_id=target_user.id if target_user else None,
            target_review_id=target_review.id if target_review else None,
            target_media_link_id=target_media_link.id if target_media_link else None,
            details=details
        )
        db.session.add(log_entry)
        db.session.commit()
        return log_entry

    def __repr__(self):
        return f'<AdminLog {self.action_type} by Admin {self.admin_id} at {self.timestamp}>'


class ContentFlag(db.Model):
    """User-reported flags for reviews and media links"""
    __tablename__ = 'content_flags'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)

    # Content being flagged (one will be set)
    review_id = db.Column(db.Integer, db.ForeignKey('review.id'), index=True)
    media_link_id = db.Column(db.Integer, db.ForeignKey('media_link.id'), index=True)

    # Flag details
    flag_type = db.Column(db.String(50),
                          nullable=False)  # spam, inappropriate, harassment, off-topic, misinformation, conflict, other
    description = db.Column(db.Text)

    # Resolution
    is_resolved = db.Column(db.Boolean, default=False, nullable=False, index=True)
    resolved_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    resolved_at = db.Column(db.DateTime)
    resolution_action = db.Column(db.String(50))  # dismissed, content_deleted, user_banned, user_warned
    resolution_notes = db.Column(db.Text)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    flagger = db.relationship('User', foreign_keys=[user_id])
    resolved_by = db.relationship('User', foreign_keys=[resolved_by_id])
    review = db.relationship('Review', backref='flags')
    media_link = db.relationship('MediaLink', backref='flags')

    def __repr__(self):
        return f'<ContentFlag {self.id} - {self.flag_type}>'