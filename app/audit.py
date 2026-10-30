import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from flask import current_app


def write_upload_audit(user_id, filename, size_bytes, outcome, reason=''):
    extension = Path(filename or '').suffix.lower().lstrip('.')
    event = {
        'event_id': uuid.uuid4().hex,
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'event': 'upload',
        'user_id': str(user_id),
        'filename': f'upload.{extension}' if extension else '',
        'extension': extension,
        'size_bytes': size_bytes,
        'outcome': outcome,
        'reason': reason,
    }
    audit_path = Path(current_app.config['UPLOAD_AUDIT_LOG'])
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    with audit_path.open('a', encoding='utf-8') as audit_file:
        audit_file.write(json.dumps(event, ensure_ascii=False) + '\n')
