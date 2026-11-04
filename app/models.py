from app import db, login_manager
from flask_login import UserMixin
from datetime import datetime, timezone
import json
from sqlalchemy import UniqueConstraint


def utc_now():
    return datetime.now(timezone.utc)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


class User(db.Model, UserMixin):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    prenom = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    date_inscription = db.Column(db.DateTime, default=utc_now)

    cvs = db.relationship('CV', backref='owner', lazy=True)

    def __repr__(self):
        return f'<User {self.email}>'


class CV(db.Model):
    __tablename__ = 'cvs'

    id = db.Column(db.Integer, primary_key=True)
    filename_original = db.Column(db.String(255), nullable=False)
    filename_stored = db.Column(db.String(255), nullable=False, unique=True)
    date_upload = db.Column(db.DateTime, default=utc_now)
    statut = db.Column(db.String(50), default='En attente')
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    analyses = db.relationship(
        'AIAnalysis',
        backref='cv',
        lazy=True,
        cascade='all, delete-orphan',
    )

    def __repr__(self):
        return f'<CV {self.filename_original}>'


class AIAnalysis(db.Model):
    __tablename__ = 'ai_analyses'

    id = db.Column(db.Integer, primary_key=True)
    cv_id = db.Column(db.Integer, db.ForeignKey('cvs.id'), nullable=False, index=True)
    job_description = db.Column(db.Text, nullable=False)
    summary = db.Column(db.Text, nullable=False)
    match_score = db.Column(db.Integer, nullable=False)
    strengths_json = db.Column(db.Text, nullable=False, default='[]')
    gaps_json = db.Column(db.Text, nullable=False, default='[]')
    interview_history_json = db.Column(db.Text, nullable=False, default='[]')
    date_analysis = db.Column(db.DateTime, default=utc_now, nullable=False)

    @property
    def strengths(self):
        return json.loads(self.strengths_json)

    @property
    def gaps(self):
        return json.loads(self.gaps_json)

    @property
    def interview_history(self):
        return json.loads(self.interview_history_json)


class AssistantConversation(db.Model):
    __tablename__ = 'assistant_conversations'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    context_cv_id = db.Column(db.Integer, db.ForeignKey('cvs.id'), nullable=True)
    title = db.Column(db.String(120), nullable=False, default='Nouvelle conversation')
    language = db.Column(db.String(2), nullable=False, default='fr')
    use_personal_context = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)
    updated_at = db.Column(db.DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    messages = db.relationship(
        'AssistantMessage',
        backref='conversation',
        lazy=True,
        cascade='all, delete-orphan',
        order_by='AssistantMessage.created_at',
    )


class AssistantMessage(db.Model):
    __tablename__ = 'assistant_messages'

    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(
        db.Integer,
        db.ForeignKey('assistant_conversations.id'),
        nullable=False,
        index=True,
    )
    role = db.Column(db.String(10), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)


class AssistantRateLimit(db.Model):
    __tablename__ = 'assistant_rate_limits'
    __table_args__ = (
        UniqueConstraint('user_id', name='uq_assistant_rate_limit_user'),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    window_start = db.Column(db.Integer, nullable=False)
    request_count = db.Column(db.Integer, nullable=False, default=0)


class JobSource(db.Model):
    __tablename__ = 'job_sources'

    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(80), nullable=False, unique=True)
    name = db.Column(db.String(120), nullable=False)
    base_url = db.Column(db.String(500), nullable=False)
    enabled = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)

    offers = db.relationship('JobOffer', backref='source', lazy=True)
    sync_runs = db.relationship('JobSyncRun', backref='source', lazy=True)


class JobOffer(db.Model):
    __tablename__ = 'job_offers'
    __table_args__ = (
        UniqueConstraint('source_id', 'source_url', name='uq_job_offer_source_url'),
        UniqueConstraint('source_id', 'external_id', name='uq_job_offer_external_id'),
    )

    id = db.Column(db.Integer, primary_key=True)
    source_id = db.Column(db.Integer, db.ForeignKey('job_sources.id'), nullable=False, index=True)
    external_id = db.Column(db.String(160), nullable=True)
    source_url = db.Column(db.String(1000), nullable=False)
    content_hash = db.Column(db.String(64), nullable=False, index=True)
    title = db.Column(db.String(300), nullable=False)
    company = db.Column(db.String(250), nullable=False, default='')
    description = db.Column(db.Text, nullable=False, default='')
    skills_json = db.Column(db.Text, nullable=False, default='[]')
    location = db.Column(db.String(250), nullable=False, default='')
    contract_type = db.Column(db.String(80), nullable=False, default='')
    experience_level = db.Column(db.String(80), nullable=False, default='')
    is_remote = db.Column(db.Boolean, nullable=False, default=False)
    published_at = db.Column(db.Date, nullable=True)
    deadline = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(20), nullable=False, default='active', index=True)
    first_seen_at = db.Column(db.DateTime, nullable=False, default=utc_now)
    last_seen_at = db.Column(db.DateTime, nullable=False, default=utc_now)


class JobSyncRun(db.Model):
    __tablename__ = 'job_sync_runs'

    id = db.Column(db.Integer, primary_key=True)
    source_id = db.Column(db.Integer, db.ForeignKey('job_sources.id'), nullable=False, index=True)
    started_at = db.Column(db.DateTime, nullable=False, default=utc_now)
    completed_at = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(20), nullable=False, default='running')
    fetched_count = db.Column(db.Integer, nullable=False, default=0)
    added_count = db.Column(db.Integer, nullable=False, default=0)
    updated_count = db.Column(db.Integer, nullable=False, default=0)
    error_message = db.Column(db.String(500), nullable=False, default='')


class JobAlertPreference(db.Model):
    __tablename__ = 'job_alert_preferences'
    __table_args__ = (
        UniqueConstraint('user_id', name='uq_job_alert_preference_user'),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    keywords = db.Column(db.String(500), nullable=False, default='')
    skills_json = db.Column(db.Text, nullable=False, default='[]')
    location = db.Column(db.String(200), nullable=False, default='')
    contract_type = db.Column(db.String(80), nullable=False, default='')
    experience_level = db.Column(db.String(80), nullable=False, default='')
    is_remote = db.Column(db.Boolean, nullable=False, default=False)
    enabled = db.Column(db.Boolean, nullable=False, default=False)
    updated_at = db.Column(db.DateTime, nullable=False, default=utc_now, onupdate=utc_now)


class JobAlertDelivery(db.Model):
    __tablename__ = 'job_alert_deliveries'
    __table_args__ = (
        UniqueConstraint(
            'user_id',
            'job_offer_id',
            name='uq_job_alert_delivery_user_offer',
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    job_offer_id = db.Column(
        db.Integer,
        db.ForeignKey('job_offers.id'),
        nullable=False,
        index=True,
    )
    status = db.Column(db.String(20), nullable=False, default='pending')
    attempts = db.Column(db.Integer, nullable=False, default=0)
    last_attempt_at = db.Column(db.DateTime, nullable=True)
    sent_at = db.Column(db.DateTime, nullable=True)
    error_message = db.Column(db.String(160), nullable=False, default='')
