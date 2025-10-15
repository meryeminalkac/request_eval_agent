#!/usr/bin/env python3
"""
Join evaulations.json and prf_answers.json on project_name, build one text per
project, embed with sentence-transformers, and save embeddings + ids.

Usage:
  python single_use_scripts/join_and_embed.py [evaulations.json] [prf_answers.json]

Outputs:
  embeddings.npy          # float32 matrix [num_projects, dim]
  embedding_ids.json      # list of project_name in same order
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List
import argparse
import os

import numpy as np
from sentence_transformers import SentenceTransformer
import faiss
try:
    import torch  # sentence-transformers uses PyTorch under the hood
except Exception:
    torch = None  # type: ignore


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def index_by_project_name(obj: Any) -> Dict[str, Dict[str, Any]]:
    # Accept dict (single project), list of dicts, or dict keyed by name
    if isinstance(obj, dict) and "project_name" in obj:
        return {obj["project_name"]: obj}
    if isinstance(obj, list):
        out: Dict[str, Dict[str, Any]] = {}
        for item in obj:
            if isinstance(item, dict) and "project_name" in item:
                out[item["project_name"]] = item
        return out
    if isinstance(obj, dict):
        return {k: v for k, v in obj.items() if isinstance(v, dict)}
    return {}


def merge(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(a)
    for k, v in b.items():
        if k in out and isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = merge(out[k], v)
        else:
            out[k] = v
    return out


def flatten_for_text(d: Dict[str, Any], prefix: str = "") -> List[str]:
    lines: List[str] = []
    for k, v in d.items():
        key = f"{prefix}{k}"
        if isinstance(v, dict):
            lines.append(f"{key}:")
            lines.extend(flatten_for_text(v, prefix=prefix + "  "))
        elif isinstance(v, list):
            lines.append(f"{key}:")
            for item in v:
                if isinstance(item, (dict, list)):
                    lines.append(f"{prefix}  - {json.dumps(item, ensure_ascii=False)}")
                else:
                    lines.append(f"{prefix}  - {item}")
        else:
            lines.append(f"{key}: {v}")
    return lines


def doc_text(project_name: str, data: Dict[str, Any]) -> str:
    return f"Project: {project_name}\n" + "\n".join(flatten_for_text(data))


def main() -> None:
    parser = argparse.ArgumentParser(description="Join JSONs and embed to FAISS (CPU-light)")
    parser.add_argument("evaulations", nargs="?", default="evaulations.json", help="Path to evaulations.json")
    parser.add_argument("prf_answers", nargs="?", default="prf_answers.json", help="Path to prf_answers.json")
    parser.add_argument(
        "--model",
        default="sentence-transformers/paraphrase-MiniLM-L3-v2",
        help="Sentence-Transformers model name (lighter is faster).",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=16,
        help="Embedding batch size (lower reduces RAM/CPU).",
    )
    parser.add_argument(
        "--threads",
        type=int,
        default=None,
        help="Limit Torch/BLAS CPU threads (e.g., 1-4 for low CPU usage).",
    )
    args = parser.parse_args()

    evals_path = Path(args.evaulations)
    prf_path = Path(args.prf_answers)
    out_emb = Path("embeddings.npy")
    out_ids = Path("embedding_ids.json")
    out_faiss = Path("faiss.index")
    out_faiss_ids = Path("faiss_ids.json")

    # Optionally reduce CPU usage by limiting thread count
    if args.threads is not None and args.threads > 0:
        os.environ["OMP_NUM_THREADS"] = str(args.threads)
        os.environ["MKL_NUM_THREADS"] = str(args.threads)
        if torch is not None:
            try:
                torch.set_num_threads(args.threads)
            except Exception:
                pass

    evals_raw = load_json(evals_path)
    prf_raw = load_json(prf_path)

    evals_by = index_by_project_name(evals_raw)
    prf_by = index_by_project_name(prf_raw)

    # Join by project_name
    merged: Dict[str, Dict[str, Any]] = {}
    all_names = set(evals_by) | set(prf_by)
    for name in sorted(all_names):
        left = evals_by.get(name, {})
        right = prf_by.get(name, {})
        merged[name] = merge(left, right)

    # Build docs
    ids: List[str] = []
    texts: List[str] = []
    for name, data in merged.items():
        ids.append(name)
        texts.append(doc_text(name, data))

    if not texts:
        print("No projects found to embed.")
        return

    # Embed
    model = SentenceTransformer(args.model, device="cpu")
    embeddings = model.encode(
        texts,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True,
        batch_size=max(1, int(args.batch_size)),
    )

    # Save numpy artifacts
    np.save(out_emb, embeddings)
    out_ids.write_text(json.dumps(ids, ensure_ascii=False, indent=2), encoding="utf-8")
    # Build FAISS index (inner product; embeddings are normalized)
    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(embeddings.astype("float32", copy=False))
    faiss.write_index(index, str(out_faiss))
    out_faiss_ids.write_text(json.dumps(ids, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        f"Saved {len(ids)} embeddings to {out_emb}, IDs to {out_ids}, and FAISS index to {out_faiss} (ids: {out_faiss_ids})"
    )


if __name__ == "__main__":
    main()


