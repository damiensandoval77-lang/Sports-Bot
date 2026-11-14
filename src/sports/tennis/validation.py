"""Date-disjoint evaluation utilities; never use row position as time."""
import pandas as pd


def chronological_masks(frame, date_column='tourney_date', test_fraction=0.1,
                        embargo_days=21):
    if not 0 < test_fraction < 1 or embargo_days < 0:
        raise ValueError('Invalid holdout fraction or embargo')
    dates = pd.to_datetime(frame[date_column], errors='coerce', utc=True)
    if dates.isna().any():
        raise ValueError('Every training row needs a valid date')
    unique = sorted(dates.unique())
    if len(unique) < 2:
        raise ValueError('At least two distinct dates are required')
    cutoff = pd.Timestamp(unique[min(len(unique)-1, max(1, int(len(unique)*(1-test_fraction))))])
    # For tournament-start dates, purge possibly unfinished training tournaments.
    train = dates + pd.Timedelta(days=embargo_days) < cutoff
    test = dates >= cutoff
    if not train.any() or not test.any():
        raise ValueError('Insufficient date-disjoint history after embargo')
    return train, test, cutoff
