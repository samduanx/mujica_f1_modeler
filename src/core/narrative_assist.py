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
        },
        "moderate": {
            "probability_shift": 0.35,
            "adversity_reduction": 0.30,
        },
        "strong": {
            "probability_shift": 0.50,
            "adversity_reduction": 0.45,
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
        if not self.should_apply(team_name):
            return random.randint(1, 20)

        shift = self.config.probability_shift

        # Calculate weights for each face
        weights = []
        for face in range(1, 21):
            if face == 1:  # Critical failure - reduce significantly
                weight = 0.4
            elif face <= 5:  # Poor rolls - reduce
                weight = 1.0 - shift * 0.35
            elif face <= 10:  # Mediocre rolls - slight reduction
                weight = 1.0 - shift * 0.15
            elif face <= 15:  # Good rolls - increase
                weight = 1.0 + shift * 0.25
            elif face <= 19:  # Great rolls - more increase
                weight = 1.0 + shift * 0.45
            else:  # Natural 20 - highest increase
                weight = 1.0 + shift * 0.65
            weights.append(max(0.1, weight))

        # Weighted random selection
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
        if not self.should_apply(team_name):
            return base_probability

        reduction = self.config.adversity_reduction
        return base_probability * (1.0 - reduction)

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
        if not self.should_apply(team_name):
            return base_stability

        boost = self.config.adversity_reduction * 0.6
        return min(99.5, base_stability + boost)

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
        if not self.should_apply(team_name):
            return base_probability

        reduction = self.config.adversity_reduction
        return base_probability * (1.0 - reduction)


def get_balancer() -> ProbabilityBalancer:
    """Get the global probability balancer instance."""
    return ProbabilityBalancer()


# Convenience function for quick checks
def is_narrative_assist_enabled() -> bool:
    """Check if narrative assistance is currently enabled."""
    return NarrativeAssistConfig.get_config().enabled
