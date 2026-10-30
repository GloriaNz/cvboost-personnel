import argparse
import hashlib
import json
import random
import unicodedata
from collections import defaultdict
from pathlib import Path


SPLIT_RATIOS = {'train': 0.8, 'validation': 0.1, 'test': 0.1}


def normalize_text(value):
    return ' '.join(unicodedata.normalize('NFKC', value).split())


def text_hash(value):
    return hashlib.sha256(normalize_text(value).casefold().encode('utf-8')).hexdigest()


def load_pairs(input_path):
    path = Path(input_path)
    pairs_by_hash = {}
    duplicates = 0
    with path.open('r', encoding='utf-8-sig') as data_file:
        for line_number, line in enumerate(data_file, start=1):
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(f'Ligne {line_number} : JSON invalide.') from error
            if not isinstance(item, dict):
                raise ValueError(f'Ligne {line_number} : chaque exemple doit être un objet JSON.')
            prompt = item.get('prompt', item.get('input'))
            completion = item.get('completion', item.get('output'))
            if not isinstance(prompt, str) or not isinstance(completion, str):
                raise ValueError(
                    f'Ligne {line_number} : champs prompt/completion (ou input/output) requis.'
                )
            prompt = normalize_text(prompt)
            completion = normalize_text(completion)
            if not prompt or not completion:
                raise ValueError(f'Ligne {line_number} : prompt et completion ne peuvent pas être vides.')

            pair_hash = hashlib.sha256(
                f'{text_hash(prompt)}:{text_hash(completion)}'.encode('ascii')
            ).hexdigest()
            if pair_hash in pairs_by_hash:
                duplicates += 1
                continue
            pairs_by_hash[pair_hash] = {
                'prompt': prompt,
                'completion': completion,
                'prompt_hash': text_hash(prompt),
                'completion_hash': text_hash(completion),
                'pair_hash': pair_hash,
            }

    return list(pairs_by_hash.values()), duplicates


class _DisjointSet:
    def __init__(self, size):
        self.parent = list(range(size))

    def find(self, value):
        while self.parent[value] != value:
            self.parent[value] = self.parent[self.parent[value]]
            value = self.parent[value]
        return value

    def union(self, left, right):
        left_root = self.find(left)
        right_root = self.find(right)
        if left_root != right_root:
            self.parent[right_root] = left_root


def _leakage_groups(pairs):
    disjoint_set = _DisjointSet(len(pairs))
    owner_by_hash = {}
    for index, pair in enumerate(pairs):
        for fingerprint in (pair['prompt_hash'], pair['completion_hash']):
            previous = owner_by_hash.setdefault(fingerprint, index)
            disjoint_set.union(index, previous)

    groups = defaultdict(list)
    for index, pair in enumerate(pairs):
        groups[disjoint_set.find(index)].append(pair)
    return list(groups.values())


def split_pairs(pairs, seed=42):
    groups = _leakage_groups(pairs)
    if len(groups) < 3:
        raise ValueError(
            'Il faut au moins 3 groupes indépendants de prompts/réponses pour créer '
            'les partitions train, validation et test sans fuite.'
        )

    rng = random.Random(seed)
    rng.shuffle(groups)
    groups.sort(key=len, reverse=True)
    total = len(pairs)
    targets = {name: ratio * total for name, ratio in SPLIT_RATIOS.items()}
    assignments = {name: [] for name in SPLIT_RATIOS}
    counts = {name: 0 for name in SPLIT_RATIOS}

    for group in groups:
        available = [
            name for name in SPLIT_RATIOS
            if not assignments[name]
        ]
        if available:
            split_name = max(available, key=lambda name: targets[name])
        else:
            split_name = max(
                SPLIT_RATIOS,
                key=lambda name: (targets[name] - counts[name]) / targets[name],
            )
        assignments[split_name].extend(group)
        counts[split_name] += len(group)

    split_by_name = {
        name: sorted(records, key=lambda record: record['pair_hash'])
        for name, records in assignments.items()
    }
    assert_no_leakage(split_by_name)
    return split_by_name


def assert_no_leakage(splits):
    seen = {'prompt_hash': {}, 'completion_hash': {}, 'pair_hash': {}}
    for split_name, records in splits.items():
        if not records:
            raise AssertionError(f'La partition {split_name} est vide.')
        for record in records:
            for field, split_owners in seen.items():
                fingerprint = record[field]
                previous_split = split_owners.get(fingerprint)
                if previous_split is not None and previous_split != split_name:
                    raise AssertionError(f'Fuite {field} entre les partitions.')
                split_owners[fingerprint] = split_name


def prepare_dataset(input_path, output_directory, seed=42):
    pairs, duplicates = load_pairs(input_path)
    if len(pairs) < 3:
        raise ValueError('Au moins 3 exemples uniques sont nécessaires.')
    splits = split_pairs(pairs, seed)
    output = Path(output_directory)
    output.mkdir(parents=True, exist_ok=True)

    for split_name, records in splits.items():
        with (output / f'{split_name}.jsonl').open('w', encoding='utf-8') as split_file:
            for record in records:
                split_file.write(json.dumps({
                    'prompt': record['prompt'],
                    'completion': record['completion'],
                }, ensure_ascii=False) + '\n')

    manifest = {
        'input_examples_after_deduplication': len(pairs),
        'exact_duplicates_removed': duplicates,
        'seed': seed,
        'split_counts': {name: len(records) for name, records in splits.items()},
        'split_ratios': SPLIT_RATIOS,
        'leakage_check': 'passed',
    }
    (output / 'manifest.json').write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding='utf-8',
    )
    return manifest


def main():
    parser = argparse.ArgumentParser(description='Déduplique et sépare un dataset sans fuite.')
    parser.add_argument('--input', required=True, help='JSONL avec prompt/completion.')
    parser.add_argument('--output-dir', default='ai_engine/data/splits')
    parser.add_argument('--seed', type=int, default=42)
    args = parser.parse_args()

    manifest = prepare_dataset(args.input, args.output_dir, args.seed)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
