import json
import tempfile
import unittest
from pathlib import Path

from ai_engine.prepare_dataset import (
    assert_no_leakage,
    load_pairs,
    prepare_dataset,
    split_pairs,
)
from ai_engine.dataset_validation import load_jsonl_examples


class PrepareDatasetTests(unittest.TestCase):
    def setUp(self):
        self.temp_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_directory.name)

    def tearDown(self):
        self.temp_directory.cleanup()

    def write_examples(self, examples):
        path = self.root / 'examples.jsonl'
        path.write_text(
            ''.join(json.dumps(example, ensure_ascii=False) + '\n' for example in examples),
            encoding='utf-8',
        )
        return path

    def test_prepare_deduplicates_and_creates_leak_free_splits(self):
        examples = [
            {'prompt': f'Profil candidat {index}', 'completion': f'Résumé professionnel {index}'}
            for index in range(10)
        ]
        examples.append(examples[0])
        input_path = self.write_examples(examples)
        output_directory = self.root / 'splits'

        manifest = prepare_dataset(input_path, output_directory, seed=17)

        self.assertEqual(manifest['input_examples_after_deduplication'], 10)
        self.assertEqual(manifest['exact_duplicates_removed'], 1)
        self.assertEqual(manifest['leakage_check'], 'passed')
        self.assertEqual(sum(manifest['split_counts'].values()), 10)
        self.assertTrue((output_directory / 'manifest.json').is_file())

        records = {
            name: [
                json.loads(line)
                for line in (output_directory / f'{name}.jsonl').read_text(encoding='utf-8').splitlines()
            ]
            for name in ('train', 'validation', 'test')
        }
        prepared_pairs, _ = load_pairs(input_path)
        splits = split_pairs(prepared_pairs, seed=17)
        assert_no_leakage(splits)
        self.assertEqual(
            {
                (record['prompt'], record['completion'])
                for split_records in records.values()
                for record in split_records
            },
            {
                (record['prompt'], record['completion'])
                for record in examples
            },
        )
        self.assertGreater(len(records['train']), len(records['validation']))

    def test_repeated_prompt_or_completion_stays_in_one_split(self):
        records = [
            {
                'prompt': f'Profil {index}' if index != 1 else 'Profil 0',
                'completion': f'Résumé {index}',
            }
            for index in range(6)
        ]
        pairs, _ = load_pairs(self.write_examples(records))
        splits = split_pairs(pairs)
        prompt_owners = {}
        for name, items in splits.items():
            for item in items:
                prompt_owners.setdefault(item['prompt_hash'], set()).add(name)
        self.assertTrue(all(len(owners) == 1 for owners in prompt_owners.values()))

    def test_rejects_too_few_independent_groups(self):
        examples = [
            {'prompt': 'Même profil', 'completion': 'Réponse un'},
            {'prompt': 'Même profil', 'completion': 'Réponse deux'},
            {'prompt': 'Profil distinct', 'completion': 'Réponse trois'},
        ]
        pairs, _ = load_pairs(self.write_examples(examples))
        with self.assertRaisesRegex(ValueError, '3 groupes indépendants'):
            split_pairs(pairs)

    def test_invalid_json_has_line_number(self):
        path = self.root / 'invalid.jsonl'
        path.write_text('{"prompt":\n', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'Ligne 1'):
            load_pairs(path)

    def test_lora_dataset_validation_accepts_prompt_completion_jsonl(self):
        path = self.write_examples([
            {'prompt': 'Question professionnelle', 'completion': 'Réponse sourcée.'}
        ])

        examples = load_jsonl_examples(path, 'train')

        self.assertEqual(examples[0]['prompt'], 'Question professionnelle')

    def test_lora_dataset_validation_reports_invalid_rows(self):
        path = self.root / 'invalid-split.jsonl'
        path.write_text('{"prompt":"Question","completion":""}\n', encoding='utf-8')

        with self.assertRaisesRegex(ValueError, 'ligne 1.*non vides'):
            load_jsonl_examples(path, 'validation')

    def test_lora_dataset_validation_rejects_empty_split(self):
        path = self.root / 'empty-split.jsonl'
        path.write_text('\n', encoding='utf-8')

        with self.assertRaisesRegex(ValueError, 'fichier test est vide'):
            load_jsonl_examples(path, 'test')


if __name__ == '__main__':
    unittest.main()
