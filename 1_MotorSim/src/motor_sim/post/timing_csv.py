from pathlib import Path
import csv

def write_timing_csv(events: dict, out_path: Path):
    csv_path = out_path.with_name(out_path.stem + "_steuerzeiten.csv")
    keys = [
        "IVO_deg", "IVC_deg", "EVO_deg", "EVC_deg",
        "intake_duration_deg", "exhaust_duration_deg",
        "lift_threshold_mm", "cycle_deg", "total_overlap_deg"
    ]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["parameter", "value"])
        for k in keys:
            if k in events:
                w.writerow([k, events[k]])
    return csv_path
