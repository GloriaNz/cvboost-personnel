import os
from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_login import current_user
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from werkzeug.middleware.proxy_fix import ProxyFix

db = SQLAlchemy()
login_manager = LoginManager()


def create_app(test_config=None):
    load_dotenv()
    app = Flask(__name__)

    app.config.update(
        SECRET_KEY=os.environ.get('SECRET_KEY'),
        SQLALCHEMY_DATABASE_URI=os.environ.get('DATABASE_URL', 'sqlite:///cvboost.db'),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        UPLOAD_FOLDER=os.environ.get(
            'UPLOAD_FOLDER',
            os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads')
        ),
        UPLOAD_AUDIT_LOG=os.environ.get(
            'UPLOAD_AUDIT_LOG',
            os.path.join(app.instance_path, 'upload_audit.jsonl')
        ),
        GROQ_API_KEY=os.environ.get('GROQ_API_KEY'),
        GROQ_MODEL=os.environ.get('GROQ_MODEL', 'qwen/qwen3.8-27b'),
        GROQ_TRANSLATION_MODEL=os.environ.get(
            'GROQ_TRANSLATION_MODEL',
            os.environ.get('GROQ_MODEL', 'qwen/qwen3.8-27b'),
        ),
        GROQ_TRANSCRIPTION_MODEL=os.environ.get(
            'GROQ_TRANSCRIPTION_MODEL',
            'whisper-large-v3-turbo',
        ),
        ASSISTANT_RATE_LIMIT_PER_MINUTE=int(
            os.environ.get('ASSISTANT_RATE_LIMIT_PER_MINUTE', '10')
        ),
        NLLB_BASE_MODEL=os.environ.get(
            'NLLB_BASE_MODEL',
            'facebook/nllb-200-distilled-600M',
        ),
        NLLB_ADAPTER_PATH=os.environ.get(
            'NLLB_ADAPTER_PATH',
            os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                'ai_engine',
                'models',
                'nllb-lora-lin-fra',
            ),
        ),
        GEMINI_API_KEY=os.environ.get('GEMINI_API_KEY'),
        GEMINI_MODEL=os.environ.get('GEMINI_MODEL', 'gemini-3.8-flash'),
        MISTRAL_API_KEY=os.environ.get('MISTRAL_API_KEY'),
        MISTRAL_MODEL=os.environ.get('MISTRAL_MODEL', 'mistral-small-latest'),
        JOB_OFFERS_FILE=os.environ.get(
            'JOB_OFFERS_FILE',
            os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                'data_pipeline',
                'jobs_clean.csv',
            ),
        ),
        JOB_ADMIN_EMAILS=os.environ.get('JOB_ADMIN_EMAILS', ''),
        MEDIACONGO_COLLECTION_APPROVED=(
            os.environ.get('MEDIACONGO_COLLECTION_APPROVED', '').lower() == 'true'
        ),
        REMOTIVE_COLLECTION_APPROVED=(
            os.environ.get('REMOTIVE_COLLECTION_APPROVED', '').lower() == 'true'
        ),
        JOB_SOURCE_SLUGS=tuple(
            slug.strip()
            for slug in os.environ.get(
                'JOB_SOURCE_SLUGS',
                'himalayas,jobicy',
            ).split(',')
            if slug.strip()
        ),
        ADZUNA_APP_ID=os.environ.get('ADZUNA_APP_ID', ''),
        ADZUNA_APP_KEY=os.environ.get('ADZUNA_APP_KEY', ''),
        ADZUNA_COUNTRY=os.environ.get('ADZUNA_COUNTRY', 'za'),
        ADZUNA_QUERY=os.environ.get('ADZUNA_QUERY', 'jobs'),
        JOB_ALERTS_ENABLED=os.environ.get('JOB_ALERTS_ENABLED', '').lower() == 'true',
        JOB_ALERT_SMTP_HOST=os.environ.get('JOB_ALERT_SMTP_HOST', ''),
        JOB_ALERT_SMTP_PORT=int(os.environ.get('JOB_ALERT_SMTP_PORT', '587')),
        JOB_ALERT_SMTP_USERNAME=os.environ.get('JOB_ALERT_SMTP_USERNAME', ''),
        JOB_ALERT_SMTP_PASSWORD=os.environ.get('JOB_ALERT_SMTP_PASSWORD', ''),
        JOB_ALERT_SMTP_USE_TLS=os.environ.get(
            'JOB_ALERT_SMTP_USE_TLS',
            'true',
        ).lower() == 'true',
        JOB_ALERT_SMTP_USE_SSL=os.environ.get(
            'JOB_ALERT_SMTP_USE_SSL',
            'false',
        ).lower() == 'true',
        JOB_ALERT_FROM_EMAIL=os.environ.get('JOB_ALERT_FROM_EMAIL', ''),
        MAX_CONTENT_LENGTH=5 * 1024 * 1024 + 64 * 1024,
        MAX_UPLOAD_SIZE=5 * 1024 * 1024,
        MAX_AUDIO_SIZE=5 * 1024 * 1024,
        ALLOWED_EXTENSIONS={'pdf', 'docx'},
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Lax',
        SESSION_COOKIE_SECURE=os.environ.get('COOKIE_SECURE', '').lower() == 'true',
        REMEMBER_COOKIE_HTTPONLY=True,
        REMEMBER_COOKIE_SECURE=os.environ.get('COOKIE_SECURE', '').lower() == 'true',
        TRUST_PROXY=os.environ.get('TRUST_PROXY', '').lower() == 'true',
    )
    if test_config:
        app.config.update(test_config)
    if not app.config.get('SECRET_KEY') or app.config['SECRET_KEY'].startswith('replace-'):
        raise RuntimeError('SECRET_KEY doit être défini dans l’environnement ou dans le fichier .env.')
    if app.config['TRUST_PROXY']:
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'main.login'
    login_manager.login_message = 'Veuillez vous connecter pour accéder à cette page.'
    login_manager.login_message_category = 'warning'

    # Register blueprints
    from app.routes import main
    app.register_blueprint(main)

    from app.forms import LogoutForm
    from app.audit import write_upload_audit

    @app.context_processor
    def inject_logout_form():
        return {'logout_form': LogoutForm()}

    @app.errorhandler(413)
    def log_request_too_large(error):
        if request.path == '/upload' and request.method == 'POST':
            write_upload_audit(
                current_user.get_id(),
                '',
                None,
                'rejected',
                'request_too_large',
            )
        if (
            request.path.endswith('/interview/audio')
            or request.path.startswith('/api/assistant/conversations/')
            and request.path.endswith('/audio')
        ) and request.method == 'POST':
            return jsonify(error='Le fichier audio dépasse la limite de 5 Mo.'), 413
        return error

    # Ensure uploads directory exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    return app
