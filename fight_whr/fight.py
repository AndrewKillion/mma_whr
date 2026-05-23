from __future__ import annotations

from typing import Any

from fight_whr import fighter as FR
from fight_whr import fighterday as FD
from fight_whr.rating_bounds import opponent_adjusted_gamma_from_elo


class Fight:
    def __init__(
        self,
        fighter_a: FR.Fighter,
        fighter_b: FR.Fighter,
        winner: str,
        outcome: int,
        time_step: int,
        handicap: float = 0,
        extras: dict[str, Any] | None = None,
    ):
        self.day = time_step
        self.fighter_a = fighter_a
        self.fighter_b = fighter_b
        self.winner = winner.upper()
        self.outcome = outcome
        self.handicap = handicap
        self.apd: FD.FighterDay | None = None
        self.bpd: FD.FighterDay | None = None
        if extras is None:
            self.extras = {"komi": 6.5}
        else:
            self.extras = extras
            self.extras.setdefault("komi", 6.5)

    def __str__(self) -> str:
        return f"A:{self.fighter_a.name}(r={self.apd.r if self.apd is not None else '?'}) B:{self.fighter_b.name}(r={self.bpd.r if self.bpd is not None else '?'}) winner = {self.winner}, komi = {self.extras['komi']}, handicap = {self.handicap}"

    def opponents_adjusted_gamma(self, fighter: FR.Fighter) -> float:
        """
        Calculates the adjusted gamma value of a fighter's opponent. This is based on the opponent's
        Elo rating adjusted for the fight's handicap.

        Parameters:
            fighter (FR.Fighter): The fighter for whom to calculate the opponent's adjusted gamma.

        Returns:
            float: The adjusted gamma value of the opponent.

        Raises:
            AttributeError: If the fighter days are not set or the fighter is not part of the fight.
        """
        if self.bpd is None or self.apd is None:
            raise AttributeError("fighter_b day and fighter_a day must be set")
        if fighter == self.fighter_a:
            opponent_day = self.bpd
            handicap_elo = self.handicap
        elif fighter == self.fighter_b:
            opponent_day = self.apd
            handicap_elo = -self.handicap
        else:
            raise AttributeError(
                f"No opponent for {fighter.__str__()}, since they're not in this fight: {self.__str__()}."
            )
        # WHR fights are within one division; offsets cancel if both use internal movement.
        opponent_elo = opponent_day.internal_elo + handicap_elo
        return opponent_adjusted_gamma_from_elo(opponent_elo)

    def opponent(self, fighter: FR.Fighter) -> FR.Fighter:
        """
        Returns the opponent of the specified fighter in this fight.

        Parameters:
            fighter (FR.Fighter): The fighter whose opponent is to be found.

        Returns:
            FR.Fighter: The opponent fighter.
        """
        if fighter == self.fighter_a:
            return self.fighter_b
        return self.fighter_a

    def prediction_score(self) -> float:
        """
        Calculates the accuracy of the prediction for the fight's outcome.
        Returns a score based on the actual outcome compared to the predicted probabilities:
        - Returns 1.0 if the prediction matches the actual outcome (fighter_a or fighter_b winning as predicted).
        - Returns 0.5 if the win probability is exactly 0.5, indicating uncertainty.
        - Returns 0.0 if the prediction does not match the actual outcome.

        Returns:
            float: The prediction score of the fight.
        """
        if self.fighter_a_win_probability() == 0.5:
            return 0.5
        return (
            1.0
            if (
                (self.winner == "A" and self.fighter_a_win_probability() > 0.5)
                or (self.winner == "B" and self.fighter_a_win_probability() < 0.5)
            )
            else 0.0
        )

    def fighter_a_win_probability(self) -> float:
        """
        Calculates the win probability for fighter_a based on their gamma value and
        the adjusted gamma value of their opponent.

        Returns:
            float: The win probability for fighter_a.

        Raises:
            AttributeError: If fighter_a day is not set.
        """
        if self.apd is None:
            raise AttributeError("fighter_a day must be set")

        return self.apd.gamma() / (
            self.apd.gamma() + self.opponents_adjusted_gamma(self.fighter_a)
        )

    def fighter_b_win_probability(self) -> float:
        """
        Calculates the win probability for fighter_b based on their gamma value and
        the adjusted gamma value of their opponent.

        Returns:
            float: The win probability for fighter_b.

        Raises:
            AttributeError: If fighter_b day is not set.
        """
        if self.bpd is None:
            raise AttributeError("fighter_b day must be set")
        return self.bpd.gamma() / (
            self.bpd.gamma() + self.opponents_adjusted_gamma(self.fighter_b)
        )