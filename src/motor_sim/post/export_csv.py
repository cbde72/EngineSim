from pathlib import Path
import pandas as pd

def ensure_dir(path: str) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p

#def write_csv(df: pd.DataFrame, out_dir: Path, name: str) -> Path:
#    out_path = out_dir / name
#    df.to_csv(out_path, index=False)
#    return out_path

def write_csv(df: pd.DataFrame, out_dir: Path, name: str) -> Path:
    out_path = out_dir / name
    df.to_csv(out_path, index=False, sep=";", encoding="utf-8-sig")
    return out_path