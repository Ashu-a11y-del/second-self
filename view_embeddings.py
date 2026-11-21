"""View embeddings stored in data/embeddings.pkl"""
import pickle
import sys
from pathlib import Path

import numpy as np

PKL_PATH = Path("data") / "embeddings.pkl"


def load_embeddings(path: Path):
    with open(path, "rb") as fh:
        return pickle.load(fh)


def as_vector(value) -> np.ndarray:
    """Extract a numpy vector from various value shapes."""
    if isinstance(value, np.ndarray):
        return value
    if isinstance(value, dict):
        for key in ("embedding", "vector", "emb", "values"):
            if key in value:
                return np.asarray(value[key])
        # fall back to first array-like value
        for v in value.values():
            if isinstance(v, (list, np.ndarray)):
                return np.asarray(v)
    if isinstance(value, (list, tuple)):
        return np.asarray(value)
    raise ValueError(f"Cannot interpret value of type {type(value)}")


def main():
    if not PKL_PATH.exists():
        print(f"ERROR: {PKL_PATH} not found.")
        print("Run `python pack_embeddings.py` to create it from embeddings/*.npy")
        sys.exit(1)

    data = load_embeddings(PKL_PATH)

    print(f"File: {PKL_PATH}")
    print(f"Type: {type(data).__name__}")

    # Normalize into a list of (id, vector, raw_value)
    items = []
    if isinstance(data, dict):
        for key, value in data.items():
            try:
                items.append((key, as_vector(value), value))
            except ValueError:
                print(f"  (skipping entry '{key}': unsupported value type)")
    elif isinstance(data, (list, tuple)):
        for i, value in enumerate(data):
            try:
                items.append((f"[{i}]", as_vector(value), value))
            except ValueError:
                print(f"  (skipping entry {i}: unsupported value type)")
    else:
        # single bare vector
        items.append(("root", as_vector(data), data))

    if not items:
        print("No embeddings could be interpreted.")
        return

    dims = items[0][1].shape[0]
    print(f"Embeddings: {len(items)}")
    print(f"Dimensions: {dims}")
    print("=" * 70)

    for idx, (note_id, vec, raw) in enumerate(items):
        norm = float(np.linalg.norm(vec))
        preview = np.array2string(vec[:8], precision=4, separator=", ")
        print(f"\n[{idx + 1}] id: {note_id}")
        print(f"    shape   : {vec.shape}")
        print(f"    norm    : {norm:.4f}")
        print(f"    preview : [{preview}, ...]")

        # Show extra metadata if the raw value was a dict
        if isinstance(raw, dict):
            extras = {k: v for k, v in raw.items()
                      if not isinstance(v, (list, np.ndarray))}
            if extras:
                print(f"    metadata: {extras}")


if __name__ == "__main__":
    main()