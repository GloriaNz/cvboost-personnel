import argparse
import csv
import hashlib
import json
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


FAILED_OUTCOMES = {'rejected', 'failed', 'error'}
SUSPICIOUS_REASONS = {'unsupported_extension', 'file_too_large', 'request_too_large'}
OUTPUT_FIELDS = (
    'event_id',
    'timestamp',
    'user_id',
    'filename',
    'extension',
    'size_bytes',
    'outcome',
    'reason',
    'suspicious',
    'suspicious_reason',
)


@dataclass
class ParseResult:
    events: list
    errors: list


def parse_upload_logs(input_path, repeated_failure_threshold=3):
    if repeated_failure_threshold < 1:
        raise ValueError('repeated_failure_threshold doit être supérieur ou égal à 1.')

    path = Path(input_path)
    events = []
    errors = []

    with path.open('r', encoding='utf-8-sig') as log_file:
        for line_number, line in enumerate(log_file, start=1):
            if not line.strip():
                continue
            try:
                raw_event = json.loads(line)
                event = _normalize_event(raw_event, line)
            except (json.JSONDecodeError, TypeError, ValueError) as error:
                errors.append(f'Ligne {line_number}: {error}')
                continue
            events.append(event)

    failed_by_user = Counter(
        event['user_id'] for event in events
        if event['user_id'] and event['outcome'] in FAILED_OUTCOMES
    )
    for event in events:
        reasons = []
        if event['reason'] in SUSPICIOUS_REASONS:
            reasons.append(event['reason'])
        if (
            event['user_id']
            and event['outcome'] in FAILED_OUTCOMES
            and failed_by_user[event['user_id']] >= repeated_failure_threshold
        ):
            reasons.append('repeated_failed_uploads')
        event['suspicious'] = bool(reasons)
        event['suspicious_reason'] = ';'.join(reasons)

    return ParseResult(events=events, errors=errors)


def _normalize_event(raw_event, raw_line):
    if not isinstance(raw_event, dict):
        raise ValueError('Chaque entrée doit être un objet JSON.')
    if raw_event.get('event') != 'upload':
        raise ValueError("Le champ event doit valoir 'upload'.")

    timestamp = raw_event.get('timestamp')
    if not isinstance(timestamp, str):
        raise ValueError('timestamp doit être une date ISO-8601.')
    try:
        datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
    except ValueError as error:
        raise ValueError('timestamp doit être une date ISO-8601 valide.') from error

    outcome = raw_event.get('outcome')
    if outcome not in {'accepted', 'rejected', 'failed', 'error'}:
        raise ValueError('outcome doit être accepted, rejected, failed ou error.')

    size_bytes = raw_event.get('size_bytes')
    if size_bytes is not None:
        if isinstance(size_bytes, bool) or not isinstance(size_bytes, int) or size_bytes < 0:
            raise ValueError('size_bytes doit être un entier positif ou nul.')

    event_id = raw_event.get('event_id')
    if not isinstance(event_id, str) or not event_id:
        event_id = hashlib.sha256(raw_line.encode('utf-8')).hexdigest()

    extension = str(raw_event.get('extension') or '').lower().lstrip('.')
    return {
        'event_id': event_id,
        'timestamp': timestamp,
        'user_id': str(raw_event['user_id']) if raw_event.get('user_id') is not None else '',
        'filename': f'upload.{extension}' if extension else '',
        'extension': extension,
        'size_bytes': size_bytes,
        'outcome': outcome,
        'reason': str(raw_event.get('reason') or ''),
    }


def write_csv(events, output_path):
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('w', encoding='utf-8-sig', newline='') as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        writer.writerows(events)
    return output


def main():
    parser = argparse.ArgumentParser(description='Analyse les journaux JSONL d’upload CVBoost.')
    parser.add_argument('--input', required=True, help='Fichier JSONL produit par l’application.')
    parser.add_argument('--output', default='data_pipeline/upload_events.csv')
    parser.add_argument('--threshold', type=int, default=3, help='Échecs par utilisateur à signaler.')
    args = parser.parse_args()

    result = parse_upload_logs(args.input, args.threshold)
    output = write_csv(result.events, args.output)
    suspicious_count = sum(event['suspicious'] for event in result.events)
    print(
        f'{len(result.events)} événements analysés, '
        f'{suspicious_count} signalements, fichier : {output.resolve()}'
    )
    for error in result.errors:
        print(error, file=sys.stderr)
    if result.errors:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
