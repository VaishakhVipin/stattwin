from __future__ import annotations

from typing import Iterable, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity as sk_cosine_similarity
from sklearn.metrics import pairwise_distances


def _to_matrix(X: "np.ndarray | pd.DataFrame") -> np.ndarray:
    if isinstance(X, pd.DataFrame):
        return X.values
    return X


def cosine_sim_matrix(X: "np.ndarray | pd.DataFrame") -> np.ndarray:
    """Return cosine similarity matrix for rows of X."""
    M = _to_matrix(X)
    return sk_cosine_similarity(M)


def euclidean_dist_matrix(X: "np.ndarray | pd.DataFrame") -> np.ndarray:
    """Return euclidean distance matrix for rows of X (L2)."""
    M = _to_matrix(X)
    return pairwise_distances(M, metric="euclidean")


def top_k_similar(sim_row: np.ndarray, k: int, exclude_index: Optional[int] = None) -> np.ndarray:
    """Given a similarity row (1 x N), return indices of top-k most similar (high to low).
    Optionally exclude a specific index (e.g., the query itself).
    """
    sim = sim_row.copy()
    if exclude_index is not None and 0 <= exclude_index < sim.shape[0]:
        sim[exclude_index] = -np.inf
    order = np.argsort(-sim)
    return order[:k]