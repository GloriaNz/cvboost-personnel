import os
import uuid
import json
import logging
import io
from urllib.parse import urljoin, urlparse
from flask import Blueprint, abort, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

from app import db
from app.audit import write_upload_audit
from app.models import AIAnalysis, User, CV
from app.forms import (
    InterviewAnswerForm,
    InterviewAudioForm,
    LoginForm,
    LogoutForm,
    MatchForm,
    RegisterForm,
    UploadForm,
)
from app.ia import (
    AIConfigurationError,
    AIServiceError,
    DocumentExtractionError,
    analyze_profile,
    extract_cv_text,
    generate_interview_question,
    transcribe_audio,
)
from data_pipeline.job_matching import JobOffersError, rank_job_offers

main = Blueprint('main', __name__)
logger = logging.getLogger(__name__)


def allowed_file(filename):
    allowed = current_app.config.get('ALLOWED_EXTENSIONS', {'pdf', 'docx'})
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed


def is_safe_redirect_target(target):
    if not target:
        return False
    host_url = urlparse(request.host_url)
    redirect_url = urlparse(urljoin(request.host_url, target))
    return redirect_url.scheme in {'http', 'https'} and host_url.netloc == redirect_url.netloc


# ── Home ──────────────────────────────────────────────────────────────────────
@main.route('/')
def index():
    return render_template('index.html')


# ── Register ──────────────────────────────────────────────────────────────────
@main.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    form = RegisterForm()
    if form.validate_on_submit():
        hashed_password = generate_password_hash(form.password.data)
        user = User(
            nom=form.nom.data,
            prenom=form.prenom.data,
            email=form.email.data,
            password_hash=hashed_password
        )
        db.session.add(user)
        db.session.commit()
        flash('Compte créé avec succès ! Vous pouvez maintenant vous connecter.', 'success')
        return redirect(url_for('main.login'))

    return render_template('register.html', form=form)


# ── Login ─────────────────────────────────────────────────────────────────────
@main.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and check_password_hash(user.password_hash, form.password.data):
            login_user(user)
            next_page = request.args.get('next')
            flash(f'Bienvenue, {user.prenom} !', 'success')
            if is_safe_redirect_target(next_page):
                return redirect(next_page)
            return redirect(url_for('main.index'))
        else:
            flash('Email ou mot de passe incorrect.', 'danger')

    return render_template('login.html', form=form)


# ── Logout ────────────────────────────────────────────────────────────────────
@main.route('/logout', methods=['POST'])
@login_required
def logout():
    form = LogoutForm()
    if form.validate_on_submit():
        logout_user()
        flash('Vous avez été déconnecté.', 'info')
        return redirect(url_for('main.index'))
    abort(400, description='Formulaire de déconnexion invalide.')


# ── Upload ────────────────────────────────────────────────────────────────────
@main.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    form = UploadForm()
    file = request.files.get('cv')
    filename = file.filename if file else ''
    file_size = None
    if file and filename:
        file.stream.seek(0, os.SEEK_END)
        file_size = file.stream.tell()
        file.stream.seek(0)

    if form.validate_on_submit():
        original_name = secure_filename(file.filename)
        if not allowed_file(original_name):
            write_upload_audit(
                current_user.id, filename, file_size, 'rejected', 'unsupported_extension'
            )
            flash('Le nom du fichier doit se terminer par .pdf ou .docx.', 'danger')
            return render_template('upload.html', form=form), 400

        if file_size is not None and file_size > current_app.config['MAX_UPLOAD_SIZE']:
            write_upload_audit(
                current_user.id, filename, file_size, 'rejected', 'file_too_large'
            )
            flash('Le fichier ne doit pas dépasser 5 Mo.', 'danger')
            return render_template('upload.html', form=form), 413

        ext = original_name.rsplit('.', 1)[1].lower()
        stored_name = f"{uuid.uuid4().hex}.{ext}"
        save_path = os.path.join(current_app.config['UPLOAD_FOLDER'], stored_name)
        file.save(save_path)

        cv = CV(
            filename_original=original_name,
            filename_stored=stored_name,
            user_id=current_user.id
        )
        db.session.add(cv)
        db.session.commit()
        write_upload_audit(current_user.id, original_name, file_size, 'accepted')
        flash('Votre CV a été envoyé avec succès !', 'success')
        return redirect(url_for('main.result', cv_id=cv.id))

    if request.method == 'POST':
        extension = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
        reason = 'missing_file' if not filename else 'invalid_form'
        if extension not in current_app.config['ALLOWED_EXTENSIONS']:
            reason = 'unsupported_extension'
        elif file_size is not None and file_size > current_app.config['MAX_UPLOAD_SIZE']:
            reason = 'file_too_large'
        write_upload_audit(current_user.id, filename, file_size, 'rejected', reason)

    return render_template('upload.html', form=form)


# ── History ───────────────────────────────────────────────────────────────────
@main.route('/history')
@login_required
def history():
    cvs = CV.query.filter_by(user_id=current_user.id).order_by(CV.date_upload.desc()).all()
    return render_template('history.html', cvs=cvs)


# ── Interview practice ────────────────────────────────────────────────────────
@main.route('/interview')
@login_required
def interview():
    cvs = CV.query.filter_by(user_id=current_user.id).order_by(CV.date_upload.desc()).all()
    analyses = AIAnalysis.query.join(CV).filter(
        CV.user_id == current_user.id
    ).order_by(AIAnalysis.date_analysis.desc()).all()
    analyses_by_cv = {}
    for analysis in analyses:
        analyses_by_cv.setdefault(analysis.cv_id, analysis)
    return render_template('interview.html', cvs=cvs, analyses_by_cv=analyses_by_cv)


@main.route('/interview/<int:analysis_id>')
@login_required
def interview_room(analysis_id):
    analysis = db.get_or_404(AIAnalysis, analysis_id)
    cv = analysis.cv
    if cv.user_id != current_user.id:
        flash('Accès non autorisé.', 'danger')
        return redirect(url_for('main.history'))
    return render_template(
        'interview_room.html',
        analysis=analysis,
        cv=cv,
        answer_form=InterviewAnswerForm(),
    )


# ── Result ────────────────────────────────────────────────────────────────────
@main.route('/result/<int:cv_id>')
@login_required
def result(cv_id):
    cv = db.get_or_404(CV, cv_id)
    if cv.user_id != current_user.id:
        flash('Accès non autorisé.', 'danger')
        return redirect(url_for('main.history'))
    analysis = AIAnalysis.query.filter_by(cv_id=cv.id).order_by(
        AIAnalysis.date_analysis.desc()
    ).first()
    match_form = MatchForm()
    if analysis:
        match_form.job_description.data = analysis.job_description
    job_offers = []
    job_offers_error = None
    job_offers_path = current_app.config['JOB_OFFERS_FILE']
    if os.path.isfile(job_offers_path):
        try:
            cv_path = os.path.join(current_app.config['UPLOAD_FOLDER'], cv.filename_stored)
            extension = cv.filename_stored.rsplit('.', 1)[-1].lower()
            cv_text = extract_cv_text(cv_path, extension)
            job_offers = rank_job_offers(job_offers_path, cv_text)
        except (DocumentExtractionError, JobOffersError) as error:
            job_offers_error = str(error)
            logger.warning('Offres non disponibles pour le document %s: %s', cv.id, error)
    return render_template(
        'result.html',
        cv=cv,
        analysis=analysis,
        match_form=match_form,
        answer_form=InterviewAnswerForm(),
        job_offers=job_offers,
        job_offers_error=job_offers_error,
    )


@main.route('/result/<int:cv_id>/analyze', methods=['POST'])
@login_required
def analyze_cv(cv_id):
    cv = db.get_or_404(CV, cv_id)
    if cv.user_id != current_user.id:
        flash('Accès non autorisé.', 'danger')
        return redirect(url_for('main.history'))

    form = MatchForm()
    if not form.validate_on_submit():
        flash('La description de l’offre doit contenir entre 30 et 12 000 caractères.', 'danger')
        return redirect(url_for('main.result', cv_id=cv.id))

    try:
        cv_path = os.path.join(current_app.config['UPLOAD_FOLDER'], cv.filename_stored)
        extension = cv.filename_stored.rsplit('.', 1)[-1].lower()
        cv_text = extract_cv_text(cv_path, extension)
        result = analyze_profile(
            cv_text,
            form.job_description.data.strip(),
            current_app.config.get('GROQ_API_KEY'),
            current_app.config['GROQ_MODEL'],
        )
    except (AIConfigurationError, AIServiceError, DocumentExtractionError) as error:
        logger.warning('Analyse CV impossible pour le document %s: %s', cv.id, error)
        flash(str(error), 'danger')
        return redirect(url_for('main.result', cv_id=cv.id))

    analysis = AIAnalysis.query.filter_by(cv_id=cv.id).order_by(
        AIAnalysis.date_analysis.desc()
    ).first()
    if analysis is None:
        analysis = AIAnalysis(cv_id=cv.id)
        db.session.add(analysis)
    analysis.job_description = form.job_description.data.strip()
    analysis.summary = result['summary']
    analysis.match_score = result['matching_percentage']
    analysis.strengths_json = json.dumps(result['strengths'], ensure_ascii=False)
    analysis.gaps_json = json.dumps(result['gaps'], ensure_ascii=False)
    analysis.interview_history_json = json.dumps(
        [{'question': result['first_interview_question'], 'answer': ''}],
        ensure_ascii=False,
    )
    cv.statut = 'Analyse terminée'
    db.session.commit()
    flash('Analyse du profil terminée. Le score est indicatif et doit être vérifié humainement.', 'success')
    return redirect(url_for('main.result', cv_id=cv.id, _anchor='interview'))


@main.route('/analysis/<int:analysis_id>/interview', methods=['POST'])
@login_required
def answer_interview(analysis_id):
    analysis = db.get_or_404(AIAnalysis, analysis_id)
    cv = analysis.cv
    if cv.user_id != current_user.id:
        flash('Accès non autorisé.', 'danger')
        return redirect(url_for('main.history'))

    ref = request.referrer or ''
    target_redirect = url_for('main.interview_room', analysis_id=analysis.id) if ('/interview/' in ref or 'room' in ref) else url_for('main.result', cv_id=cv.id, _anchor='interview')

    form = InterviewAnswerForm()
    if not form.validate_on_submit():
        flash('Votre réponse doit contenir entre 2 et 4 000 caractères.', 'danger')
        return redirect(target_redirect)

    history = analysis.interview_history
    if len(history) > 10:
        flash('La simulation a atteint sa limite. Relancez une analyse pour recommencer.', 'warning')
        return redirect(target_redirect)
    if not history or history[-1].get('answer'):
        flash('Aucune question en attente de réponse.', 'danger')
        return redirect(target_redirect)

    history[-1]['answer'] = form.answer.data.strip()
    if len(history) == 10:
        analysis.interview_history_json = json.dumps(history, ensure_ascii=False)
        db.session.commit()
        flash('Simulation terminée : les 10 réponses ont été enregistrées.', 'success')
        return redirect(target_redirect)

    try:
        cv_path = os.path.join(current_app.config['UPLOAD_FOLDER'], cv.filename_stored)
        extension = cv.filename_stored.rsplit('.', 1)[-1].lower()
        cv_text = extract_cv_text(cv_path, extension)
        question = generate_interview_question(
            cv_text,
            analysis.job_description,
            analysis.summary,
            history,
            form.answer.data.strip(),
            current_app.config.get('GROQ_API_KEY'),
            current_app.config['GROQ_MODEL'],
        )
    except (AIConfigurationError, AIServiceError, DocumentExtractionError) as error:
        logger.warning('Simulation entretien impossible pour le document %s: %s', cv.id, error)
        flash(str(error), 'danger')
        return redirect(target_redirect)

    history.append({'question': question, 'answer': ''})
    analysis.interview_history_json = json.dumps(history, ensure_ascii=False)
    db.session.commit()
    flash('Réponse enregistrée. Voici la question suivante.', 'success')
    return redirect(target_redirect)


@main.route('/analysis/<int:analysis_id>/interview/audio', methods=['POST'])
@login_required
def transcribe_interview_audio(analysis_id):
    analysis = db.get_or_404(AIAnalysis, analysis_id)
    if analysis.cv.user_id != current_user.id:
        abort(404)

    form = InterviewAudioForm()
    if not form.validate_on_submit():
        return {'error': 'Enregistrement audio absent ou format non pris en charge.'}, 400

    history = analysis.interview_history
    if not history or history[-1].get('answer') or len(history) >= 10:
        return {'error': 'Aucune question ne peut être transcrite pour cette simulation.'}, 409

    audio = form.audio.data
    audio_bytes = audio.stream.read(current_app.config['MAX_AUDIO_SIZE'] + 1)
    if len(audio_bytes) > current_app.config['MAX_AUDIO_SIZE']:
        return {'error': 'Le fichier audio ne doit pas dépasser 5 Mo.'}, 413

    filename = secure_filename(audio.filename)
    try:
        transcript = transcribe_audio(
            io.BytesIO(audio_bytes),
            filename,
            current_app.config.get('GROQ_API_KEY'),
            current_app.config['GROQ_TRANSCRIPTION_MODEL'],
        )
    except (AIConfigurationError, AIServiceError) as error:
        logger.warning('Transcription audio impossible pour l’analyse %s: %s', analysis.id, error)
        return {'error': str(error)}, 503

    if len(transcript) > 4000:
        return {
            'error': 'La transcription dépasse 4 000 caractères. Enregistrez une réponse plus courte.'
        }, 422
    return {'transcript': transcript}
