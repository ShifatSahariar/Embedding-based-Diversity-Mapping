import random
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import numpy as np
from openai import OpenAI

import os

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# ================================
# 🔹 Function: Get batched embeddings
# ================================
def get_code_embeddings_batch(snippets, max_retries=5, delay=2):
    """Fetch embeddings for a list of code snippets with retry and error handling."""
    for attempt in range(max_retries):
        try:
            response = client.embeddings.create(
                input=snippets,
                model="text-embedding-3-small"
            )
            return [d.embedding for d in response.data]
        except Exception as e:
            print(f"[Retry {attempt+1}/{max_retries}] Error: {e}")
            time.sleep(delay ** (attempt + 1) + random.random())
    print("❌ Failed to fetch batch after retries.")
    return [None] * len(snippets)


# ================================
# 🔹 Function: Process one batch of files
# ================================
def process_batch(batch_files, input_dir, output_dir):
    snippets, paths = [], []

    # Read files
    for fname in batch_files:
        in_path = os.path.join(input_dir, fname)
        out_path = os.path.join(output_dir, fname.replace(".txt", "_vector.txt"))

        # Skip already processed
        if os.path.exists(out_path):
            print(f"⏩ Skipped (cached): {fname}")
            continue

        try:
            with open(in_path, "r", encoding="utf-8") as f:
                code = f.read().strip()
                if code:
                    snippets.append(code)
                    paths.append(out_path)
                else:
                    print(f"⚠️ Empty file skipped: {fname}")
        except Exception as e:
            print(f"❌ Read error ({fname}): {e}")

    if not snippets:
        return

    # Get embeddings in one API call
    embeddings = get_code_embeddings_batch(snippets)

    # Save results
    for out_path, emb in zip(paths, embeddings):
        if emb is None:
            print(f"❌ Failed: {os.path.basename(out_path)}")
            continue
        np.savetxt(
            out_path,
            np.array(emb, dtype=np.float32).reshape(1, -1),
            delimiter=" "
        )
        print(f"✅ Saved embedding → {out_path}")


# ================================
# 🔹 Main export function
# ================================
def export_openai_embeddings(input_dir, output_dir, batch_size=10, max_workers=5):
    os.makedirs(output_dir, exist_ok=True)
    files = sorted([f for f in os.listdir(input_dir) if f.endswith(".txt")])
    if not files:
        print("No .txt files found.")
        return

    # Create batches
    batches = [files[i:i+batch_size] for i in range(0, len(files), batch_size)]
    print(f"[INFO] Total files: {len(files)} | Batches: {len(batches)} | Parallel workers: {max_workers}")

    # Run batches in parallel
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(process_batch, batch, input_dir, output_dir)
            for batch in batches
        ]
        for fut in as_completed(futures):
            fut.result()

    print("\n🎯 All embeddings exported successfully!")
