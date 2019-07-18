from __future__ import absolute_import, division, print_function

import argparse
import json
import os
import random
from types import SimpleNamespace

import numpy as np

import torch
from relogic.logickit.base import utils
from relogic.logickit.base.configure import configure
from relogic.logickit.training import trainer, training_progress
from relogic.logickit.serving import Server


def train(config):
  model_trainer = trainer.Trainer(config)
  progress = training_progress.TrainingProgress(
    config=config, tokenizer=model_trainer.tokenizer)
  model_trainer.train(progress)

def finetune(config):
  general_config_path = os.path.join(config.restore_path,
                                     "general_config.json")
  with open(general_config_path) as f:
    restore_config = SimpleNamespace(**json.load(f))
  if config.model_name:
    model_path = os.path.join(config.restore_path,
                            config.model_name + ".ckpt")
  else:
    model_path = os.path.join(config.restore_path,
                              restore_config.model_name + ".ckpt")
  model_trainer = trainer.Trainer(config)
  model_trainer.restore(model_path)
  progress = training_progress.TrainingProgress(
    config=config, tokenizer=model_trainer.tokenizer)
  model_trainer.train(progress)


def eval(config):
  general_config_path = os.path.join(config.restore_path,
                                     "general_config.json")
  with open(general_config_path) as f:
    restore_config = SimpleNamespace(**json.load(f))
  if config.model_name:
    model_path = os.path.join(config.restore_path,
                            config.model_name + ".ckpt")
  else:
    model_path = os.path.join(config.restore_path,
                              restore_config.model_name + ".ckpt")
  restore_config.mode = config.mode
  restore_config.local_rank = config.local_rank
  restore_config.no_cuda = config.no_cuda
  restore_config.buckets = config.buckets
  restore_config.gold_answer_file = config.gold_answer_file
  restore_config.null_score_diff_threshold = config.null_score_diff_threshold
  restore_config.output_attentions = config.output_attentions
  if not hasattr(restore_config, "branching_encoder"):
    restore_config.branching_encoder = False
  print(restore_config)
  utils.heading("RUN {} ({:})".format(config.mode.upper(),
                                      restore_config.task_names))
  model_trainer = trainer.Trainer(restore_config)
  model_trainer.restore(model_path)
  if config.mode == "serving":
    server = Server(model_trainer)
    server.start()
  else:
    model_trainer.evaluate_all_tasks()


def main():
  utils.heading("SETUP")
  parser = argparse.ArgumentParser()

  # IO
  parser.add_argument("--data_dir", type=str, default="data")
  parser.add_argument(
    "--mode", default=None, choices=["train", "valid", "eval", "finetune"])
  parser.add_argument("--output_dir", type=str, default="data/models")
  parser.add_argument("--max_seq_length", type=int, default=450)
  parser.add_argument("--max_query_length", type=int, default=64)
  parser.add_argument("--doc_stride", type=int, default=128)
  parser.add_argument("--do_lower_case", default=False, action="store_true")
  parser.add_argument("--model_name", type=str)
  parser.add_argument("--restore_path", type=str)
  parser.add_argument("--train_file", type=str, default="train.txt")
  parser.add_argument("--dev_file", type=str, default="dev.txt")
  parser.add_argument("--test_file", type=str, default="test.txt")

  # Task Definition
  parser.add_argument("--task_names", type=str)
  parser.add_argument("--raw_data_path", type=str)
  parser.add_argument("--label_mapping_path", type=str)
  parser.add_argument("--unsupervised_data", type=str)
  parser.add_argument("--lang", type=str, default="en")
  parser.add_argument("--topk", default=1)
  parser.add_argument("--gold_answer_file", default="data/preprocessed_data/squad20.json")
  parser.add_argument("--dump_to_files_dict", default="")

  parser.add_argument("--output_attentions", default=False, action="store_true")

  # Task related configuration

  # Relation Extraction
  parser.add_argument("--no_entity_surface", dest="entity_surface_aware", default=True, action="store_false")
  parser.add_argument("--use_dependency_feature", dest="use_dependency_feature", default=False, action="store_true")

  # Semantic Role Labeling
  parser.add_argument("--no_predicate_surface", dest="predicate_surface_aware", default=True, action="store_false")
  parser.add_argument("--no_span_annotation", dest="use_span_annotation", default=True, action="store_false")

  # Reading Comprehension
  parser.add_argument("--null_score_diff_threshold", default=1.0)

  # Modeling
  parser.add_argument("--use_gcn", dest="use_gcn", default=False, action="store_true")

  # Model
  parser.add_argument("--bert_model", type=str)
  parser.add_argument("--hidden_size", type=int, default=768)
  parser.add_argument("--projection_size", type=int, default=300)
  parser.add_argument(
    "--initializer_range", type=float,
    default=0.02)  # initialization for task module
  # follow the initialization range of bert
  parser.add_argument("--no_bilstm", default=True, dest="use_bilstm", action="store_false")
  parser.add_argument("--repr_size", default=300, type=int)
  parser.add_argument("--branching_encoder", default=False, action="store_true")
  parser.add_argument("--routing_config_file", type=str)

  # Semi-Supervised
  parser.add_argument("--is_semisup", default=False, action="store_true")
  parser.add_argument("--partial_view_sources", type=str)

  # Training
  parser.add_argument("--seed", type=int, default=3435)
  parser.add_argument("--no_cuda", action="store_true")
  parser.add_argument("--local_rank", type=int, default=-1)
  parser.add_argument("--learning_rate", type=float, default=5e-5)
  parser.add_argument("--warmup_proportion", type=float, default=0.1)
  parser.add_argument(
    "--gradient_accumulation_steps",
    type=int,
    default=1,
    help=
    "Number of updates steps to accumulate before performing a backward/update pass"
  )
  parser.add_argument("--print_every", type=int, default=25)
  parser.add_argument("--eval_dev_every", default=2000, type=int)
  parser.add_argument("--train_batch_size", type=int, default=8)
  parser.add_argument("--test_batch_size", type=int, default=8)
  parser.add_argument("--grad_clip", type=float, default=1.0)
  parser.add_argument("--epoch_number", type=int, default=20)
  parser.add_argument("--self_attention_head_size", default=64, type=int)
  parser.add_argument("--schedule_method", default="warmup_linear")
  parser.add_argument(
    "--no_schedule_lr", dest="schedule_lr", default=True, action="store_false")
  parser.add_argument("--word_dropout", default=False, action="store_true")
  parser.add_argument("--word_dropout_prob", default=0.6, type=float)
  parser.add_argument("--max_margin", type=float, default=3)
  parser.add_argument("--warmup_epoch_number", type=int, default=0)
  parser.add_argument("--sgd_learning_rate", type=float, default=0.1)
  parser.add_argument("--adam_learning_rate", type=float, default=0.0001)
  parser.add_argument("--sep_optim", dest="sep_optim", default=False, action="store_true")
  parser.add_argument("--multi_gpu", dest="multi_gpu", default=False, action="store_true")
  parser.add_argument("--ignore_parameters", default="", type=str)
  # Need to combine to CUDA_VISIBLE_DEVICES

  args = parser.parse_args()

  if not args.mode:
    raise ValueError("You need to specify the mode")
  if args.output_dir:
    if os.path.exists(args.output_dir) and os.listdir(
        args.output_dir) and args.mode == "train":
      raise ValueError(
        "Output directory ({}) already exists and is not empty.".format(
          args.output_dir))
    if not os.path.exists(args.output_dir):
      os.makedirs(args.output_dir)

  if args.gradient_accumulation_steps < 1:
    raise ValueError(
      "Invalid gradient_accumulation_steps parameter: {}, should be >= 1".
      format(args.gradient_accumulation_steps))
  # args.train_batch_size = args.train_batch_size // args.gradient_accumulation_steps
  # num_train_optimization_steps = len(train_examples) / batch_size * epoch_number

  random.seed(args.seed)
  np.random.seed(args.seed)
  torch.manual_seed(args.seed)
  torch.cuda.manual_seed_all(args.seed)

  configure(args)

  print(args)

  if args.mode == "train":
    utils.heading("START TRAINING ({:})".format(args.task_names))
    train(args)
  elif args.mode == "valid":
    eval(args)
  elif args.mode == "eval":
    eval(args)
  elif args.mode == "finetune":
    finetune(args)
  elif args.mode == "serving":
    eval(args)


if __name__ == "__main__":
  main()