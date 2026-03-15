from pathlib import Path
from typing import Tuple
import numpy as np

def load_3col(path: str) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Table not found: {path}")
    rows = []
    for line in p.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        parts = s.split()
        if len(parts) < 3:
            continue
        rows.append((float(parts[0]), float(parts[1]), float(parts[2])))
    if len(rows) < 2:
        raise ValueError(f"Not enough rows in {path}")
    arr = np.array(rows, dtype=float)
    return arr[:,0], arr[:,1], arr[:,2]

def load_4col(path: str) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Table not found: {path}")
    rows = []
    for line in p.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        parts = s.split()
        if len(parts) < 4:
            continue
        rows.append((float(parts[0]), float(parts[1]), float(parts[2]), float(parts[3])))
    if len(rows) < 2:
        raise ValueError(f"Not enough rows in {path}")
    arr = np.array(rows, dtype=float)
    return arr[:,0], arr[:,1], arr[:,2], arr[:,3]
