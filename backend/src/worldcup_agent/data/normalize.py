import pandas as pd

from worldcup_agent.data.aliases import TEAM_ALIASES

REQUIRED_COLUMNS = {
    "date", "home_team", "away_team", "home_score", "away_score",
    "tournament", "city", "country", "neutral",
}


def normalize_matches(frame: pd.DataFrame) -> pd.DataFrame:
    missing = REQUIRED_COLUMNS - set(frame.columns)
    if missing:
        raise ValueError(f"missing match columns: {sorted(missing)}")
    result = frame.copy()
    result["date"] = pd.to_datetime(result["date"], utc=True)
    for column in ("home_team", "away_team"):
        result[column] = result[column].astype("string").str.strip().replace(TEAM_ALIASES)
    # Coerce scores to numeric and drop rows with non-finite scores or missing teams.
    result["home_score"] = pd.to_numeric(result["home_score"], errors="coerce")
    result["away_score"] = pd.to_numeric(result["away_score"], errors="coerce")
    result = result.dropna(subset=["home_score", "away_score", "home_team", "away_team"])
    result["home_score"] = result["home_score"].astype("int64")
    result["away_score"] = result["away_score"].astype("int64")
    result["neutral"] = result["neutral"].astype("string").str.lower().isin(["true", "1"]).astype("bool")
    result = result.sort_values(["date", "home_team", "away_team"]).drop_duplicates(
        ["date", "home_team", "away_team", "home_score", "away_score", "tournament"]
    )
    result["match_id"] = [f"INT-{index:06d}" for index in range(1, len(result) + 1)]
    return result.reset_index(drop=True)
