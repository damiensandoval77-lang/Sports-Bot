"""Consensus benchmark from actual matched, two-sided sportsbook markets.

This module NEVER changes the independently trained NBA player projection.
It aggregates available quotes by player/game/market and computes the median
observed prop line. A median from one book is NOT labeled consensus.
"""
from collections import defaultdict
from statistics import median
import math

def consensus_markets(valid):
    groups=defaultdict(list)
    for row in valid:
        # Identity has already passed same-current-team and two-sided checks.
        if not all(k in row for k in ("player_id","team","stat","game","start","sportsbook","line")):
            continue
        try:line=float(row["line"])
        except (TypeError,ValueError):continue
        if not math.isfinite(line):continue
        key=(str(row["player_id"]),row["team"],row["stat"],row["game"],row["start"])
        groups[key].append(row)
    output=[]
    for key,quotes in groups.items():
        by_book={}
        # Select one actual two-sided quote per source for a player/market.
        # Prefer freshest timestamp where present; stable otherwise.
        for quote in quotes:
            name=str(quote["sportsbook"]).strip()
            if not name:continue
            book_key=name.casefold()
            original=by_book.get(book_key)
            if original is None or str(quote.get("market_updated",""))>str(original.get("market_updated","")):
                by_book[book_key]=quote
        selected=sorted(by_book.values(),key=lambda r:str(r["sportsbook"]).casefold())
        if not selected:continue
        values=[float(q["line"]) for q in selected]
        count=len(selected)
        template=dict(selected[0])
        template.update({
            "line":float(median(values)),
            "line_book_count":count,
            "line_type":"MULTIBOOK_MEDIAN" if count>=2 else "SINGLE_BOOK_FALLBACK",
            "line_range":[min(values),max(values)],
            "sportsbook":"Consensus ("+str(count)+" books)" if count>=2 else selected[0]["sportsbook"],
            "book_quotes":[{"name":q["sportsbook"],"line":float(q["line"]),
                            "over":q["over_odds"],"under":q["under_odds"],
                            "updated_at":q.get("market_updated")}
                           for q in selected],
            "over_odds":None if count>=2 else selected[0]["over_odds"],
            "under_odds":None if count>=2 else selected[0]["under_odds"],
        })
        output.append(template)
    return output
