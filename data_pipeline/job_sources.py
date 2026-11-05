import re
from datetime import datetime, timezone
from html import unescape

import requests
from bs4 import BeautifulSoup


SOURCE_CATALOG = {
    'adzuna': {
        'name': 'Adzuna',
        'base_url': 'https://www.adzuna.com/',
    },
    'himalayas': {
        'name': 'Himalayas',
        'base_url': 'https://himalayas.app/jobs',
    },
    'jobicy': {
        'name': 'Jobicy',
        'base_url': 'https://jobicy.com/',
    },
    'remotive': {
        'name': 'Remotive',
        'base_url': 'https://remotive.com/remote-jobs',
    },
}


class JobSourceError(RuntimeError):
    pass


def _text(value):
    if not value:
        return ''
    if isinstance(value, (dict, list)):
        return ''
    value = unescape(str(value))
    if '<' not in value:
        return ' '.join(value.split())
    return ' '.join(BeautifulSoup(value, 'html.parser').stripped_strings)


def _date(value):
    if not value:
        return ''
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=timezone.utc).date().isoformat()
    try:
        return datetime.fromisoformat(str(value).replace('Z', '+00:00')).date().isoformat()
    except ValueError:
        return str(value)[:10]


def _salary(minimum, maximum, currency='', period=''):
    if minimum is None and maximum is None:
        return ''
    if minimum is None:
        value = str(maximum)
    elif maximum is None or minimum == maximum:
        value = str(minimum)
    else:
        value = f'{minimum} - {maximum}'
    return ' '.join(part for part in (value, currency, period) if part)


def _job(title, company, location, published_at, salary, description, url, reference=''):
    return {
        'title': _text(title),
        'company': _text(company),
        'location': _text(location),
        'published_at': _date(published_at),
        'salary': _text(salary),
        'description': _text(description),
        'source_url': _text(url),
        'reference': _text(reference),
    }


def parse_adzuna(payload):
    if not isinstance(payload, dict) or not isinstance(payload.get('results'), list):
        raise JobSourceError('Réponse Adzuna invalide.')
    jobs = []
    for item in payload['results']:
        if not isinstance(item, dict):
            continue
        company = item.get('company') or {}
        location = item.get('location') or {}
        jobs.append(_job(
            item.get('title'),
            company.get('display_name', '') if isinstance(company, dict) else '',
            location.get('display_name', '') if isinstance(location, dict) else '',
            item.get('created'),
            _salary(item.get('salary_min'), item.get('salary_max')),
            item.get('description'),
            item.get('redirect_url'),
            item.get('id'),
        ))
    return jobs


def parse_himalayas(payload):
    if not isinstance(payload, dict) or not isinstance(payload.get('jobs'), list):
        raise JobSourceError('Réponse Himalayas invalide.')
    jobs = []
    for item in payload['jobs']:
        if not isinstance(item, dict):
            continue
        jobs.append(_job(
            item.get('title'),
            item.get('companyName'),
            ', '.join(item.get('locationRestrictions') or []) or 'Remote',
            item.get('pubDate'),
            _salary(
                item.get('minSalary'),
                item.get('maxSalary'),
                item.get('currency'),
                item.get('salaryPeriod'),
            ),
            item.get('description') or item.get('excerpt'),
            item.get('applicationLink') or item.get('guid'),
            item.get('guid'),
        ))
    return jobs


def parse_jobicy(payload):
    if not isinstance(payload, dict) or not isinstance(payload.get('jobs'), list):
        raise JobSourceError('Réponse Jobicy invalide.')
    jobs = []
    for item in payload['jobs']:
        if not isinstance(item, dict):
            continue
        location = item.get('jobGeo') or item.get('jobIndustry') or ''
        if isinstance(location, list):
            location = ', '.join(location)
        jobs.append(_job(
            item.get('jobTitle'),
            item.get('companyName'),
            location,
            item.get('pubDate'),
            _salary(
                item.get('salaryMin'),
                item.get('salaryMax'),
                item.get('salaryCurrency'),
                item.get('salaryPeriod'),
            ),
            item.get('jobDescription') or item.get('jobExcerpt'),
            item.get('url'),
            item.get('id'),
        ))
    return jobs


def parse_remotive(payload):
    if not isinstance(payload, dict) or not isinstance(payload.get('jobs'), list):
        raise JobSourceError('Réponse Remotive invalide.')
    jobs = []
    for item in payload['jobs']:
        if not isinstance(item, dict):
            continue
        jobs.append(_job(
            item.get('title'),
            item.get('company_name'),
            item.get('candidate_required_location') or 'Remote',
            item.get('publication_date'),
            item.get('salary'),
            item.get('description'),
            item.get('url'),
            item.get('id'),
        ))
    return jobs


def fetch_source_jobs(source_slug, config, limit=50, session=None):
    session = session or requests.Session()
    session.headers.update({'User-Agent': 'CVBoostJobCollector/1.0'})
    if source_slug == 'adzuna':
        app_id = config.get('ADZUNA_APP_ID')
        app_key = config.get('ADZUNA_APP_KEY')
        if not app_id or not app_key:
            raise JobSourceError('ADZUNA_APP_ID et ADZUNA_APP_KEY doivent être configurés.')
        country = str(config.get('ADZUNA_COUNTRY', 'za')).lower()
        if not re.fullmatch(r'[a-z]{2}', country):
            raise JobSourceError('ADZUNA_COUNTRY doit être un code pays de deux lettres.')
        response = session.get(
            f'https://api.adzuna.com/v1/api/jobs/{country}/search/1',
            params={
                'app_id': app_id,
                'app_key': app_key,
                'results_per_page': min(limit, 50),
                'what': config.get('ADZUNA_QUERY', 'jobs'),
                'content-type': 'application/json',
            },
            timeout=20,
        )
        parser = parse_adzuna
    elif source_slug == 'himalayas':
        response = session.get(
            'https://himalayas.app/jobs/api',
            params={'limit': min(limit, 100)},
            timeout=20,
        )
        parser = parse_himalayas
    elif source_slug == 'jobicy':
        response = session.get(
            'https://jobicy.com/api/v2/remote-jobs',
            params={'count': min(limit, 50)},
            timeout=20,
        )
        parser = parse_jobicy
    elif source_slug == 'remotive':
        response = session.get(
            'https://remotive.com/api/remote-jobs',
            params={'limit': min(limit, 100)},
            timeout=20,
        )
        parser = parse_remotive
    else:
        raise JobSourceError(f'Source d’emploi inconnue : {source_slug}.')

    response.raise_for_status()
    try:
        payload = response.json()
    except (ValueError, requests.JSONDecodeError) as error:
        raise JobSourceError(f'La réponse de {SOURCE_CATALOG[source_slug]["name"]} n’est pas un JSON valide.') from error
    return parser(payload)[:limit]
