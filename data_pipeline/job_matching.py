import csv
from pathlib import Path
from urllib.parse import urlparse

from data_pipeline.pandas_cleaning import extract_skills, normalize_text


MAX_JOB_FILE_BYTES = 10 * 1024 * 1024
MAX_JOB_ROWS = 2000
MAX_ANALYSIS_TEXT_LENGTH = 12000
ALLOWED_JOB_HOSTS = {
    'adzuna.com',
    'himalayas.app',
    'jobicy.com',
    'mediacongo.net',
    'remotive.com',
}


class JobOffersError(RuntimeError):
    pass


def _analysis_text(job):
    fields = (
        ('Intitulé', job['title']),
        ('Entreprise', job['company']),
        ('Lieu', job['location']),
        ('Date de publication', job['published_at']),
        ('Rémunération', job['salary']),
        ('Compétences mentionnées', ', '.join(job['skills'])),
        ('Description', job['description']),
    )
    content = '\n'.join(f'{label} : {value}' for label, value in fields if value)
    if len(content) < 30:
        return ''
    if len(content) > MAX_ANALYSIS_TEXT_LENGTH:
        raise JobOffersError(
            f"L’offre « {job['title']} » dépasse la limite de 12 000 caractères et ne peut pas être analysée."
        )
    return content


def _safe_source_url(value):
    parsed = urlparse(value)
    if (
        parsed.scheme not in {'http', 'https'}
        or not parsed.hostname
        or not any(
            parsed.hostname == host or parsed.hostname.endswith(f'.{host}')
            for host in ALLOWED_JOB_HOSTS
        )
        or parsed.username
        or parsed.password
    ):
        return ''
    return parsed.geturl()


def rank_job_records(records, cv_text, limit=10):
    cv_skills = set(extract_skills(cv_text))
    jobs = []
    for row_number, row in enumerate(records, start=1):
        title = normalize_text(row.get('title', ''))
        if not title:
            continue
        description = normalize_text(row.get('description', ''))
        skills = extract_skills(' '.join((
            title,
            description,
            normalize_text(row.get('skills', '')),
        )))
        job = {
            'title': title,
            'company': normalize_text(row.get('company', '')),
            'location': normalize_text(row.get('location', '')),
            'published_at': normalize_text(
                row.get('published_date') or row.get('published_at', '')
            ),
            'salary': normalize_text(row.get('salary', '')),
            'description': description,
            'skills': skills,
            'matching_skills': sorted(cv_skills.intersection(skills)),
            'source_url': _safe_source_url(normalize_text(row.get('source_url', ''))),
            'source_name': normalize_text(row.get('source_name', '')),
            'position': row_number,
        }
        try:
            job['analysis_text'] = _analysis_text(job)
            job['analysis_error'] = ''
        except JobOffersError as error:
            job['analysis_text'] = ''
            job['analysis_error'] = str(error)
        jobs.append(job)

    jobs.sort(key=lambda job: (-len(job['matching_skills']), job['position']))
    return jobs[:limit]


def rank_job_offers(path, cv_text, limit=10):
    source = Path(path)
    if not source.is_file():
        return []
    try:
        source_size = source.stat().st_size
    except OSError as error:
        raise JobOffersError('Impossible d’accéder au fichier CSV des offres.') from error
    if source_size > MAX_JOB_FILE_BYTES:
        raise JobOffersError('Le fichier des offres dépasse la limite de 10 Mo.')

    rows = []
    try:
        with source.open('r', encoding='utf-8-sig', newline='') as csv_file:
            reader = csv.DictReader(csv_file)
            if not reader.fieldnames or 'title' not in reader.fieldnames:
                raise JobOffersError('Le CSV des offres doit contenir une colonne « title ».')
            for row_number, row in enumerate(reader, start=1):
                if row_number > MAX_JOB_ROWS:
                    raise JobOffersError(
                        f'Le CSV dépasse la limite de {MAX_JOB_ROWS} offres.'
                    )
                rows.append(row)
    except (OSError, UnicodeError, csv.Error) as error:
        raise JobOffersError('Impossible de lire le fichier CSV des offres.') from error

    return rank_job_records(rows, cv_text, limit=limit)
