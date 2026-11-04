import csv
import hashlib
import json
import logging
import re
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlparse

import requests
from flask import current_app
from sqlalchemy.exc import SQLAlchemyError

from app import db
from data_pipeline.job_matching import MAX_JOB_FILE_BYTES, MAX_JOB_ROWS
from app.models import JobOffer, JobSource, JobSyncRun, utc_now
from data_pipeline.pandas_cleaning import extract_skills, normalize_text


logger = logging.getLogger(__name__)
MEDIACONGO_SOURCE = {
    'slug': 'mediacongo',
    'name': 'MediaCongo',
    'base_url': 'https://mediacongo.net/emplois.html',
}
_JOB_ID = re.compile(r'/emploi-societe-(\d+)_', re.I)
_DATE_FORMATS = ('%Y-%m-%d', '%d.%m.%Y', '%d/%m/%Y')


class JobSyncError(RuntimeError):
    pass


def _safe_source_url(value, source_slug):
    parsed = urlparse(normalize_text(value))
    allowed_hosts = {
        'mediacongo': {'mediacongo.net', 'www.mediacongo.net'},
    }
    if (
        source_slug not in allowed_hosts
        or parsed.scheme not in {'http', 'https'}
        or parsed.hostname not in allowed_hosts[source_slug]
        or parsed.username
        or parsed.password
    ):
        return ''
    return parsed.geturl()


def _parse_date(value):
    value = normalize_text(value)
    if not value:
        return None
    for date_format in _DATE_FORMATS:
        try:
            return datetime.strptime(value, date_format).date()
        except ValueError:
            continue
    return None


def _classify_job(job):
    text = ' '.join((
        job['title'],
        job['description'],
    )).casefold()
    contract_type = next(
        (
            name for pattern, name in (
                (r'\b(stage|internship)\b', 'Stage'),
                (r'\b(alternance|apprentissage)\b', 'Alternance'),
                (r'\b(cdi|permanent)\b', 'CDI'),
                (r'\b(cdd|contractuel)\b', 'CDD'),
                (r'\b(freelance|indépendant)\b', 'Freelance'),
            )
            if re.search(pattern, text)
        ),
        '',
    )
    experience = next(
        (
            name for pattern, name in (
                (r'\b(junior|débutant|entry.level)\b', 'Junior'),
                (r'\b(confirmé|confirmed|intermédiaire)\b', 'Confirmé'),
                (r'\b(senior|expérimenté)\b', 'Senior'),
            )
            if re.search(pattern, text)
        ),
        '',
    )
    return contract_type, experience, bool(
        re.search(r'\b(télétravail|remote|work from home)\b', text)
    )


def _normalize_job(row, source_slug):
    title = normalize_text(row.get('title', ''))
    source_url = _safe_source_url(row.get('source_url', ''), source_slug)
    if not title or not source_url:
        raise JobSyncError('Une offre ne contient pas de titre ou de lien source autorisé.')

    company = normalize_text(row.get('company', ''))
    location = normalize_text(row.get('location', ''))
    description = normalize_text(row.get('description', ''))
    skills = extract_skills(' '.join((
        title,
        description,
        normalize_text(row.get('skills', '')),
    )))
    external_id = normalize_text(row.get('reference', ''))
    if not external_id:
        match = _JOB_ID.search(urlparse(source_url).path)
        external_id = match.group(1) if match else ''
    contract_type, experience_level, is_remote = _classify_job({
        'title': title,
        'description': description,
    })
    published_at = _parse_date(row.get('published_date') or row.get('published_at', ''))
    deadline = _parse_date(row.get('deadline') or row.get('deadline_date', ''))
    content = '\n'.join((
        title.casefold(),
        company.casefold(),
        location.casefold(),
        description.casefold(),
        ';'.join(skills),
        contract_type.casefold(),
        experience_level.casefold(),
    ))
    return {
        'external_id': external_id or None,
        'source_url': source_url,
        'content_hash': hashlib.sha256(content.encode('utf-8')).hexdigest(),
        'title': title[:300],
        'company': company[:250],
        'description': description,
        'skills_json': json.dumps(skills, ensure_ascii=False),
        'location': location[:250],
        'contract_type': contract_type,
        'experience_level': experience_level,
        'is_remote': is_remote,
        'published_at': published_at,
        'deadline': deadline,
        'status': 'expired' if deadline and deadline < date.today() else 'active',
    }


def _ensure_mediacongo_source():
    source = JobSource.query.filter_by(slug=MEDIACONGO_SOURCE['slug']).first()
    if source is None:
        source = JobSource(**MEDIACONGO_SOURCE)
        db.session.add(source)
        db.session.commit()
    return source


def _mark_run_failed(run, error_message):
    run.status = 'failed'
    run.completed_at = utc_now()
    run.error_message = error_message[:500]
    db.session.commit()


def sync_job_rows(source, rows, run=None):
    rows = list(rows)
    if run is None:
        run = JobSyncRun(source_id=source.id)
        db.session.add(run)
        db.session.commit()
    run.fetched_count = len(rows)
    db.session.commit()

    added = 0
    updated = 0
    try:
        for row in rows:
            normalized = _normalize_job(row, source.slug)
            existing = None
            if normalized['external_id']:
                existing = JobOffer.query.filter_by(
                    source_id=source.id,
                    external_id=normalized['external_id'],
                ).first()
            if existing is None:
                existing = JobOffer.query.filter_by(
                    source_id=source.id,
                    source_url=normalized['source_url'],
                ).first()
            if existing is None:
                existing = JobOffer.query.filter_by(
                    source_id=source.id,
                    content_hash=normalized['content_hash'],
                ).first()

            if existing is None:
                existing = JobOffer(source_id=source.id, **normalized)
                db.session.add(existing)
                added += 1
            else:
                if existing.content_hash != normalized['content_hash']:
                    updated += 1
                for field, value in normalized.items():
                    setattr(existing, field, value)
                existing.last_seen_at = utc_now()

        run.status = 'completed'
        run.added_count = added
        run.updated_count = updated
        run.completed_at = utc_now()
        db.session.commit()
    except (JobSyncError, SQLAlchemyError) as error:
        db.session.rollback()
        failed_run = db.session.get(JobSyncRun, run.id)
        if failed_run is not None:
            error_message = (
                str(error)[:500] if isinstance(error, JobSyncError)
                else 'Erreur de stockage des offres.'
            )
            _mark_run_failed(failed_run, error_message)
        logger.warning('Job synchronization failed for source %s.', source.slug)
        raise JobSyncError(
            'La synchronisation des offres a échoué ; les annonces n’ont pas été mises à jour.'
        ) from error

    return run


def import_csv(path, source=None):
    source = source or _ensure_mediacongo_source()
    run = JobSyncRun(source_id=source.id)
    db.session.add(run)
    db.session.commit()
    input_path = Path(path)
    try:
        if not input_path.is_file():
            raise JobSyncError('Le fichier CSV des offres est introuvable.')
        if input_path.stat().st_size > MAX_JOB_FILE_BYTES:
            raise JobSyncError('Le fichier CSV des offres dépasse la limite de 10 Mo.')
        with input_path.open('r', encoding='utf-8-sig', newline='') as csv_file:
            rows = []
            for row_number, row in enumerate(csv.DictReader(csv_file), start=1):
                if row_number > MAX_JOB_ROWS:
                    raise JobSyncError(
                        f'Le CSV dépasse la limite de {MAX_JOB_ROWS} offres.'
                    )
                rows.append(row)
    except JobSyncError as error:
        _mark_run_failed(run, str(error))
        raise
    except (OSError, UnicodeError, csv.Error) as error:
        _mark_run_failed(run, 'Impossible de lire le fichier CSV des offres.')
        raise JobSyncError('Impossible de lire le fichier CSV des offres.') from error
    return sync_job_rows(source, rows, run)


def collect_mediacongo(limit=50):
    from data_pipeline.scraper_jobs import MediaCongoScraper

    if not current_app.config.get('MEDIACONGO_COLLECTION_APPROVED'):
        raise JobSyncError(
            'La collecte périodique est désactivée. Vérifiez les conditions d’utilisation '
            'de MediaCongo puis définissez MEDIACONGO_COLLECTION_APPROVED=true, '
            'ou importez un CSV autorisé.'
        )
    source = _ensure_mediacongo_source()
    run = JobSyncRun(source_id=source.id)
    db.session.add(run)
    db.session.commit()
    try:
        rows = MediaCongoScraper().scrape(limit=limit)
    except (requests.RequestException, PermissionError, RuntimeError) as error:
        _mark_run_failed(run, f'Échec de la collecte ({type(error).__name__}).')
        raise JobSyncError(
            'La collecte MediaCongo a échoué ; vérifiez la connexion et les règles de collecte.'
        ) from error
    return sync_job_rows(source, rows, run)


def refresh_expired_offers():
    today = date.today()
    count = JobOffer.query.filter(
        JobOffer.deadline.isnot(None),
        JobOffer.deadline < today,
        JobOffer.status != 'expired',
    ).update(
        {'status': 'expired'},
        synchronize_session=False,
    )
    db.session.commit()
    return count
