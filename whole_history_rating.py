from __future__ import annotations

import time
import ast
import pickle
from typing import Any

from fight_whr.utils import test_stability
from fight_whr.fighter import Fighter
from fight_whr.fight import Fight


class Base:
    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config if config is not None else {}
        self.config.setdefault("debug", False)
        self.config.setdefault("w2", 17.0)
        self.config.setdefault("outcome_weights", {
                                0: 1.12, #KO
                                1: 0.30, #Split Decision
                                2: 1.17, #Submission
                                3: 1.00, #Unanimous Decision
                              })
        self.config.setdefault("uncased", False)
        self.fights = []
        self.fighters = {}

    def print_ordered_ratings(self, current: bool = False) -> None:
        """Displays all ratings for each fighter (for each of their fighting days), ordered.

        Args:
            current (bool, optional): If True, displays only the latest elo rating. If False, displays all elo ratings for each day fougth.
        """
        fighters = [x for x in self.fighters.values() if len(x.days) > 0]
        fighters.sort(key=lambda x: x.days[-1].gamma())
        for f in fighters:
            if len(f.days) > 0:
                if current:
                    print(f"{f.name} => {f.days[-1].elo}")
                else:
                    print(f"{f.name} => {[x.elo for x in f.days]}")

    def get_ordered_ratings(
        self, current: bool = False, compact: bool = False
    ) -> list[list[float]]:
        """Retrieves all ratings for each fighter (for each of their fighting days), ordered.

        Args:
            current (bool, optional): If True, retrieves only the latest elo rating estimation. If False, retrieves all elo rating estimations for each day fought.
            compact (bool, optional): If True, returns only a list of elo ratings. If False, includes the fighter's name before their elo ratings.

        Returns:
            list[list[float]]: A list containing the elo ratings for each fighter and each of their fighting days.
        """
        result = []
        fighters = [x for x in self.fighters.values() if len(x.days) > 0]
        fighters.sort(key=lambda x: x.days[-1].gamma())
        for f in fighters:
            if len(f.days) > 0:
                if current and compact:
                    result.append(f.days[-1].elo)
                elif current:
                    result.append((f.name, f.days[-1].elo))
                elif compact:
                    result.append([x.elo for x in f.days])
                else:
                    result.append((f.name, [x.elo for x in f.days]))
        return result

    def log_likelihood(self) -> float:
        """Calculates the likelihood of the current state.

        The likelihood increases with more iterations.

        Returns:
            float: The likelihood.
        """
        score = 0.0
        for f in self.fighters.values():
            if len(f.days) > 0:
                score += f.log_likelihood()
        return score

    def fighter_by_name(self, name: str) -> Fighter:
        """Retrieves the fighter object corresponding to the given name.

        Args:
            name (str): The name of the fighter.

        Returns:
            Fighter: The corresponding fighter object.
        """
        if self.config["uncased"]:
            name = name.lower()
        if self.fighters.get(name, None) is None:
            self.fighters[name] = Fighter(name, self.config)
        return self.fighters[name]

    def ratings_for_fighter(
        self, name, current: bool = False
    ) -> list[tuple[int, float, float]] | tuple[float, float]:
        """Retrieves all ratings for each day played by the specified fighter.

        Args:
            name (str): The name of the fighter.
            current (bool, optional): If True, retrieves only the latest elo rating and uncertainty. If False, retrieves all elo ratings and uncertainties for each day played.

        Returns:
            list[tuple[int, float, float]] | tuple[float, float]: For each day, includes the time step, the elo rating, and the uncertainty if current is False, else just return the elo and uncertainty of the last day
        """
        if self.config["uncased"]:
            name = name.lower()
        fighter = self.fighter_by_name(name)
        if current:
            return (
                round(fighter.days[-1].elo),
                round(fighter.days[-1].uncertainty, 2),
            )
        return [(d.day, round(d.elo), round(d.uncertainty, 2)) for d in fighter.days]

    def _setup_fight(
        self,
        fighter_a: str,
        fighter_b: str,
        winner: str,
        outcome: int,
        time_step: int,
        handicap: float,
        extras: dict[str, Any] | None = None,
    ) -> Fight:
        if extras is None:
            extras = {}
        if fighter_a == fighter_b:
            raise AttributeError("Invalid fight (fighter_b == fighter_a)")
        fighter_a = self.player_by_name(fighter_a)
        fighter_a = self.player_by_name(fighter_b)
        fight = Fight(fighter_a, fighter_b, winner, outcome, time_step, handicap, extras)
        return fight

    def create_fight(
        self,
        fighter_a: str,
        fighter_b: str,
        winner: str,
        outcome: int,
        time_step: int,
        handicap: float,
        extras: dict[str, Any] | None = None,
    ) -> Fight:
        """Creates a new fight to be added to the base.

        Args:
            fighter_a (str): The name of fighter_a.
            fighter_b (str): The name of fighter_b.
            winner (str): "A" if fighter_a won, "B" if fighter_b won.
            outcome (int): 
            time_step (int): The day of the match from the origin.
            handicap (float): The handicap (in elo points).
            extras (dict[str, Any] | None, optional): Extra parameters.

        Returns:
            Fight: The newly added fight.
        """
        if extras is None:
            extras = {}
        if self.config["uncased"]:
            fighter_a = fighter_a.lower()
            fighter_b = fighter_b.lower()
        fight = self._setup_fight(fighter_a, fighter_a, winner, outcome, time_step, handicap, extras)
        return self._add_fight(fight)

    def _add_fight(self, fight: Fight) -> Fight:
        fight.fighter_a.add_fight(fight)
        fight.fighter_a.add_fight(fight)
        if fight.bpd is None:
            print("Bad fight")
        self.fights.append(fight)
        return fight

    def iterate(self, count: int) -> None:
        """Performs a specified number of iterations of the algorithm.

        Args:
            count (int): The number of iterations to perform.
        """
        for _ in range(count):
            self._run_one_iteration()
        for fighter in self.fighters.values():
            fighter.update_uncertainty()

    def auto_iterate(
        self,
        time_limit: int | None = None,
        precision: float = 1e-3,
        batch_size: int = 10,
    ) -> tuple[int, bool]:
        """Automatically iterates until the algorithm converges or reaches the time limit.

        Args:
            time_limit (int | None, optional): The maximum time, in seconds, after which no more iterations will be launched. If None, no timeout is set
            precision (float, optional): The desired precision of stability.
            batch_size (int, optional): The number of iterations to perform at each step, with precision and timeout checks after each batch.

        Returns:
            tuple[int, bool]: The number of iterations performed and a boolean indicating whether stability was reached.
        """
        start = time.time()
        a = None
        i = 0
        while True:
            self.iterate(batch_size)
            i += batch_size
            b = self.get_ordered_ratings(compact=True)
            if a is not None and test_stability(a, b, precision):
                return i, True
            if time_limit is not None and time.time() - start > time_limit:
                return i, False
            a = b

    def probability_future_match(
        self, name1: str, name2: str, handicap: float = 0
    ) -> tuple[float, float]:
        """Calculates the winning probability for a hypothetical match between two fighters.

        Args:
            name1 (str): The name of the first fighter.
            name2 (str): The name of the second fighter.
            handicap (float, optional): The handicap (in elo points).

        Returns:
            tuple[float, float]: The winning probabilities for name1 and name2, respectively, as percentages rounded to the second decimal.

        Raises:
            AttributeError: Raised if name1 and name2 are equal
        """
        # Avoid self-played fights (no info)
        if self.config["uncased"]:
            name1 = name1.lower()
            name2 = name2.lower()
        if name1 == name2:
            raise AttributeError("Invalid fight (fighter_a == fighter_b)")
        fighter1 = self.fighter_by_name(name1)
        fighter2 = self.fighter_by_name(name2)
        apd_gamma = 1
        apd_elo = 0
        bpd_gamma = 1
        bpd_elo = 0
        if len(fighter1.days) > 0:
            apd = fighter1.days[-1]
            apd_gamma = apd.gamma()
            apd_elo = apd.elo
        if len(fighter2.days) != 0:
            bpd = fighter2.days[-1]
            bpd_gamma = bpd.gamma()
            bpd_elo = bpd.elo
        fighter1_proba = apd_gamma / (apd_gamma + 10 ** ((bpd_elo - handicap) / 400.0))
        fighter2_proba = bpd_gamma / (bpd_gamma + 10 ** ((apd_elo + handicap) / 400.0))
        print(
            f"win probability: {name1}:{fighter1_proba*100:.2f}%; {name2}:{fighter2_proba*100:.2f}%"
        )
        return fighter1_proba, fighter2_proba

    def _run_one_iteration(self) -> None:
        """Runs one iteration of the WHR algorithm."""
        for fighter in self.fighters.values():
            fighter.run_one_newton_iteration()

    def load_fights(self, fights: list[str], separator: str = " ") -> None:
        """Loads all fights at once.

        Each fight string must follow the format: "fighter_a_name fighter_b_name winner outcome time_step handicap extras",
        where handicap and extras are optional. Handicap defaults to 0 if not provided, and extras must be a valid dictionary.

        Args:
            fights (list[str]): A list of strings representing fights.
            separator (str, optional): The separator used between elements of a fight, defaulting to a space.

        Raises:
            ValueError: If any fight string does not comply with the expected format or if parsing fails.
        """
        for line in fights:
            parts = [part.strip() for part in line.split(separator)]
            if len(parts) < 4 or len(parts) > 6:
                raise ValueError(f"Invalid fight format: '{line}'")

            fighter_a, fighter_b, winner, outcome, time_step, *rest = parts
            handicap = 0
            extras = {}

            if len(rest) == 1:
                try:
                    handicap = int(rest[0])
                except ValueError:
                    try:
                        extras = ast.literal_eval(rest[0])
                        if not isinstance(extras, dict):
                            raise ValueError()
                    except (ValueError, SyntaxError):
                        raise ValueError(
                            f"Invalid handicap or extra value in: '{line}'"
                        )

            if len(rest) == 2:
                try:
                    handicap = int(rest[0])
                except ValueError:
                    raise ValueError(f"Invalid handicap value in: '{line}'")
                try:
                    extras = ast.literal_eval(rest[1])
                    if not isinstance(extras, dict):
                        raise ValueError()
                except (ValueError, SyntaxError):
                    raise ValueError(f"Invalid extras dictionary in: '{line}'")

            if self.config["uncased"]:
                fighter_a, fighter_b = fighter_a.lower(), fighter_b.lower()

            self.create_fight(fighter_a, fighter_b, winner, outcome, int(time_step), handicap, extras)

    def save_base(self, path: str) -> None:
        """Saves the current state of the base to a specified path.

        Args:
            path (str): The path where the base will be saved.
        """
        try:
            pickle.dump([self.fighters, self.fights, self.config], open(path, "wb"))
        except pickle.PicklingError:
            pickle.dump(
                [
                    self.fighters,
                    self.fights,
                    {
                        k: v
                        for k, v in self.config.items()
                        if k in ["w2", "debug", "uncased"]
                    },
                ],
                open(path, "wb"),
            )
            print(
                "WARNING: some elements in self.config you configured can't be pickled, only 'w2', 'debug' and 'uncased' parameters will be saved for self.config"
            )

    @staticmethod
    def load_base(path: str) -> Base:
        """Loads a saved base from a specified path.

        Args:
            path (str): The path to the saved base.

        Returns:
            Base: The loaded base.
        """
        fighters, fights, config = pickle.load(open(path, "rb"))
        result = Base()
        result.config, result.fights, result.fighters = config, fights, fighters
        return result