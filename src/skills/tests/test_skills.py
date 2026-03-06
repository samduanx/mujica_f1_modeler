"""
Tests for the Driver Skills System.
"""

import pytest
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.skills import (
    DriverSkill,
    SkillTrigger,
    SkillEffectType,
    SkillCategory,
    SkillContext,
    SessionType,
    WeatherCondition,
    DriverSkillManager,
    get_skill_manager,
    reset_skill_manager,
    load_skills_from_csv,
    parse_skill,
    PENDING_DRIVERS,
)


class TestSkillTypes:
    """Test skill type definitions."""
    
    def test_skill_creation(self):
        """Test creating a DriverSkill."""
        skill = DriverSkill(
            name_cn="老潘课堂",
            name_en="RainMaster",
            driver="Verstappen",
            description="R+0.5 in rain",
            category=SkillCategory.WEATHER,
            trigger=SkillTrigger.WEATHER_RAIN,
            effect_type=SkillEffectType.RATING_BOOST,
            effect_value=0.5,
        )
        
        assert skill.name_cn == "老潘课堂"
        assert skill.effect_value == 0.5
        assert skill.driver == "Verstappen"
    
    def test_pending_drivers_list(self):
        """Test that pending drivers are correctly identified."""
        assert "Hamilton" in PENDING_DRIVERS
        assert "Russell" in PENDING_DRIVERS
        assert "Piastri" in PENDING_DRIVERS
        assert "Verstappen" not in PENDING_DRIVERS


class TestSkillContext:
    """Test skill context creation and queries."""
    
    def test_basic_context(self):
        """Test creating a basic context."""
        context = SkillContext(
            session_type=SessionType.RACE,
            lap_number=10,
            position=5,
        )
        
        assert context.session_type == SessionType.RACE
        assert context.lap_number == 10
        assert not context.is_qualifying()
    
    def test_qualifying_context(self):
        """Test qualifying context."""
        context = SkillContext(
            session_type=SessionType.QUALIFYING_Q3,
            is_in_danger_zone=True,
        )
        
        assert context.is_qualifying()
        assert context.get_qualifying_stage() == "Q3"
        assert context.is_in_danger()
    
    def test_weather_context(self):
        """Test weather context."""
        context = SkillContext(
            weather_condition=WeatherCondition.LIGHT_RAIN,
        )
        
        assert context.is_raining()
        assert not context.is_heavy_rain()
    
    def test_defense_context(self):
        """Test defense context."""
        context = SkillContext(
            is_defending=True,
            is_forming_train=True,
        )
        
        assert context.is_defending
        assert context.is_forming_train


class TestSkillParser:
    """Test skill parsing from CSV."""
    
    def test_parse_rain_skill(self):
        """Test parsing Verstappen's rain skill."""
        skill = parse_skill("老潘课堂", "维斯塔潘")
        
        assert skill is not None
        assert skill.name_cn == "老潘课堂"
        assert skill.name_en == "RainMaster"
        assert skill.driver == "Verstappen"
        assert skill.trigger == SkillTrigger.WEATHER_RAIN
        assert skill.effect_value == 0.5
    
    def test_parse_defense_skill(self):
        """Test parsing a defense skill."""
        skill = parse_skill("WIDELONSO", "阿隆索")
        
        assert skill is not None
        assert skill.name_cn == "WIDELONSO"
        assert skill.driver == "Alonso"
        assert skill.category == SkillCategory.DEFENSE
        assert skill.effect_value == 0.8
    
    def test_parse_pending_skill(self):
        """Test that pending skills are marked correctly."""
        skill = parse_skill("振金超车", "汉密尔顿")
        
        assert skill is not None
        assert skill.trigger == SkillTrigger.PENDING
    
    def test_load_from_csv(self):
        """Test loading all skills from CSV."""
        skills = load_skills_from_csv("data/driver_ratings.csv")
        
        # Check some drivers are loaded
        assert "Verstappen" in skills
        assert "Leclerc" in skills
        assert "Alonso" in skills
        
        # Check Verstappen has rain skill
        verstappen_skills = skills["Verstappen"]
        assert any(s.name_cn == "老潘课堂" for s in verstappen_skills)


class TestSkillEffects:
    """Test skill effect calculations."""
    
    def test_weather_skill_activation(self):
        """Test weather skill activates in rain."""
        manager = DriverSkillManager()
        
        # Verstappen in rain
        context = SkillContext(
            weather_condition=WeatherCondition.LIGHT_RAIN,
        )
        
        modifier, activations = manager.calculate_rating_modifier(
            "Verstappen", 100.5, context
        )
        
        # Should get +0.5 from 老潘课堂
        assert modifier == 0.5
        assert len(activations) == 1
        assert activations[0].skill_name_cn == "老潘课堂"
    
    def test_weather_skill_no_activation_in_dry(self):
        """Test weather skill doesn't activate in dry."""
        manager = DriverSkillManager()
        
        context = SkillContext(
            weather_condition=WeatherCondition.DRY,
        )
        
        modifier, activations = manager.calculate_rating_modifier(
            "Verstappen", 100.5, context
        )
        
        # No rain = no skill
        assert modifier == 0.0
        assert len(activations) == 0
    
    def test_defense_skill_activation(self):
        """Test defense skill activates when defending."""
        manager = DriverSkillManager()
        
        context = SkillContext(
            is_defending=True,
        )
        
        modifier, activations = manager.calculate_rating_modifier(
            "Alonso", 100.5, context
        )
        
        # Should get +0.8 from WIDELONSO
        assert modifier == 0.8
        assert len(activations) >= 1
    
    def test_qualifying_skill(self):
        """Test qualifying skill in Q3."""
        manager = DriverSkillManager()
        
        context = SkillContext(
            session_type=SessionType.QUALIFYING_Q3,
            is_in_danger_zone=True,  # Leclerc's skill requires danger
        )
        
        modifier, activations = manager.calculate_rating_modifier(
            "Leclerc", 100.4, context
        )
        
        # Should get +0.5 from 勒一圈
        assert modifier == 0.5
    
    def test_constant_skill(self):
        """Test constant skill (Vettel)."""
        manager = DriverSkillManager()
        
        # Vettel's 全能老农 is always active
        context = SkillContext()
        
        modifier, activations = manager.calculate_rating_modifier(
            "Vettel", 100.3, context
        )
        
        # Should get +0.8
        assert modifier == 0.8
    
    def test_tire_cliff_skill(self):
        """Test tire cliff skill."""
        manager = DriverSkillManager()
        
        context = SkillContext(
            is_past_tire_cliff=True,
        )
        
        modifier, activations = manager.calculate_rating_modifier(
            "Perez", 99.8, context
        )
        
        # Should get -0.3 (reduces R loss)
        assert modifier == -0.3
    
    def test_start_skill(self):
        """Test start skill."""
        manager = DriverSkillManager()
        
        context = SkillContext(
            is_race_start=True,
            is_first_lap=True,
        )
        
        modifier, activations = manager.calculate_rating_modifier(
            "Bottas", 100.2, context
        )
        
        # Should get activation (penalty or avoided)
        # The actual modifier depends on dice roll
        assert len(activations) >= 1
    
    def test_blind_box_car(self):
        """Test blind box car skill (Norris)."""
        manager = DriverSkillManager()
        
        # Roll once
        modifier1 = manager.roll_blind_box_car("Norris")
        
        # Roll again - should be same (cached per race)
        modifier2 = manager.roll_blind_box_car("Norris")
        
        assert modifier1 == modifier2
        assert modifier1 in [-0.5, -0.3, 0.0, 0.3, 0.5]


class TestSkillManager:
    """Test DriverSkillManager functionality."""
    
    def setup_method(self):
        """Reset skill manager before each test."""
        reset_skill_manager()
    
    def test_singleton(self):
        """Test skill manager singleton."""
        mgr1 = get_skill_manager()
        mgr2 = get_skill_manager()
        
        assert mgr1 is mgr2
    
    def test_get_driver_skills(self):
        """Test getting skills for a driver."""
        manager = DriverSkillManager()
        
        skills = manager.get_driver_skills("Verstappen")
        assert len(skills) >= 1
        
        # Check for specific skill
        skill_names = [s.name_cn for s in skills]
        assert "老潘课堂" in skill_names
    
    def test_has_skill(self):
        """Test checking if driver has skill."""
        manager = DriverSkillManager()
        
        assert manager.has_skill("Verstappen", "老潘课堂")
        assert not manager.has_skill("Verstappen", "WIDELONSO")
    
    def test_get_adjusted_r_value(self):
        """Test getting adjusted R value."""
        manager = DriverSkillManager()
        
        context = SkillContext(
            weather_condition=WeatherCondition.LIGHT_RAIN,
        )
        
        adjusted, modifier, activations = manager.get_adjusted_r_value(
            "Verstappen", 100.5, context
        )
        
        assert adjusted == 101.0  # 100.5 + 0.5
        assert modifier == 0.5
        assert len(activations) == 1
    
    def test_get_defense_bonus(self):
        """Test getting defense bonus."""
        manager = DriverSkillManager()
        
        context = SkillContext(
            is_defending=True,
        )
        
        bonus, activation = manager.get_defense_bonus("Alonso", context)
        
        assert bonus > 0
        assert activation is not None
    
    def test_get_attack_bonus(self):
        """Test getting attack bonus."""
        manager = DriverSkillManager()
        
        context = SkillContext(
            is_attacking=True,
            is_in_drs_zone=True,
            drs_zone_consecutive_laps=3,
        )
        
        bonus, activation = manager.get_attack_bonus("Leclerc", context)
        
        # Leclerc's 极限哥 should activate with 3+ DRS laps
        # But only if dice roll succeeds
        assert bonus != 0 or activation is not None
    
    def test_get_qualifying_modifier(self):
        """Test qualifying modifier."""
        manager = DriverSkillManager()
        
        modifier, activations = manager.get_qualifying_modifier(
            "Magnussen", "Q3"
        )
        
        # Magnussen has 排位神车
        assert modifier == 0.8
    
    def test_activation_history(self):
        """Test activation history tracking."""
        manager = DriverSkillManager()
        
        # Trigger some skills
        context = SkillContext(
            weather_condition=WeatherCondition.LIGHT_RAIN,
        )
        
        manager.calculate_rating_modifier("Verstappen", 100.5, context)
        
        # Check history
        history = manager.get_activation_history("Verstappen")
        assert len(history) >= 1
        
        # Check all history
        all_history = manager.get_activation_history()
        assert len(all_history) >= 1
    
    def test_get_drivers_with_skill(self):
        """Test finding drivers by skill."""
        manager = DriverSkillManager()
        
        drivers = manager.get_driver_with_skill("保胎大师")
        
        # Perez and Albon have this skill
        assert "Perez" in drivers
        assert "Albon" in drivers
    
    def test_pending_skills_list(self):
        """Test getting pending skills."""
        manager = DriverSkillManager()
        
        pending = manager.get_all_pending_skills()
        
        # Hamilton, Russell, Piastri should have pending skills
        assert "Hamilton" in pending or "Russell" in pending or "Piastri" in pending


class TestSkillIntegration:
    """Integration tests for skills with various contexts."""
    
    def test_multiple_skills_same_driver(self):
        """Test driver with multiple skills."""
        manager = DriverSkillManager()
        
        # Sainz has two skills
        skills = manager.get_driver_skills("Sainz")
        assert len(skills) >= 2
    
    def test_skill_vs_specific_driver(self):
        """Test skill against specific driver."""
        manager = DriverSkillManager()
        
        context = SkillContext(
            opponent_name="Magnussen",
            opponent_is_specific_target=True,
        )
        
        modifier, activations = manager.calculate_rating_modifier(
            "Hulkenberg", 100.1, context
        )
        
        # Hulkenberg's 嗦球队 vs Magnussen
        assert modifier == 0.5
    
    def test_team_order_skill(self):
        """Test team order skill."""
        manager = DriverSkillManager()
        
        context = SkillContext(
            team_order_issued=True,
            teammate_name="Zhou",
        )
        
        modifier, activations = manager.calculate_rating_modifier(
            "Bottas", 100.2, context
        )
        
        # Bottas's 好大哥 when helping Zhou
        assert modifier == 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
