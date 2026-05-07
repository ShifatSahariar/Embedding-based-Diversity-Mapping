import os
import torch
import warnings

from transformers import RobertaModel, RobertaTokenizer
from Helper_Functions.HelperFunctions import clear_directory

# Suppress specific warnings
warnings.filterwarnings("ignore", category=FutureWarning, message=".*resume_download.*")


def export_codebert_vectors(input_directory, output_vector_directory):
    if not os.path.exists(output_vector_directory):
        os.makedirs(output_vector_directory)

    tokenizer = RobertaTokenizer.from_pretrained("microsoft/codebert-base")
    model = RobertaModel.from_pretrained("microsoft/codebert-base")

    java_files = [f for f in os.listdir(input_directory) if f.endswith('.txt')]

    for java_file in java_files:
        java_file_path = os.path.join(input_directory, java_file)

        with open(java_file_path, 'r') as file:
            code_snippet = file.read()

        inputs = tokenizer(
            code_snippet,
            truncation=True,
            max_length=512,  # explicit upper bound
            return_tensors="pt"
        )

        with torch.no_grad():
            outputs = model(**inputs)

        embeddings = outputs.last_hidden_state[:, 0, :].numpy()


        vector_file_name = java_file.replace('.txt', '_vector.txt')
        output_vector_path = os.path.join(output_vector_directory, vector_file_name)

        with open(output_vector_path, 'w') as vector_file:
            for value in embeddings[0]:
                vector_file.write(f"{value} ")

        print(f"Output VECTORS_COLLECTION saved to: {output_vector_path}")

