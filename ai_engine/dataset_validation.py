import json
from pathlib import Path


def iter_jsonl_examples(path, split_name):
    source = Path(path)
    if not source.is_file():
        raise ValueError(f'Fichier {split_name} introuvable : {source}')

    example_count = 0
    try:
        with source.open('r', encoding='utf-8-sig') as dataset_file:
            for line_number, line in enumerate(dataset_file, start=1):
                if not line.strip():
                    continue
                try:
                    example = json.loads(line)
                except json.JSONDecodeError as error:
                    raise ValueError(
                        f'{split_name}, ligne {line_number} : JSON invalide.'
                    ) from error
                if not isinstance(example, dict):
                    raise ValueError(
                        f'{split_name}, ligne {line_number} : un objet JSON est requis.'
                    )
                if any(
                    not isinstance(example.get(field), str) or not example[field].strip()
                    for field in ('prompt', 'completion')
                ):
                    raise ValueError(
                        f'{split_name}, ligne {line_number} : prompt et completion non vides requis.'
                    )
                example_count += 1
                yield example
    except OSError as error:
        raise ValueError(f'Impossible de lire le fichier {split_name} : {source}') from error

    if not example_count:
        raise ValueError(f'Le fichier {split_name} est vide.')


def validate_jsonl_examples(path, split_name):
    return sum(1 for _ in iter_jsonl_examples(path, split_name))


def load_jsonl_examples(path, split_name):
    return list(iter_jsonl_examples(path, split_name))
