import transformers
from transformers import AutoConfig, AutoModel, AutoTokenizer
import torch, pathlib, numpy as np, torch.nn.functional as F
import threading

# ============================================================
# Thread-safe global cache for model/tokenizer
# ============================================================
_MODEL_CACHE = {}
_MODEL_LOCK = threading.Lock()


def get_qwen3_model(model_name="Qwen/Qwen3-Embedding-0.6B"):
    """Load Qwen3 model once per process, thread-safe."""
    global _MODEL_CACHE
    if model_name in _MODEL_CACHE:
        return _MODEL_CACHE[model_name]

    # 🔒 ensure only one thread loads at a time
    with _MODEL_LOCK:
        if model_name in _MODEL_CACHE:
            return _MODEL_CACHE[model_name]

        print(f"[QWEN3] Loading model '{model_name}' once...")

        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        # Load tokenizer/config/model (no meta-device conflicts)
        tokenizer = AutoTokenizer.from_pretrained(
            model_name, use_fast=False, trust_remote_code=True
        )
        config = AutoConfig.from_pretrained(model_name, trust_remote_code=True)
        model = AutoModel.from_pretrained(
            model_name, config=config, trust_remote_code=True
        )

        # ⚙️ Important: move after weights are materialized
        model = model.to(device, dtype=torch.float32).eval()

        _MODEL_CACHE[model_name] = (tokenizer, model, device)
        print(f"[QWEN3] Model loaded successfully on {device}.")
        return tokenizer, model, device


# ============================================================
# 🧩 Main embedding export (same logic)
# ============================================================
def export_qwen3_vectors(
    input_directory,
    output_vector_directory,
    max_len=1024,
    model_name="Qwen/Qwen3-Embedding-0.6B",
    batch_size=50
):
    input_directory = pathlib.Path(input_directory)
    output_directory = pathlib.Path(output_vector_directory)
    output_directory.mkdir(parents=True, exist_ok=True)

    tokenizer, model, device = get_qwen3_model(model_name)

    def last_token_pool(hidden, mask):
        idx = mask.sum(1) - 1
        return hidden[torch.arange(hidden.size(0)), idx]

    files = [p for p in input_directory.iterdir() if p.suffix in {".txt", ".java"}]
    if not files:
        print(f"[QWEN3] ️ No input files found in {input_directory}")
        return

    for i in range(0, len(files), batch_size):
        batch_paths = files[i:i + batch_size]
        texts = []
        for p in batch_paths:
            try:
                txt = p.read_text(encoding="utf-8").strip()
                texts.append(txt if txt else " ")
            except Exception as e:
                print(f"[QWEN3] ⚠️ Read error ({p.name}): {e}")
                texts.append(" ")

        batch = tokenizer(
            texts,
            padding=True,
            truncation=True,
            max_length=max_len,
            return_tensors="pt"
        ).to(device)

        with torch.no_grad():
            out = model(**batch)
            hidden = getattr(out, "last_hidden_state", None)

            if hidden is None and hasattr(out, "pooler_output"):
                vecs = F.normalize(out.pooler_output, p=2, dim=1)
            else:
                vecs = last_token_pool(hidden, batch["attention_mask"])
                vecs = F.normalize(vecs, p=2, dim=1)

        for vec, path in zip(vecs, batch_paths):
            out_path = output_directory / f"{path.stem}_vector.txt"
            np.savetxt(
                out_path,
                vec.detach().cpu().numpy().reshape(1, -1),
                delimiter=" "
            )
            print(f"✓ Saved Qwen3 embedding → {out_path}")

        if (i + batch_size) % 500 == 0:
            print(f"[QWEN3] Progress: {i + batch_size}/{len(files)}")

    print(f"[QWEN3] ✅ All embeddings saved to {output_directory}")
