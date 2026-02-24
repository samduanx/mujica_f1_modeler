"""
Tests for Red Flag System.
"""

import pytest
from incidents.red_flag import (
    RaceEndReason,
    RaceCompletionStatus,
    RedFlagOutcome,
    RestartType,
    RedFlagRaceDistanceRules,
    RedFlagTrigger,
    RedFlagManager,
    RedFlagRestart,
)


class TestRedFlagRaceDistanceRules:
    """Test race distance threshold logic"""

    def setup_method(self):
        self.rules = RedFlagRaceDistanceRules()

    def test_early_red_flag_restart(self):
        """Red flag at 20% - should restart"""
        result = self.rules.determine_outcome(
            completed_laps=14,
            total_laps=70,
            race_time=900,  # 15 minutes
        )

        assert result["outcome"] == RedFlagOutcome.RESTART.value
        assert result["end_reason"] == RaceEndReason.RED_FLAG_RESTART
        assert result["remaining_laps"] == 56
        assert result["full_points"] is False

    def test_mid_red_flag_restart(self):
        """Red flag at 60% - should restart (can fit within time)"""
        result = self.rules.determine_outcome(
            completed_laps=42,
            total_laps=70,
            race_time=3000,  # 50 minutes - can still restart
        )

        assert result["outcome"] == RedFlagOutcome.RESTART.value
        assert result["end_reason"] == RaceEndReason.RED_FLAG_RESTART
        assert result["remaining_laps"] == 28

    def test_late_red_flag_insufficient_time(self):
        """Red flag at 80% - should end due to insufficient time"""
        result = self.rules.determine_outcome(
            completed_laps=56,
            total_laps=70,
            race_time=6800,  # ~113 minutes - not enough time to restart
        )

        assert result["outcome"] == RedFlagOutcome.END.value
        assert result["end_reason"] == RaceEndReason.RED_FLAG_TIME
        assert result["insufficient_time"] is True
        assert result["full_points"] is True  # Full points if >75%
        assert result["classification_lap"] == 56

    def test_very_late_red_flag_threshold(self):
        """Red flag at 95% - should end (threshold met)"""
        result = self.rules.determine_outcome(
            completed_laps=67,
            total_laps=70,
            race_time=6000,  # 100 minutes
        )

        assert result["outcome"] == RedFlagOutcome.END.value
        assert result["end_reason"] == RaceEndReason.RED_FLAG_THRESHOLD
        assert result["full_points"] is True
        assert result["classification_lap"] == 67

    def test_race_abandoned(self):
        """Red flag before 2 laps - should abandon"""
        result = self.rules.determine_outcome(
            completed_laps=1,
            total_laps=70,
            race_time=120,
        )

        assert result["outcome"] == RedFlagOutcome.ABANDON.value
        assert result["end_reason"] == RaceEndReason.ABANDONED
        assert result["full_points"] is False
        assert result["points_percentage"] == 0.0

    def test_normal_race_completion(self):
        """Race completed - full points"""
        result = self.rules.determine_outcome(
            completed_laps=70,
            total_laps=70,
            race_time=5400,  # 90 minutes
        )

        # This would be handled by normal race end, not red flag
        assert result["outcome"] == RedFlagOutcome.RESTART.value  # Not triggered
        assert result["remaining_laps"] == 0


class TestRedFlagTrigger:
    """Test red flag trigger conditions"""

    def setup_method(self):
        self.trigger = RedFlagTrigger()

    def test_track_blocked(self):
        """Should trigger when track is blocked"""
        should_red_flag, reason = self.trigger.should_red_flag(
            incidents=[],
            track_blocked=True,
        )

        assert should_red_flag is True
        assert "blocked" in reason.lower()

    def test_severe_weather(self):
        """Should trigger in severe weather"""
        should_red_flag, reason = self.trigger.should_red_flag(
            incidents=[],
            weather="heavy_rain",
        )

        assert should_red_flag is True
        assert "weather" in reason.lower()

    def test_no_trigger_dry_conditions(self):
        """Should not trigger in normal conditions"""
        should_red_flag, reason = self.trigger.should_red_flag(
            incidents=[],
            weather="dry",
            track_blocked=False,
        )

        assert should_red_flag is False
        assert "no red flag" in reason.lower()


class TestRedFlagManager:
    """Test red flag manager"""

    def setup_method(self):
        self.manager = RedFlagManager(total_laps=70, track_length_km=4.657)

    def test_show_red_flag(self):
        """Test showing red flag"""
        success, message = self.manager.show_red_flag(
            race_time=3000,
            lap=45,
            reason="Multiple collisions",
            car_positions={"VER": 300.5, "HAM": 295.2},
        )

        assert success is True
        assert self.manager.is_red_flag is True
        assert self.manager.start_time == 3000
        assert self.manager.start_lap == 45
        assert len(self.manager.red_flag_periods) == 1

    def test_show_red_flag_already_active(self):
        """Test showing red flag when already active"""
        self.manager.show_red_flag(race_time=3000, lap=45, reason="Test")

        success, message = self.manager.show_red_flag(
            race_time=3100, lap=45, reason="Another"
        )

        assert success is False
        assert "already" in message.lower()

    def test_assess_race_status(self):
        """Test assessing race status"""
        self.manager.show_red_flag(race_time=3000, lap=45, reason="Test")
        result = self.manager.assess_race_status()

        assert "outcome" in result
        assert "end_reason" in result

    def test_resume_race(self):
        """Test resuming race after red flag"""
        self.manager.show_red_flag(race_time=3000, lap=45, reason="Test")
        self.manager.assess_race_status()  # Determine outcome

        result = self.manager.resume_race(race_time=3600)

        assert self.manager.is_red_flag is False
        assert result["outcome"] == "restart"
        assert result["remaining_laps"] == 25  # 70 - 45

    def test_end_race_early(self):
        """Test ending race early"""
        self.manager.show_red_flag(race_time=6000, lap=65, reason="Test")
        self.manager.assess_race_status()

        result = self.manager.end_race_early(race_time=6100)

        assert self.manager.is_red_flag is False
        assert result["outcome"] == "ended"

    def test_get_points_info(self):
        """Test getting points info for points calculation"""
        self.manager.show_red_flag(race_time=6000, lap=65, reason="Test")
        self.manager.assess_race_status()

        points_info = self.manager.get_points_info()

        assert "end_reason" in points_info
        assert "full_points" in points_info
        assert "insufficient_time" in points_info


class TestRedFlagRestart:
    """Test red flag restart"""

    def setup_method(self):
        self.manager = RedFlagManager(total_laps=70)
        self.manager.show_red_flag(race_time=3000, lap=45, reason="Test")
        self.restart = RedFlagRestart(self.manager)

    def test_prepare_standing_restart(self):
        """Test preparing standing restart grid"""
        grid_positions = {
            "VER": 1,
            "HAM": 2,
            "NOR": 3,
            "LEC": 4,
            "ALO": 5,
        }

        result = self.restart.prepare_standing_restart(grid_positions)

        assert result["restart_type"] == RestartType.STANDING.value
        assert result["grid"] == ["VER", "HAM", "NOR", "LEC", "ALO"]
        assert result["positions"]["VER"] == 1
        assert result["total_cars"] == 5

    def test_prepare_restart_with_retired(self):
        """Test preparing grid with retired cars"""
        grid_positions = {
            "VER": 1,
            "HAM": 2,
            "NOR": 3,
            "LEC": 4,
            "ALO": 5,
        }
        car_status = {
            "VER": "running",
            "HAM": "running",
            "NOR": "retired",
            "LEC": "running",
            "ALO": "retired",
        }

        result = self.restart.prepare_standing_restart(grid_positions, car_status)

        assert result["total_cars"] == 3
        assert "NOR" not in result["grid"]
        assert "ALO" not in result["grid"]

    def test_get_restart_message(self):
        """Test getting restart message"""
        message = self.restart.get_restart_message()

        # Red flag is shown but outcome not determined
        assert "suspended" in message.lower() or "resume" in message.lower()


class TestRaceEndReason:
    """Test race end reason enum for points calculation"""

    def test_all_end_reasons_defined(self):
        """Verify all end reasons are defined"""
        reasons = [
            RaceEndReason.NORMAL,
            RaceEndReason.RED_FLAG_TIME,
            RaceEndReason.RED_FLAG_THRESHOLD,
            RaceEndReason.RED_FLAG_RESTART,
            RaceEndReason.ABANDONED,
        ]

        assert len(reasons) == 5

    def test_insufficient_time_flag(self):
        """Test that insufficient_time is properly flagged"""
        rules = RedFlagRaceDistanceRules()

        # 80% but not enough time
        result = rules.determine_outcome(56, 70, 6900)

        assert result.get("insufficient_time") is True
        assert result["end_reason"] == RaceEndReason.RED_FLAG_TIME

    def test_threshold_flag(self):
        """Test that >90% is properly flagged"""
        rules = RedFlagRaceDistanceRules()

        # 95%
        result = rules.determine_outcome(67, 70, 6000)

        assert result.get("insufficient_time") is False
        assert result["end_reason"] == RaceEndReason.RED_FLAG_THRESHOLD


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
