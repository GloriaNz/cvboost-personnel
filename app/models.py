from app import db, login_manager
from flask_login import UserMixin
from datetime import datetime, timezone
import json


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
