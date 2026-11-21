"""Consolidate individual .npy embeddings into data/embeddings.pkl"""
import pickle
from pathlib import Path
import numpy as np

EMBEDDINGS_DIR = Path("embeddings")
DATA_DIR = Path("data")
OUTPUT = DATA_DIR / "embeddings.pkl"


def main():
    npy_files = sorted(EMBEDDINGS_DIR.glob("*.npy"))
    if not npy_files:
        print("No .npy files found in embeddings/. Run `python link.py` first.")
        return

    embeddings = {}
    for f in npy_files:
        note_id = f.stem
        embeddings[note_id] = np.load(f)

    DATA_DIR.mkdir(exist_ok=True)
    with open(OUTPUT, "wb") as fh:
        pickle.dump(embeddings, fh)

    print(f"Packed {len(embeddings)} embeddings into {OUTPUT}")
    print(f"Dimensions: {next(iter(embeddings.values())).shape[0]}")


if __name__ == "__main__":
    main()