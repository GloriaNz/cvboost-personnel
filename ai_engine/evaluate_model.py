import argparse
from pathlib import Path

from ai_engine.dataset_validation import load_jsonl_examples


def main():
    parser = argparse.ArgumentParser(description='Évalue l’adaptateur LoRA avec SacreBLEU.')
    parser.add_argument('--model', default='Qwen/Qwen2.5-0.5B-Instruct')
    parser.add_argument('--adapter', required=True)
    parser.add_argument('--test', default='ai_engine/data/splits/test.jsonl')
    parser.add_argument('--max-new-tokens', type=int, default=128)
    args = parser.parse_args()

    if args.max_new_tokens < 1:
        parser.error('--max-new-tokens doit être supérieur à zéro.')
    test_path = Path(args.test)
    adapter_path = Path(args.adapter)
    try:
        examples = load_jsonl_examples(test_path, 'test')
    except ValueError as error:
        parser.error(str(error))
    if not adapter_path.is_dir():
        parser.error(f'Adaptateur LoRA introuvable : {adapter_path}')

    try:
        import torch
        from peft import PeftModel
        from sacrebleu import corpus_bleu
        from transformers import AutoModelForCausalLM, AutoTokenizer
    except ImportError as error:
        raise SystemExit(
            'Dépendances d’évaluation manquantes. Installez requirements-training.txt.'
        ) from error

    tokenizer = AutoTokenizer.from_pretrained(adapter_path)
    base_model = AutoModelForCausalLM.from_pretrained(args.model)
    model = PeftModel.from_pretrained(base_model, adapter_path)
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model.to(device)
    model.eval()

    predictions = []
    references = []
    for example in examples:
        inputs = tokenizer(example['prompt'], return_tensors='pt').to(device)
        with torch.no_grad():
            generated = model.generate(
                **inputs,
                max_new_tokens=args.max_new_tokens,
                do_sample=False,
                pad_token_id=tokenizer.eos_token_id,
            )
        prompt_length = inputs['input_ids'].shape[1]
        prediction = tokenizer.decode(
            generated[0][prompt_length:],
            skip_special_tokens=True,
        ).strip()
        predictions.append(prediction)
        references.append(example['completion'])

    score = corpus_bleu(predictions, [references])
    print(score)
    print(f'SacreBLEU: {score.score:.2f}')


if __name__ == '__main__':
    main()
