import os
import torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM


def export_codet5_small_vectors(input_directory, output_vector_directory):
    if not os.path.exists(output_vector_directory):
        os.makedirs(output_vector_directory)

    # Use Auto classes for better compatibility
    tokenizer = AutoTokenizer.from_pretrained('Salesforce/codet5-small')
    model = AutoModelForSeq2SeqLM.from_pretrained('Salesforce/codet5-small')
    model.eval()

    java_files = [f for f in os.listdir(input_directory) if f.endswith('.txt')]

    for java_file in java_files:
        java_file_path = os.path.join(input_directory, java_file)

        with open(java_file_path, 'r') as file:
            code_snippet = file.read()

        # Tokenize with both encoder and decoder inputs
        inputs = tokenizer(code_snippet, return_tensors="pt")
        inputs['decoder_input_ids'] = inputs['input_ids'].clone()  # Critical for T5 models

        with torch.no_grad():
            outputs = model(**inputs, output_hidden_states=True)
            # Get encoder's last hidden state (not decoder's)
            embeddings = outputs.encoder_last_hidden_state[:, 0, :].numpy()

        vector_file_name = java_file.replace('.txt', '_vector.txt')
        output_vector_path = os.path.join(output_vector_directory, vector_file_name)

        with open(output_vector_path, 'w') as vector_file:
            for value in embeddings[0]:
                vector_file.write(f"{value} ")

        print(f"Vector saved: {output_vector_path}")