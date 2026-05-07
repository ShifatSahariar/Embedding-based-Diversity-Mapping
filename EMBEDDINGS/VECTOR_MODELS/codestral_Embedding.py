import random
import time
import os

from mistralai import Mistral
import numpy as np, pathlib
from concurrent.futures import ThreadPoolExecutor, as_completed
api_key = os.getenv("MISTRAL_API_KEY")

if not api_key:
    raise RuntimeError("MISTRAL_API_KEY missing!")

client = Mistral(api_key=api_key)
MODEL = "codestral-embed-2505"
OUT_DIM = 1536


# =========================================
# 🔹 Function: Get batched embeddings with retries
# =========================================
def get_codestral_embeddings_batch(texts, model=MODEL, output_dim=OUT_DIM, max_retries=5, base_delay=2):
    """Request embeddings for a batch of texts with retry and backoff."""
    for attempt in range(max_retries):
        try:
            resp = client.embeddings.create(
                model=model,
                inputs=texts,
                output_dimension=output_dim
            )
            return [d.embedding for d in resp.data]
        except Exception as e:
            print(f"[Retry {attempt+1}/{max_retries}] Error: {e}")
            time.sleep(base_delay ** (attempt + 1) + random.random())
    print("Failed batch after multiple retries.")
    return [None] * len(texts)


# =========================================
# 🔹 Function: Process one batch of files
# =========================================
def process_batch(batch_files, input_dir, output_dir, model=MODEL, output_dim=OUT_DIM):
    texts, out_paths = [], []

    for p in batch_files:
        out_path = output_dir / f"{p.stem}_vector.txt"
        if out_path.exists():
            print(f"⏩ Skipped (cached): {p.name}")
            continue

        try:
            text = p.read_text(encoding="utf-8").strip()
            if not text:
                print(f" Empty file skipped: {p.name}")
                continue
            texts.append(text)
            out_paths.append(out_path)
        except Exception as e:
            print(f"Read error ({p.name}): {e}")

    if not texts:
        return

    # Get batched embeddings
    embeddings = get_codestral_embeddings_batch(texts, model=model, output_dim=output_dim)

    # Save embeddings
    for out_path, emb in zip(out_paths, embeddings):
        if emb is None:
            print(f" Failed: {out_path.name}")
            continue
        np.savetxt(out_path, np.array(emb, dtype=np.float32).reshape(1, -1), delimiter=" ")
        print(f"Saved embedding → {out_path}")


# =========================================
# 🔹 Main export function
# =========================================
def export_codestral_vectors(input_dir, output_dir, batch_size=64, max_workers=5, model=MODEL, output_dim=OUT_DIM):
    input_dir = pathlib.Path(input_dir)
    output_dir = pathlib.Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    files = sorted(input_dir.glob("*.txt"))
    if not files:
        print(f"No *.txt files in {input_dir}")
        return

    batches = [files[i:i+batch_size] for i in range(0, len(files), batch_size)]
    print(f"[INFO] Files: {len(files)} | Batches: {len(batches)} | Parallel workers: {max_workers}")

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(process_batch, batch, input_dir, output_dir, model, output_dim)
            for batch in batches
        ]
        for fut in as_completed(futures):
            fut.result()

    print("\nAll Codestral embeddings exported successfully!")
