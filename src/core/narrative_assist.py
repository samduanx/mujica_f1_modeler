"""
Narrative Assistance Module

Provides optional probability balancing to help the simulation
generate more compelling story outcomes. This is useful for
narrative-driven simulations where certain teams are the focus
of the storyline (e.g., protagonist teams in doujin works).

Usage:
    Set F1_NARRATIVE_ASSIST environment variable to enable:
    - "subtle": Minor adjustments for story flow
    - "moderate": Balanced assistance
    - "strong": Significant narrative guidance
    - "ultra": Maximum narrative enforcement with locked dice

Note: This module does not modify any data files. All adjustments
are applied at runtime and only affect the current simulation session.
"""

import os
import random
from typing import List, Optional


class NarrativeAssistConfig:
    """
    Configuration for narrative assistance features.

    This class manages probability adjustments that can help guide
    simulation outcomes toward more narratively satisfying results.
    Commonly used when simulating seasons with a clear protagonist
    team or storyline focus.
    """

    _instance = None

    # Intensity presets for narrative flow
    INTENSITY_PRESETS = {
        "subtle": {
            "probability_shift": 0.20,  # 20% bias toward better outcomes
            "adversity_reduction": 0.15,  # 15% fewer setbacks
            "opponent_debuff": 0.08,
            "strategy_bias": 0.20,
        },
        "moderate": {
            "probability_shift": 0.35,
            "adversity_reduction": 0.30,
            "opponent_debuff": 0.18,
            "strategy_bias": 0.40,
        },
        "strong": {
            "probability_shift": 0.50,
            "adversity_reduction": 0.45,
            "opponent_debuff": 0.30,
            "strategy_bias": 0.65,
        },
        "ultra": {
            "probability_shift": 0.72,
            "adversity_reduction": 0.62,
            "opponent_debuff": 0.42,
            "strategy_bias": 0.92,
            "dice_lock": True,
            "strategy_lock": True,
        },
    }

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        # Initialize default values
        self.enabled: bool = False
        self.intensity: Optional[str] = None
        self.target_team: str = "Ferrari"
        self.probability_shift: float = 0.0
        self.adversity_reduction: float = 0.0
        self.opponent_debuff: float = 0.0
        self.strategy_bias: float = 0.0
        self.dice_lock: bool = False
        self.strategy_lock: bool = False
        self._load_from_environment()
        self._initialized = True

    def _load_from_environment(self):
        """Load configuration from environment variables."""
        assist_level = os.environ.get("F1_NARRATIVE_ASSIST", "").lower()

        self.enabled = assist_level in self.INTENSITY_PRESETS
        self.intensity = assist_level if self.enabled else None

        # Target team can be specified (default: Ferrari as common protagonist)
        self.target_team = os.environ.get("F1_ASSIST_TARGET", "Ferrari")

        if self.enabled and self.intensity:
            preset = self.INTENSITY_PRESETS[self.intensity]
            self.probability_shift = preset["probability_shift"]
            self.adversity_reduction = preset["adversity_reduction"]
            self.opponent_debuff = preset.get("opponent_debuff", 0.0)
            self.strategy_bias = preset.get("strategy_bias", 0.0)
            self.dice_lock = bool(preset.get("dice_lock", False))
            self.strategy_lock = bool(preset.get("strategy_lock", False))
        else:
            self.dice_lock = False
            self.strategy_lock = False

    @classmethod
    def get_config(cls) -> "NarrativeAssistConfig":
        """Get the global configuration instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def is_target_team(self, team_name: str) -> bool:
        """Check if the given team is the narrative focus."""
        if not team_name:
            return False
        return team_name.lower() == self.target_team.lower()

    def is_ultra(self) -> bool:
        """Check whether the strongest narrative preset is active."""
        return self.enabled and self.intensity == "ultra"

    def get_locked_roll(self, team_name: str, sides: int) -> Optional[int]:
        """Return a deterministic roll for ultra mode when dice locking is enabled."""
        if not self.enabled or not self.dice_lock or sides <= 1:
            return None
        if self.is_target_team(team_name):
            return sides
        if team_name and not self.is_target_team(team_name):
            return 1
        return None

    def reload(self):
        """Reload configuration (for switching mid-session)."""
        self._load_from_environment()


class ProbabilityBalancer:
    """
    Runtime probability balancer for narrative consistency.

    This class provides methods to adjust probabilities at runtime
    without modifying any stored data. Adjustments are ephemeral
    and only affect the current simulation run.
    """

    def __init__(self):
        self.config = NarrativeAssistConfig.get_config()

    def should_apply(self, team_name: str) -> bool:
        """Check if balancing should be applied for this team."""
        return self.config.enabled and self.config.is_target_team(team_name)

    def should_debuff(self, team_name: str) -> bool:
        """Check if opponent debuff should be applied for this team."""
        if not self.config.enabled or not team_name:
            return False
        return not self.config.is_target_team(team_name)

    def generate_weighted_d20(self, team_name: str) -> int:
        """
        Generate a weighted d20 roll for narrative balance.

        Uses probability weighting to favor better outcomes for the
        protagonist team while maintaining plausible randomness.

        Args:
            team_name: The team rolling the dice

        Returns:
            A value between 1-20 with weighted probability
        """
        if not self.config.enabled:
            return random.randint(1, 20)

        locked_roll = self.config.get_locked_roll(team_name, 20)
        if locked_roll is not None:
            return locked_roll

        is_target = self.should_apply(team_name)
        is_opponent = self.should_debuff(team_name)
        if not is_target and not is_opponent:
            return random.randint(1, 20)

        shift = (
            self.config.probability_shift
            if is_target
            else self.config.opponent_debuff
        )

        weights = []
        for face in range(1, 21):
            if is_target:
                if face == 1:
                    weight = 0.4
                elif face <= 5:
                    weight = 1.0 - shift * 0.35
                elif face <= 10:
                    weight = 1.0 - shift * 0.15
                elif face <= 15:
                    weight = 1.0 + shift * 0.25
                elif face <= 19:
                    weight = 1.0 + shift * 0.45
                else:
                    weight = 1.0 + shift * 0.65
            else:
                if face == 1:
                    weight = 1.0 + shift * 0.35
                elif face <= 5:
                    weight = 1.0 + shift * 0.20
                elif face <= 10:
                    weight = 1.0 + shift * 0.10
                elif face <= 15:
                    weight = 1.0 - shift * 0.20
                elif face <= 19:
                    weight = 1.0 - shift * 0.35
                else:
                    weight = 1.0 - shift * 0.50
            weights.append(max(0.1, weight))

        return random.choices(range(1, 21), weights=weights)[0]

    def balance_error_probability(
        self, base_probability: float, team_name: str
    ) -> float:
        """
        Balance driver error probability for narrative flow.

        Reduces error probability for the protagonist team to help
        them perform closer to their potential.

        Args:
            base_probability: Original error probability
            team_name: Team to check

        Returns:
            Adjusted probability
        """
        if self.should_apply(team_name):
            reduction = self.config.adversity_reduction
            return base_probability * (1.0 - reduction)

        if self.should_debuff(team_name):
            increase = self.config.opponent_debuff * 0.7
            return min(1.0, base_probability * (1.0 + increase))

        return base_probability

    def balance_stability(self, base_stability: float, team_name: str) -> float:
        """
        Balance team stability for narrative flow.

        Increases stability for the protagonist team, reducing
        the likelihood of mechanical failures.

        Args:
            base_stability: Original stability value
            team_name: Team to check

        Returns:
            Adjusted stability
        """
        if self.should_apply(team_name):
            boost = self.config.adversity_reduction * 0.6
            return min(99.5, base_stability + boost)

        if self.should_debuff(team_name):
            drop = self.config.opponent_debuff * 2.0
            return max(88.0, base_stability - drop)

        return base_stability

    def balance_incident_probability(
        self, base_probability: float, team_name: str
    ) -> float:
        """
        Balance general incident probability.

        Args:
            base_probability: Original incident probability
            team_name: Team to check

        Returns:
            Adjusted probability
        """
        if self.should_apply(team_name):
            reduction = self.config.adversity_reduction
            return base_probability * (1.0 - reduction)

        if self.should_debuff(team_name):
            increase = self.config.opponent_debuff * 0.55
            return min(1.0, base_probability * (1.0 + increase))

        return base_probability

    def shape_strategy_weights(self, team_name: str, w1: float, w2: float) -> tuple[float, float]:
        """Shape 1-stop/2-stop weights based on narrative intensity and team role."""
        if not self.config.enabled:
            return (w1, w2)

        if self.config.is_ultra() and self.config.strategy_lock:
            if self.should_apply(team_name):
                preferred = 1 if w1 >= w2 else 2
                return (0.995, 0.005) if preferred == 1 else (0.005, 0.995)
            if self.should_debuff(team_name):
                inverted = 2 if w1 >= w2 else 1
                return (0.995, 0.005) if inverted == 1 else (0.005, 0.995)

        total = max(1e-9, w1 + w2)
        p1 = max(0.001, min(0.999, w1 / total))
        p2 = max(0.001, min(0.999, w2 / total))

        if self.should_apply(team_name):
            gamma = 1.0 + (self.config.strategy_bias * (1.8 if self.config.is_ultra() else 1.0))
            p1 = p1**gamma
            p2 = p2**gamma
        elif self.should_debuff(team_name):
            gamma = 1.0 + self.config.strategy_bias * (1.2 if self.config.is_ultra() else 0.6)
            p1 = (1.0 - p1) ** gamma
            p2 = (1.0 - p2) ** gamma
        else:
            return (w1, w2)

        norm = max(1e-9, p1 + p2)
        return (p1 / norm, p2 / norm)


def get_balancer() -> ProbabilityBalancer:
    """Get the global probability balancer instance."""
    return ProbabilityBalancer()


# Convenience function for quick checks
def is_narrative_assist_enabled() -> bool:
    """Check if narrative assistance is currently enabled."""
    return NarrativeAssistConfig.get_config().enabled
