import os, torch, numpy as np
from transformers import RobertaTokenizer, RobertaModel
import threading

# ======================================================
# 🔒 Thread-safe global cache for model/tokenizer
# ======================================================
_MODEL_CACHE = {}
_MODEL_LOCK = threading.Lock()


def get_graphcodebert_model(model_name="microsoft/graphcodebert-base"):
    """Load GraphCodeBERT model once per process (thread-safe)."""
    global _MODEL_CACHE
    if model_name in _MODEL_CACHE:
        return _MODEL_CACHE[model_name]

    with _MODEL_LOCK:
        if model_name in _MODEL_CACHE:
            return _MODEL_CACHE[model_name]

        print(f"[GRAPH_CODEBERT] Loading model '{model_name}' once...")

        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        tokenizer = RobertaTokenizer.from_pretrained(model_name)
        model = RobertaModel.from_pretrained(model_name)
        model = model.to(device).eval()

        _MODEL_CACHE[model_name] = (tokenizer, model, device)
        print(f"[GRAPH_CODEBERT] Model loaded successfully on {device}.")
        return tokenizer, model, device


# ======================================================
# 🧩 Main export function (batched)
# ======================================================
def export_graphcodebert_vectors(
    input_directory,
    output_vector_directory,
    batch_size=16,
    model_name="microsoft/graphcodebert-base"
):
    """
    Export GraphCodeBERT embeddings for all .txt files in the given directory.
    - Batches inputs for faster processing
    - Thread-safe model reuse
    - Same output format (space-separated values)
    """
    os.makedirs(output_vector_directory, exist_ok=True)
    tokenizer, model, device = get_graphcodebert_model(model_name)

    java_files = [f for f in os.listdir(input_directory) if f.endswith(".txt")]
    if not java_files:
        print(f"[GRAPH_CODEBERT] ⚠️ No input files found in {input_directory}")
        return

    for i in range(0, len(java_files), batch_size):
        batch_files = java_files[i:i + batch_size]
        snippets = []
        for fname in batch_files:
            try:
                path = os.path.join(input_directory, fname)
                with open(path, "r", encoding="utf-8") as f:
                    code_snippet = f.read().strip()
                snippets.append(code_snippet if code_snippet else " ")
            except Exception as e:
                print(f"[GRAPH_CODEBERT] ⚠️ Read error ({fname}): {e}")
                snippets.append(" ")

        # Tokenize entire batch
        inputs = tokenizer(
            snippets,
            truncation=True,
            padding=True,
            max_length=512,
            return_tensors="pt"
        ).to(device)

        with torch.no_grad():
            outputs = model(**inputs)
            embeddings = outputs.last_hidden_state[:, 0, :]  # CLS token
            embeddings = embeddings.detach().cpu().numpy()

        # Save each embedding
        for vec, fname in zip(embeddings, batch_files):
            out_path = os.path.join(output_vector_directory, fname.replace(".txt", "_vector.txt"))
            np.savetxt(out_path, vec.reshape(1, -1), delimiter=" ")
            print(f"✓ Saved GraphCodeBERT embedding → {out_path}")

        if (i + batch_size) % 500 == 0:
            print(f"[GRAPH_CODEBERT] Progress: {i + batch_size}/{len(java_files)}")

    print(f"[GRAPH_CODEBERT] ✅ All embeddings saved to {output_vector_directory}")
