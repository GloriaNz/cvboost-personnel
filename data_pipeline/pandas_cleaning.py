import argparse
import re
from pathlib import Path

import pandas as pd


TEXT_COLUMNS = ('title', 'company', 'location', 'description', 'salary', 'source_url')
SKILL_KEYWORDS = (
    'python',
    'sql',
    'excel',
    'power bi',
    'tableau',
    'pandas',
    'machine learning',
    'gestion de projet',
    'comptabilité',
    'communication',
    'leadership',
    'anglais',
    'français',
)
AMOUNT_PATTERN = re.compile(r'\d(?:[\d\s.,]*\d)?')
CURRENCY_PATTERNS = (
    (re.compile(r'\b(?:usd|us\$|dollars?\s*(?:us|américains?)?)\b|\$', re.I), 'USD'),
    (re.compile(r'\b(?:cdf|fc)\b|\bfrancs?\s*congolais\b', re.I), 'CDF'),
)


def normalize_text(value):
    if pd.isna(value):
        return ''
    return re.sub(r'\s+', ' ', str(value)).strip()


def _parse_amount(value):
    normalized = value.replace(' ', '')
    if ',' in normalized and '.' in normalized:
        decimal_separator = ',' if normalized.rfind(',') > normalized.rfind('.') else '.'
        thousands_separator = '.' if decimal_separator == ',' else ','
        normalized = normalized.replace(thousands_separator, '').replace(decimal_separator, '.')
    elif ',' in normalized or '.' in normalized:
        separator = ',' if ',' in normalized else '.'
        whole, *fraction = normalized.split(separator)
        if len(fraction) == 1 and len(fraction[0]) == 3:
            normalized = whole + fraction[0]
        else:
            normalized = whole + ('.' + ''.join(fraction) if fraction else '')
    try:
        return float(normalized)
    except ValueError:
        return None


def parse_salary(value):
    text = normalize_text(value)
    if not text:
        return {'salary_min': None, 'salary_max': None, 'salary_currency': ''}

    amounts = [_parse_amount(match.group()) for match in AMOUNT_PATTERN.finditer(text)]
    amounts = [amount for amount in amounts if amount is not None]
    currency = next(
        (code for pattern, code in CURRENCY_PATTERNS if pattern.search(text)),
        '',
    )
    if not amounts:
        return {'salary_min': None, 'salary_max': None, 'salary_currency': currency}
    if len(amounts) == 1:
        return {'salary_min': amounts[0], 'salary_max': amounts[0], 'salary_currency': currency}
    return {
        'salary_min': min(amounts),
        'salary_max': max(amounts),
        'salary_currency': currency,
    }


def extract_skills(description):
    normalized = normalize_text(description).casefold()
    return [
        keyword for keyword in SKILL_KEYWORDS
        if re.search(r'(?<!\w)' + re.escape(keyword) + r'(?!\w)', normalized)
    ]


def clean_jobs(input_path):
    source = Path(input_path)
    if not source.exists():
        raise FileNotFoundError(f'Fichier source introuvable : {source}')

    frame = pd.read_csv(source, encoding='utf-8-sig', dtype=str)
    for column in TEXT_COLUMNS:
        if column not in frame.columns:
            frame[column] = ''
        frame[column] = frame[column].map(normalize_text)

    frame = frame[frame['title'].ne('')].copy()
    frame['company'] = frame['company'].replace('', 'Non précisé')
    frame['location'] = frame['location'].replace('', 'Non précisé')
    frame['description'] = frame['description'].fillna('')

    frame['_dedupe_key'] = frame['source_url'].str.casefold()
    missing_url = frame['_dedupe_key'].eq('')
    frame.loc[missing_url, '_dedupe_key'] = (
        frame.loc[missing_url, 'title'].str.casefold()
        + '|'
        + frame.loc[missing_url, 'company'].str.casefold()
    )
    frame = frame.drop_duplicates(subset='_dedupe_key', keep='first').drop(columns='_dedupe_key')

    salary_fields = pd.DataFrame(
        [parse_salary(value) for value in frame['salary']],
        index=frame.index,
        columns=('salary_min', 'salary_max', 'salary_currency'),
    )
    frame = pd.concat([frame.reset_index(drop=True), salary_fields.reset_index(drop=True)], axis=1)

    published = frame.get('published_at', pd.Series('', index=frame.index)).map(normalize_text)
    frame['published_date'] = pd.to_datetime(published, dayfirst=True, errors='coerce').dt.strftime('%Y-%m-%d')
    frame['published_date'] = frame['published_date'].fillna('')

    skills = frame['description'].map(extract_skills)
    frame['skills'] = skills.map(lambda items: ';'.join(items))
    all_skills = sorted({skill for items in skills for skill in items})
    for skill in all_skills:
        column_name = 'skill_' + re.sub(r'\W+', '_', skill.casefold()).strip('_')
        frame[column_name] = skills.map(lambda items: int(skill in items))

    return frame.reset_index(drop=True)


def main():
    parser = argparse.ArgumentParser(description='Nettoie les offres CSV et encode les compétences.')
    parser.add_argument('--input', default='data_pipeline/jobs_mediacongo.csv')
    parser.add_argument('--output', default='data_pipeline/jobs_clean.csv')
    args = parser.parse_args()

    cleaned = clean_jobs(args.input)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    cleaned.to_csv(output, index=False, encoding='utf-8-sig')
    print(f'{len(cleaned)} offres nettoyées : {output.resolve()}')


if __name__ == '__main__':
    main()
