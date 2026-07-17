from dataclasses import dataclass


@dataclass(frozen=True)
class MatchForElo:
    home_team: str
    away_team: str
    home_score: int
    away_score: int
    tournament: str
    neutral: bool


@dataclass(frozen=True)
class PreMatchElo:
    home_rating: float
    away_rating: float
    expected_home: float


class EloEngine:
    def __init__(self, initial: float = 1500.0, home_advantage: float = 100.0) -> None:
        self.initial = initial
        self.home_advantage = home_advantage
        self._ratings: dict[str, float] = {}

    def rating(self, team: str) -> float:
        return self._ratings.get(team, self.initial)

    def expected_home_score(self, home: str, away: str, neutral: bool) -> float:
        advantage = 0.0 if neutral else self.home_advantage
        difference = self.rating(home) + advantage - self.rating(away)
        return 1.0 / (1.0 + 10 ** (-difference / 400.0))

    @staticmethod
    def expected_home_score_from_ratings(home_rating: float, away_rating: float, neutral: bool) -> float:
        advantage = 0.0 if neutral else 100.0
        difference = home_rating + advantage - away_rating
        return 1.0 / (1.0 + 10 ** (-difference / 400.0))

    def process(self, match: MatchForElo) -> PreMatchElo:
        home_before = self.rating(match.home_team)
        away_before = self.rating(match.away_team)
        expected = self.expected_home_score(match.home_team, match.away_team, match.neutral)
        actual = 1.0 if match.home_score > match.away_score else 0.0 if match.home_score < match.away_score else 0.5
        goal_difference = abs(match.home_score - match.away_score)
        multiplier = 1.0 if goal_difference <= 1 else 1.5 if goal_difference == 2 else (11 + goal_difference) / 8
        k = self._k_factor(match.tournament)
        change = k * multiplier * (actual - expected)
        self._ratings[match.home_team] = home_before + change
        self._ratings[match.away_team] = away_before - change
        return PreMatchElo(home_before, away_before, expected)

    @staticmethod
    def _k_factor(tournament: str) -> float:
        name = tournament.casefold()
        if "world cup" in name and "qualification" not in name:
            return 60.0
        if "qualification" in name or "qualifier" in name:
            return 25.0
        if "friendly" in name:
            return 20.0
        return 35.0
