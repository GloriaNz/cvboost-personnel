import argparse
import json
from pathlib import Path

from ai_engine.dataset_validation import validate_jsonl_examples


def main():
    parser = argparse.ArgumentParser(description='Fine-tune un modèle causal avec LoRA/PEFT.')
    parser.add_argument('--model', default='Qwen/Qwen2.5-0.5B-Instruct')
    parser.add_argument('--train', default='ai_engine/data/splits/train.jsonl')
    parser.add_argument('--validation', default='ai_engine/data/splits/validation.jsonl')
    parser.add_argument('--output-dir', default='ai_engine/models/cvboost-lora')
    parser.add_argument('--max-length', type=int, default=768)
    parser.add_argument('--epochs', type=float, default=2)
    parser.add_argument('--batch-size', type=int, default=1)
    parser.add_argument('--gradient-accumulation', type=int, default=8)
    parser.add_argument('--learning-rate', type=float, default=2e-4)
    parser.add_argument('--target-modules', default='q_proj,v_proj')
    args = parser.parse_args()

    target_modules = [item.strip() for item in args.target_modules.split(',') if item.strip()]
    if not target_modules:
        parser.error('--target-modules doit contenir au moins un nom de module.')
    if args.max_length < 4:
        parser.error('--max-length doit être supérieur ou égal à 4.')
    if args.epochs <= 0 or args.learning_rate <= 0:
        parser.error('--epochs et --learning-rate doivent être supérieurs à zéro.')
    if args.batch_size < 1 or args.gradient_accumulation < 1:
        parser.error('--batch-size et --gradient-accumulation doivent être positifs.')
    try:
        validate_jsonl_examples(args.train, 'train')
        validate_jsonl_examples(args.validation, 'validation')
    except ValueError as error:
        parser.error(str(error))

    try:
        import torch
        from datasets import load_dataset
        from peft import LoraConfig, TaskType, get_peft_model
        from transformers import (
            AutoModelForCausalLM,
            AutoTokenizer,
            DataCollatorForSeq2Seq,
            Trainer,
            TrainingArguments,
        )
    except ImportError as error:
        raise SystemExit(
            'Dépendances de fine-tuning manquantes. Installez requirements-training.txt.'
        ) from error

    dataset = load_dataset(
        'json',
        data_files={'train': args.train, 'validation': args.validation},
    )
    tokenizer = AutoTokenizer.from_pretrained(args.model)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    def tokenize_example(example):
        prompt_tokens = tokenizer(
            example['prompt'],
            add_special_tokens=True,
            truncation=True,
            max_length=args.max_length // 2,
        )['input_ids']
        completion_tokens = tokenizer(
            example['completion'],
            add_special_tokens=False,
            truncation=True,
            max_length=max(1, args.max_length - len(prompt_tokens) - 1),
        )['input_ids']
        input_ids = prompt_tokens + completion_tokens + [tokenizer.eos_token_id]
        labels = [-100] * len(prompt_tokens) + completion_tokens + [tokenizer.eos_token_id]
        return {
            'input_ids': input_ids[:args.max_length],
            'attention_mask': [1] * min(len(input_ids), args.max_length),
            'labels': labels[:args.max_length],
        }

    tokenized = dataset.map(
        tokenize_example,
        remove_columns=dataset['train'].column_names,
        desc='Tokenisation du dataset',
    )
    model = AutoModelForCausalLM.from_pretrained(args.model)
    lora_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=8,
        lora_alpha=16,
        lora_dropout=0.05,
        target_modules=target_modules,
        bias='none',
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    output_directory = Path(args.output_dir)
    output_directory.mkdir(parents=True, exist_ok=True)
    training_args = TrainingArguments(
        output_dir=str(output_directory),
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size,
        gradient_accumulation_steps=args.gradient_accumulation,
        learning_rate=args.learning_rate,
        eval_strategy='epoch',
        save_strategy='epoch',
        logging_strategy='steps',
        logging_steps=10,
        load_best_model_at_end=True,
        metric_for_best_model='eval_loss',
        greater_is_better=False,
        fp16=torch.cuda.is_available(),
        report_to='none',
        seed=42,
    )
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized['train'],
        eval_dataset=tokenized['validation'],
        data_collator=DataCollatorForSeq2Seq(
            tokenizer=tokenizer,
            model=model,
            label_pad_token_id=-100,
        ),
    )
    train_result = trainer.train()
    trainer.save_model(str(output_directory))
    tokenizer.save_pretrained(str(output_directory))
    (output_directory / 'training_metrics.json').write_text(
        json.dumps(train_result.metrics, indent=2),
        encoding='utf-8',
    )
    print(json.dumps(train_result.metrics, indent=2))


if __name__ == '__main__':
    main()
