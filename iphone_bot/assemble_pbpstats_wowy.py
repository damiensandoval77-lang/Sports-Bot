"""Assemble two authorized, date-bounded PBP Stats WOWY JSON exports.

This tool does not call any provider API. It requires separate raw WITH and
WITHOUT captures, each with its exact query params and independently verified
game-level participation evidence, plus explicit rights review. No provider
source rows or approval papers are ever committed or published.
"""
import argparse
import json
from pathlib import Path

try:
    from .pbpstats_wowy_adapter import normalize_pair
    from .pbpstats_game_coverage import audit_pair
    from .import_authorized_onoff import validate,ROOT,FORM,PRIVATE
except ImportError:
    from pbpstats_wowy_adapter import normalize_pair
    from pbpstats_game_coverage import audit_pair
    from import_authorized_onoff import validate,ROOT,FORM,PRIVATE

def assemble(bundle,approval,form):
    """Returns safe normalized licensed export; refuses unverifiable game logs."""
    if not isinstance(bundle,dict) or not isinstance(bundle.get("pairs"),list) or not bundle["pairs"]:
        raise ValueError("Missing authorized PBP Stats ON/OFF response pairs")
    raw=[]
    for i,pair in enumerate(bundle["pairs"]):
        if not isinstance(pair,dict):
            raise ValueError(f"Invalid response pair {i}")
        required=("with_response","without_response","player_id","teammate_id",
                  "team","with_provenance","without_provenance")
        missing=[key for key in required if key not in pair]
        if missing:raise ValueError(f"Response pair {i} missing {missing}")
        # Require independently sourced target/teammate dated on-court stints.
        # The provenance game-date arrays must agree with independently
        # recomputed ON and OFF intervals, not just a self-declared flag.
        if "target_distribution" not in pair or "teammate_distribution" not in pair:
            raise ValueError("Missing independent player stint distributions")
        coverage=audit_pair(pair["target_distribution"],pair["teammate_distribution"],
            player_id=pair["player_id"],teammate_id=pair["teammate_id"],
            cutoff_date=pair["data_through"])
        for name in ("with","without"):
            source_proof=pair[name+"_provenance"]
            if sorted(source_proof.get("game_dates",[]))!=coverage[name]["game_dates"]:
                raise ValueError("Independent "+name+" on/off games do not match provider proof")
        normalized=normalize_pair(pair["with_response"],pair["without_response"],
            player_id=pair["player_id"],teammate_id=pair["teammate_id"],
            team=pair["team"],season=bundle["season"],
            provider_generated_at=bundle["generated_at"],
            observed_through_at=pair["observed_through_at"],
            data_through=pair["data_through"],
            with_provenance=pair["with_provenance"],
            without_provenance=pair["without_provenance"])
        for name in ("with","without"):
            if abs(normalized[name]["minutes"]-coverage[name]["minutes"])>max(3,coverage[name]["minutes"]*.03):
                raise ValueError("Provider "+name+" exposure does not match game-level teammate stints")
        raw.append(normalized)
    return validate({"season":bundle["season"],"source":bundle["source"],
          "generated_at":bundle["generated_at"],"observations":raw},
          approval,form)

def main(argv=None):
    parser=argparse.ArgumentParser(description="Assemble approved dated WOWY captures, never fetch over network")
    parser.add_argument("--bundle",type=Path,required=True)
    parser.add_argument("--approval",type=Path,required=True)
    parser.add_argument("--form",type=Path,default=FORM)
    parser.add_argument("--output",type=Path,default=PRIVATE)
    args=parser.parse_args(argv)
    if not args.output.resolve().is_relative_to((ROOT/"data/nba/private").resolve()):
        parser.error("Output must be in gitignored data/nba/private")
    try:
        complete=assemble(json.loads(args.bundle.read_text()),
             json.loads(args.approval.read_text()),
             json.loads(args.form.read_text()))
    except (ValueError,OSError,KeyError,json.JSONDecodeError) as error:
        parser.error(str(error))
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(complete,indent=2)+"\n")
    print("Verified private ON/OFF research pairs:",len(complete["observations"]),
          "No network calls, no public provider data, no live model changes.")

if __name__=="__main__":main()
