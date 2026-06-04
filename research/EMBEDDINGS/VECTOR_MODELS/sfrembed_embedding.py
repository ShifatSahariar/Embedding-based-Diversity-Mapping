
import os
import torch
import torch.nn.functional as F
from transformers import AutoTokenizer, AutoModel


def export_sfrembed_vectors(input_directory, output_vector_directory,
                            model_name="Salesforce/SFR-Embedding-Code-400M_R"):

    os.makedirs(output_vector_directory, exist_ok=True)

    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    model = AutoModel.from_pretrained(model_name, trust_remote_code=True)
    model.eval()

    java_files = [f for f in os.listdir(input_directory) if f.endswith('.txt')]

    for java_file in java_files:
        java_file_path = os.path.join(input_directory, java_file)

        with open(java_file_path, 'r', encoding='utf-8') as file:
            code_snippet = file.read()

        # we can adjust max_length as needed (e.g., 512 tokens)
        inputs = tokenizer(code_snippet, return_tensors="pt", truncation=True, max_length=512)

        with torch.no_grad():
            outputs = model(**inputs)

        token_embeddings = outputs.last_hidden_state  # shape: (1, sequence_length, hidden_size)
        code_embedding = token_embeddings.mean(dim=1)  # shape: (1, hidden_size)

        normalized_embedding = F.normalize(code_embedding, p=2, dim=1)
        embedding_vector = normalized_embedding.squeeze(0).cpu().numpy()

        vector_file_name = java_file.replace('.txt', '_vector.txt')
        output_path = os.path.join(output_vector_directory, vector_file_name)
        with open(output_path, 'w') as f:
            f.write(" ".join(map(str, embedding_vector.tolist())))

        print(f"Processed {java_file} and saved embedding to {vector_file_name}")


        print(f"Embedding saved: {output_path}")