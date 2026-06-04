import os
import torch
from infercode.client.infercode_client import InferCodeClient

# Initialize InferCode client
infercode = InferCodeClient(language="java")  # Set the language to Java (or your target language)

def get_code_embedding(code_snippet):
    try:
        # Generate embedding using InferCode
        embedding = infercode.encode([code_snippet])
        return embedding[0]  # Return the first (and only) embedding
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

def export_infercode_embeddings(input_directory, output_vector_directory):
    if not os.path.exists(output_vector_directory):
        os.makedirs(output_vector_directory)

    input_files = [f for f in os.listdir(input_directory) if f.endswith('.java')]

    for input_file in input_files:
        input_file_path = os.path.join(input_directory, input_file)
        with open(input_file_path, 'r') as file:
            code_snippet = file.read()

        embedding = get_code_embedding(code_snippet)
        if embedding is None:
            print(f"Failed to retrieve embedding for file: {input_file}")
            continue

        vector_file_name = input_file.replace('.java', '_vector.txt')
        output_vector_path = os.path.join(output_vector_directory, vector_file_name)

        with open(output_vector_path, 'w') as vector_file:
            for value in embedding:
                vector_file.write(f"{value} ")

        print(f"Output VECTORS_COLLECTION saved to: {output_vector_path}")

# Example usage
input_directory = "path/to/your/java/files"
output_vector_directory = "path/to/save/embeddings"
export_infercode_embeddings(input_directory, output_vector_directory)