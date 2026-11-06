from pathlib import Path
import json
from datetime import datetime, timezone

root = Path(__file__).resolve().parents[1]
names = ("PTS", "REB", "AST", "PRA", "PR", "PA", "RA")
available = {name: (root / "models" / "nba" / (name + "_model.json")).is_file() for name in names}
status = {
    "checked_at": datetime.now(timezone.utc).isoformat(),
    "model_files_present": available,
    "training_dataset_present": (root / "data" / "nba" / "processed" / "training_dataset.csv").is_file(),
    "ready_for_inference": all(available.values()),
    "message": "Model artifacts detected" if all(available.values()) else "Trained models missing. AI projections are not available."
}
(root / "docs" / "model_status.json").write_text(json.dumps(status, indent=2) + "\n")
print(status["message"])
