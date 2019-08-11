python -u -m relogic.main \
--task_name rel_extraction \
--mode train \
--output_dir saves/relation_extraction/tacred/tacred_base_5 \
--bert_model bert-base-cased \
--raw_data_path data/raw_data/rel_extraction/tacred/origin \
--label_mapping_path data/preprocessed_data/rel_extraction_tacred_label_mapping.pkl \
--model_name default \
--local_rank $1 \
--train_batch_size 16 \
--test_batch_size 16 \
--learning_rate 3e-5 \
--epoch_number 3 \
--eval_dev_every 1000 \
--no_entity_surface \
--no_bilstm \
--rel_extraction_module_type sent_repr \
# --gradient_accumulation_steps 2 \