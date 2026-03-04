import argparse
import fastf1
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import random
import os
from collections import defaultdict


## Use non-interactive backend to avoid font and GUI issues
# matplotlib.use("Agg")

# Define available fonts and fallback fonts
FONTS = [
    "DejaVu Sans",
    "Arial",
    "Liberation Sans",
    "sans-serif",
]
plt.rcParams["font.family"] = [
    "DejaVu Sans",
    "Arial",
    "Liberation Sans",
    "sans-serif",
]
plt.rcParams["font.size"] = 16
plt.rcParams["axes.unicode_minus"] = False

# Output directories for simulation artifacts
OUTPUT_BASE_DIR = os.path.join("outputs", "long_dist_sim")
FIGS_OUTPUT_DIR = os.path.join(OUTPUT_BASE_DIR, "figs")
REPORT_OUTPUT_DIR = os.path.join(OUTPUT_BASE_DIR, "reports")

for directory in (FIGS_OUTPUT_DIR, REPORT_OUTPUT_DIR):
    os.makedirs(directory, exist_ok=True)

# Ensure cache directory exists before enabling FastF1 cache
os.makedirs("outputs/f1_cache", exist_ok=True)
# Enable FastF1 cache
fastf1.Cache.enable_cache("outputs/f1_cache")
fastf1.set_log_level("ERROR")


# Smart legend handling function
def get_smart_legend_indices(total_items, max_display=15, always_show_first=5):
    """
    Generate indices for legend items to display intelligently
    Returns a list of indices to show in legend
    """
    if total_items <= max_display:
        return list(range(total_items))

    # Always show first few items
    indices = list(range(always_show_first))

    # Calculate spacing for remaining items
    remaining_items = total_items - always_show_first
    remaining_slots = max_display - always_show_first
    spacing = max(1, remaining_items // remaining_slots)

    # Add evenly spaced items from the remaining
    for i in range(always_show_first, total_items, spacing):
        if len(indices) < max_display:
            indices.append(i)

    return indices[:max_display]


def roll_d3_tyre_choice(track_name=None, avoid_compound=None):
    """
    使用d3骰子随机选择轮胎配方
    1 = 软胎 (C5 - 最软)
    2 = 中性胎 (C3 - 中性)
    3 = 硬胎 (C1 - 最硬)

    可以根据赛道调整可用的轮胎配方
    avoid_compound: 避免选择的轮胎配方
    """
    # 基础轮胎映射 (C标号越大越软)
    tyre_mapping = {
        1: "C3",  # 软胎
        2: "C2",  # 中性胎
        3: "C1",  # 硬胎
    }

    # 掷d3骰子
    roll = random.randint(1, 3)
    selected_tyre = tyre_mapping[roll]

    # 如果选中的轮胎需要避免，重新掷骰子（最多重试2次）
    if avoid_compound and selected_tyre == avoid_compound:
        for _ in range(2):
            roll = random.randint(1, 3)
            selected_tyre = tyre_mapping[roll]
            if selected_tyre != avoid_compound:
                break

    return selected_tyre


def get_available_compounds_for_track(track_name):
    """
    根据赛道获取可用的轮胎配方
    基于实际F1轮胎分配规则
    """
    # 2022年西班牙大奖赛可用轮胎: C1, C2, C3
    # 这里使用简化的规则，实际应该从配置文件读取
    available_compounds = {
        "Spain": ["C1", "C2", "C3"],
        "Bahrain": ["C1", "C2", "C3"],
        "Monaco": ["C3", "C4", "C5"],
        "Silverstone": ["C1", "C2", "C3"],
        # 默认使用C1, C2, C3
        "default": ["C1", "C2", "C3"],
    }

    return available_compounds.get(track_name, available_compounds["default"])


def roll_tyre_for_track(track_name, avoid_compound=None):
    """
    为特定赛道掷骰选择轮胎
    适配赛道可用的轮胎配方，考虑赛道特性
    avoid_compound: 避免选择的轮胎配方
    """
    available = get_available_compounds_for_track(track_name)

    # 获取赛道特性权重
    weights = get_track_tyre_weights(track_name)

    # 根据权重选择轮胎，但考虑避免特定轮胎
    available_with_weights = []
    for compound in available:
        if compound == avoid_compound:
            # 降低被避免轮胎的权重，但仍保留一定概率
            adjusted_weight = weights.get(compound, 1.0) * 0.1
        else:
            adjusted_weight = weights.get(compound, 1.0)
        available_with_weights.append((compound, adjusted_weight))

    # 归一化权重
    total_weight = sum(weight for _, weight in available_with_weights)
    if total_weight > 0:
        probabilities = [weight / total_weight for _, weight in available_with_weights]
        compounds = [compound for compound, _ in available_with_weights]
        return random.choices(compounds, weights=probabilities)[0]

    # 备用方案：随机选择
    return random.choice(available)


def get_track_tyre_weights(track_name):
    """
    根据赛道特性返回轮胎选择权重
    不同赛道对不同轮胎配方的偏好
    """
    # 轮胎权重配置：C1(硬), C2(中硬), C3(中性), C4(软), C5(最软)
    track_weights = {
        "Spain": {"C1": 0.15, "C2": 0.25, "C3": 0.6},  # 西班牙：偏中性胎
        "Monaco": {"C3": 0.2, "C4": 0.35, "C5": 0.45},  # 摩纳哥：偏软胎
        "Bahrain": {"C1": 0.2, "C2": 0.3, "C3": 0.5},  # 巴林：平衡但偏中性
        "Silverstone": {"C1": 0.25, "C2": 0.35, "C3": 0.4},  # 银石：偏硬胎
        "Hungary": {"C1": 0.1, "C2": 0.25, "C3": 0.65},  # 匈牙利：强偏中性胎
        "Monza": {"C1": 0.3, "C2": 0.4, "C3": 0.3},  # 蒙扎：偏硬胎
        "Singapore": {"C2": 0.15, "C3": 0.35, "C4": 0.5},  # 新加坡：偏软胎
    }

    return track_weights.get(track_name, {"C1": 0.33, "C2": 0.33, "C3": 0.34})


def get_team_strategy(track_name, team_name, num_laps, pit_data):
    """
    为车队生成统一的进站策略
    同一车队的两名车手使用相同的进站次数和轮胎配方集合
    """
    # 确定进站次数策略 - 为每个车队独立生成
    strategy = determine_pit_strategy(track_name, pit_data)

    # 生成轮胎配方集合（车队统一，但顺序可以不同）
    tyre_compounds_set = generate_team_tyre_compounds(
        track_name, int(strategy), num_laps
    )

    return {"strategy": strategy, "tyre_compounds_set": tyre_compounds_set}


def generate_team_tyre_compounds(track_name, num_stops, num_laps):
    """
    为车队生成统一的轮胎配方集合
    车手可以以不同顺序使用这些轮胎
    根据F1规则，必须使用两种或以上不同种类的轮胎
    """
    total_tyres = num_stops + 1  # 发车胎 + 进站轮胎
    available_compounds = get_available_compounds_for_track(track_name)

    # 如果只有一种轮胎可选，直接返回
    if len(available_compounds) < 2:
        return [roll_tyre_for_track(track_name) for _ in range(total_tyres)]

    # 生成轮胎配方集合（包含发车胎和所有进站轮胎）
    tyre_compounds = []

    # 发车轮胎
    starting_tyre = roll_tyre_for_track(track_name)
    tyre_compounds.append(starting_tyre)

    # 为每次进站选择轮胎配方
    used_compounds = {starting_tyre}

    for i in range(num_stops):
        # 使用智能轮胎选择确保F1规则合规
        force_different = len(used_compounds) < 2

        if i == 0:
            # 第一次进站：必须选择与发车胎不同的轮胎
            pit_tyre = smart_tyre_selection(
                track_name,
                tyre_compounds,
                avoid_compound=starting_tyre,
                force_different=True,
            )
        elif i == 1 and num_stops == 1:
            # 只有一次进站：倾向于偏软胎，且必须与发车胎不同
            weights = get_track_tyre_weights(track_name)
            weights = {
                k: v * (2.0 if k in ["C2", "C3"] else 1.0) for k, v in weights.items()
            }
            # 排除发车胎
            weights = {k: v for k, v in weights.items() if k != starting_tyre}
            available = [c for c in available_compounds if c != starting_tyre]

            if available:
                total_weight = sum(weights.get(c, 1.0) for c in available)
                probabilities = [weights.get(c, 1.0) / total_weight for c in available]
                pit_tyre = random.choices(available, weights=probabilities)[0]
            else:
                # 如果没有其他选择，强制选择一个不同的
                pit_tyre = smart_tyre_selection(
                    track_name,
                    tyre_compounds,
                    avoid_compound=starting_tyre,
                    force_different=True,
                )
        else:
            # 其他情况：智能选择，确保F1规则合规
            remaining_laps = num_laps - (i * 20)  # 估算剩余圈数

            if force_different:
                # 强制选择不同种类
                pit_tyre = smart_tyre_selection(
                    track_name, tyre_compounds, force_different=True
                )
            elif remaining_laps < 20:  # 剩余圈数少，倾向于软胎
                weights = get_track_tyre_weights(track_name)
                weights = {
                    k: v * (1.5 if k in ["C2", "C3"] else 1.0)
                    for k, v in weights.items()
                }
                available = get_available_compounds_for_track(track_name)
                total_weight = sum(weights.get(c, 1.0) for c in available)
                probabilities = [weights.get(c, 1.0) / total_weight for c in available]
                pit_tyre = random.choices(available, weights=probabilities)[0]
            else:
                pit_tyre = smart_tyre_selection(track_name, tyre_compounds)

        tyre_compounds.append(pit_tyre)
        used_compounds.add(pit_tyre)

    # 最终检查：如果只有一种轮胎，强制修改一个为不同种类
    final_compounds_set = set(tyre_compounds)
    if len(final_compounds_set) == 1 and len(available_compounds) >= 2:
        # 随机选择一个非发车胎的位置进行替换
        other_compounds = [c for c in available_compounds if c != tyre_compounds[0]]
        if other_compounds:
            replacement = random.choice(other_compounds)
            # 随机替换一个非发车胎的位置
            if len(tyre_compounds) > 1:
                replace_index = random.randint(1, len(tyre_compounds) - 1)
                tyre_compounds[replace_index] = replacement

    return tyre_compounds


def generate_individual_tyre_sequence(tyre_compounds_set):
    """
    为车手生成个性化的轮胎序列顺序
    保持轮胎配方集合相同，但顺序可以不同
    确保最终序列包含至少两种不同种类的轮胎
    """
    # 随机打乱轮胎顺序（除了发车胎保持原位）
    if len(tyre_compounds_set) <= 1:
        # 如果只有一种轮胎，需要扩展以符合F1规则
        extended_compounds = tyre_compounds_set.copy()
        all_compounds = ["C1", "C2", "C3", "C4", "C5"]
        current_compound = tyre_compounds_set[0]
        available_alternatives = [c for c in all_compounds if c != current_compound]

        if available_alternatives:
            # 添加一种不同的轮胎
            extended_compounds.append(random.choice(available_alternatives))
        tyre_compounds_set = extended_compounds

    # 创建完整列表的副本以避免修改原数据
    tyre_compounds_copy = tyre_compounds_set.copy()

    # 随机选择一个轮胎作为发车胎（保持车队集合中的元素）
    starting_tyre = random.choice(tyre_compounds_copy)

    # 从集合中移除发车胎
    tyre_compounds_copy.remove(starting_tyre)

    # 随机打乱剩余的进站轮胎顺序
    random.shuffle(tyre_compounds_copy)

    # 重新组合：发车胎 + 打乱的进站轮胎
    tyre_sequence = [starting_tyre] + tyre_compounds_copy

    # 使用合规检查函数确保F1规则
    tyre_sequence = ensure_f1_tyre_compliance(tyre_sequence)

    return tyre_sequence


def assign_team_strategies(driver_data, track_name, num_laps, pit_data):
    """
    为所有车手分配车队策略
    同一车队的车手使用相同的策略
    """
    team_strategies = {}
    driver_teams = {}

    # 首先收集所有车手的车队信息
    for driver_name, driver_info in driver_data.items():
        team_name = driver_info.get("Team", "Unknown")
        driver_teams[driver_name] = team_name

    # 为每个车队生成独立的策略
    unique_teams = set(driver_teams.values())
    for team_name in unique_teams:
        if team_name != "Unknown":
            team_strategies[team_name] = get_team_strategy(
                track_name, team_name, num_laps, pit_data
            )
        else:
            # 对于未知车队，生成随机策略
            strategy = determine_pit_strategy(track_name, pit_data)
            pit_laps = generate_pit_laps(track_name, strategy, pit_data)
            tyre_sequence = [roll_tyre_for_track(track_name)]
            for i in range(len(pit_laps)):
                tyre_sequence.append(roll_tyre_for_track(track_name))
            team_strategies[team_name] = {
                "strategy": strategy,
                "tyre_compounds_set": tyre_sequence,
            }

    return team_strategies, driver_teams


# Non-linear scaling function
def nonlinear_scaling(r_value, base_lap, r_max):
    """Non-linear scaling function"""
    return base_lap * (
        1 + 0.65 * (1 - r_value / r_max) * np.exp(-2.5 * (1 - r_value / r_max))
    )


# Track characteristics data
def get_track_characteristics():
    """Define track characteristics data"""
    return {
        "bahrain": {
            "abrasion": 5,
            "stress": 3,
            "evolution": 4,
            "pressure": {"C1": 22.5, "C2": 22.0, "C3": 21.5, "C4": 21.0, "C5": 20.5},
        },
        "spain": {
            "abrasion": 4,
            "stress": 4,
            "evolution": 3,
            "pressure": {"C1": 23.0, "C2": 22.5, "C3": 22.0, "C4": 21.5, "C5": 21.0},
        },
        "monaco": {
            "abrasion": 1,
            "stress": 1,
            "evolution": 5,
            "pressure": {"C1": 20.0, "C2": 19.5, "C3": 19.0, "C4": 18.5, "C5": 18.0},
        },
        "canada": {
            "abrasion": 2,
            "stress": 3,
            "evolution": 5,
            "pressure": {"C1": 22.0, "C2": 21.5, "C3": 21.0, "C4": 20.5, "C5": 20.0},
        },
        "azerbaijan": {
            "abrasion": 1,
            "stress": 3,
            "evolution": 5,
            "pressure": {"C1": 21.0, "C2": 20.5, "C3": 20.0, "C4": 19.5, "C5": 19.0},
        },
        "austria": {
            "abrasion": 3,
            "stress": 5,
            "evolution": 3,
            "pressure": {"C1": 23.5, "C2": 23.0, "C3": 22.5, "C4": 22.0, "C5": 21.5},
        },
        "britain": {
            "abrasion": 3,
            "stress": 5,
            "evolution": 3,
            "pressure": {"C1": 23.5, "C2": 23.0, "C3": 22.5, "C4": 22.0, "C5": 21.5},
        },
        "hungary": {
            "abrasion": 2,
            "stress": 3,
            "evolution": 4,
            "pressure": {"C1": 22.0, "C2": 21.5, "C3": 21.0, "C4": 20.5, "C5": 20.0},
        },
        "belgium": {
            "abrasion": 4,
            "stress": 5,
            "evolution": 3,
            "pressure": {"C1": 23.0, "C2": 22.5, "C3": 22.0, "C4": 21.5, "C5": 21.0},
        },
        "netherlands": {
            "abrasion": 3,
            "stress": 5,
            "evolution": 3,
            "pressure": {"C1": 23.5, "C2": 23.0, "C3": 22.5, "C4": 22.0, "C5": 21.5},
        },
        "italy": {
            "abrasion": 3,
            "stress": 3,
            "evolution": 3,
            "pressure": {"C1": 24.5, "C2": 24.0, "C3": 23.5, "C4": 23.0, "C5": 22.5},
        },
        "singapore": {
            "abrasion": 3,
            "stress": 2,
            "evolution": 4,
            "pressure": {"C1": 22.5, "C2": 22.0, "C3": 21.5, "C4": 21.0, "C5": 20.5},
        },
        "japan": {
            "abrasion": 4,
            "stress": 5,
            "evolution": 3,
            "pressure": {"C1": 24.0, "C2": 23.5, "C3": 23.0, "C4": 22.5, "C5": 22.0},
        },
        "usa": {
            "abrasion": 4,
            "stress": 4,
            "evolution": 4,
            "pressure": {"C1": 23.5, "C2": 23.0, "C3": 22.5, "C4": 22.0, "C5": 21.5},
        },
        "mexico": {
            "abrasion": 2,
            "stress": 2,
            "evolution": 4,
            "pressure": {"C1": 21.0, "C2": 20.5, "C3": 20.0, "C4": 19.5, "C5": 19.0},
        },
        "brazil": {
            "abrasion": 3,
            "stress": 4,
            "evolution": 4,
            "pressure": {"C1": 22.5, "C2": 22.0, "C3": 21.5, "C4": 21.0, "C5": 20.5},
        },
        "abudhabi": {
            "abrasion": 3,
            "stress": 3,
            "evolution": 4,
            "pressure": {"C1": 22.5, "C2": 22.0, "C3": 21.5, "C4": 21.0, "C5": 20.5},
        },
    }


# =============================================================================
# TRACK BASE LAP TIME CONFIGURATION
# Based on FastF1 real data (2022-2025 seasons) - RACE PACE (not pole time)
# These are realistic race lap times including degradation
# Updated after multi-track calibration comparison with real FastF1 data
# =============================================================================

TRACK_BASE_LAP_TIMES = {
    # Track: (Race pace base lap time, R-value reference)
    # Formula: base_lap = TRACK_BASE - (R_Value - 300) * 0.03
    # 2024-2025 FastF1 calibrated values (multi-year average where available)
    # High-speed tracks
    "Italy": (86.5, 300),  # Monza - FastF1: ~86.5s
    "Bahrain": (97.8, 300),  # FastF1 multi-year: 97.776s
    "Saudi Arabia": (96.2, 300),  # FastF1 multi-year: 94.767s
    "Belgium": (102.3, 300),  # Spa - FastF1: 102.0s (was 112.7)
    "Austria": (70.7, 300),  # Red Bull Ring - FastF1: ~70.7s
    # Street circuits
    "Monaco": (79.6, 300),  # Monte Carlo - FastF1: 79.6s (2023: 79.8s, 2024: 79.5s)
    "Singapore": (110.1, 300),  # Marina Bay - FastF1: ~109.8s multi-year avg
    "Azerbaijan": (
        108.3,
        300,
    ),  # Baku Street - FastF1: 108.2s (2023: 107.3s, 2024: 109.0s)
    "Miami": (93.0, 300),  # Hard Rock Stadium - FastF1: ~93.0s
    "Las Vegas": (98.7, 300),  # Street Circuit - FastF1 multi-year: 98.7s
    # Technical tracks
    "Spain": (89.0, 300),  # Circuit de Barcelona - FastF1: 88.9s (reference track)
    "Hungary": (79.6, 300),  # Hungaroring - FastF1: 79.3s (was 84.4)
    "France": (91.5, 300),  # Paul Ricard - FastF1: 91.2s (was 98.8)
    # Medium-length tracks
    "Silverstone": (93.3, 300),  # British GP - FastF1: ~93.3s
    "Netherlands": (76.6, 300),  # Zandvoort - FastF1: ~76.6s
    "Brazil": (73.3, 300),  # Interlagos - FastF1: 73.0s (was 76.4)
    "Canada": (80.8, 300),  # Gilles Villeneuve - FastF1: 80.5s (was 83.5)
    "Japan": (97.5, 300),  # Suzuka - FastF1: 97.41s (2024 race pace)
    "Abu Dhabi": (90.3, 300),  # Yas Marina - FastF1: 90.0s (was 93.0)
    # Updated entries with FastF1 calibration
    "Qatar": (88.4, 300),  # Lusail - FastF1: 88.447s
    "Mexico": (84.2, 300),  # Rodriguez - FastF1: 83.9s (was 79.3)
    "China": (
        99.8,
        300,
    ),  # Shanghai - FastF1 multi-year: 99.8s (2024: 101.9s, 2025: 97.7s)
    # Track name aliases for flexibility
    "Great Britain": (93.3, 300),  # Silverstone
    "Great_Britain": (93.3, 300),
    "United States": (95.0, 300),  # COTA - FastF1: ~95.0s
    "USA": (95.0, 300),
    "Abu_Dhabi": (93.0, 300),
    "Saudi_Arabia": (96.2, 300),
    "SaudiArabia": (96.2, 300),
    "default": (88.0, 300),  # Fallback for unknown tracks
}


def get_track_base_lap(track_name: str) -> float:
    """
    Get the base lap time for a track.

    Args:
        track_name: Name of the track (case-insensitive, with alias support)

    Returns:
        Base lap time in seconds
    """
    # Track name normalization and alias mapping
    track_aliases = {
        # Common name -> canonical name in TRACK_BASE_LAP_TIMES
        "monza": "Italy",
        "italy": "Italy",
        "lasvegas": "Las Vegas",
        "las_vegas": "Las Vegas",
        "lv": "Las Vegas",
        "shanghai": "China",
        "china": "China",
        "bahrain": "Bahrain",
        "saudiarabia": "Saudi Arabia",
        "saudi_arabia": "Saudi Arabia",
        "silverstone": "Great Britain",
        "gb": "Great Britain",
        "unitedstates": "USA",
        "cota": "USA",
        "texas": "USA",
        "austin": "USA",
        "catalunya": "Spain",
        "barcelona": "Spain",
        "spain": "Spain",
        "monaco": "Monaco",
        "montecarlo": "Monaco",
        "japan": "Japan",
        "suzuka": "Japan",
        "singapore": "Singapore",
        "marinabay": "Singapore",
        "azerbaijan": "Azerbaijan",
        "baku": "Azerbaijan",
        "hungary": "Hungary",
        "hungaroring": "Hungary",
        "netherlands": "Netherlands",
        "zandvoort": "Netherlands",
        "belgium": "Belgium",
        "spa": "Belgium",
        "france": "France",
        "paulricard": "France",
        "canada": "Canada",
        "montreal": "Canada",
        "brazil": "Brazil",
        "interlagos": "Brazil",
        "saopaulo": "Brazil",
        "abudhabi": "Abu Dhabi",
        "yasmarina": "Abu Dhabi",
        "qatar": "Qatar",
        "lusail": "Qatar",
        "mexico": "Mexico",
        "mexicocity": "Mexico",
        "austria": "Austria",
        "redbullring": "Austria",
    }

    # Normalize track name
    normalized_name = track_name.lower().replace(" ", "").replace("_", "")

    # Check if this is an alias
    if normalized_name in track_aliases:
        canonical_name = track_aliases[normalized_name]
        if canonical_name in TRACK_BASE_LAP_TIMES:
            return TRACK_BASE_LAP_TIMES[canonical_name][0]

    # Try exact match first
    track_key = normalized_name
    if track_key in TRACK_BASE_LAP_TIMES:
        return TRACK_BASE_LAP_TIMES[track_key][0]

    # Try partial matches
    for track, (base_lap, _) in TRACK_BASE_LAP_TIMES.items():
        track_lower = track.lower().replace(" ", "").replace("_", "")
        if track_lower in normalized_name or normalized_name in track_lower:
            return base_lap

    return TRACK_BASE_LAP_TIMES["default"][0]


def calculate_base_lap_time(driver_r_value: float, track_name: str) -> float:
    """
    Calculate base lap time for a driver on a specific track.

    Formula:
        base_lap = TRACK_BASE - (R_Value - 300) * 0.03

    Where:
        - TRACK_BASE is the track-specific base lap time
        - R_Value is the driver's R-value
        - 0.03s per R-value point (reduced from 0.05 for better calibration)

    Args:
        driver_r_value: Driver's R-value
        track_name: Name of the track

    Returns:
        Base lap time in seconds
    """
    track_base = get_track_base_lap(track_name)

    # Calculate time difference based on R-value
    # Higher R-value = faster lap
    r_adjustment = (driver_r_value - 300) * 0.03

    return track_base - r_adjustment


# 发车直道长度数据 (米) - 基于F1官方赛道布局和技术文档
def get_start_straight_data():
    """获取各赛道的发车直道长度和特性数据"""
    return {
        # 长直道赛道 (>1000m) - 高速发车，超车机会多
        "bahrain": {
            "straight_length": 1070,
            "complexity": "medium",
            "category": "long",
        },
        "canada": {"straight_length": 1100, "complexity": "medium", "category": "long"},
        "italy": {"straight_length": 1120, "complexity": "low", "category": "long"},
        "usa": {"straight_length": 1060, "complexity": "medium", "category": "long"},
        "mexico": {"straight_length": 1045, "complexity": "low", "category": "long"},
        # 中等直道赛道 (600-1000m) - 平衡型发车
        "spain": {"straight_length": 830, "complexity": "medium", "category": "medium"},
        "australia": {
            "straight_length": 720,
            "complexity": "high",
            "category": "medium",
        },
        "austria": {"straight_length": 790, "complexity": "low", "category": "medium"},
        "britain": {"straight_length": 870, "complexity": "high", "category": "medium"},
        "hungary": {
            "straight_length": 630,
            "complexity": "medium",
            "category": "medium",
        },
        "belgium": {"straight_length": 940, "complexity": "high", "category": "medium"},
        "netherlands": {
            "straight_length": 800,
            "complexity": "medium",
            "category": "medium",
        },
        "japan": {"straight_length": 750, "complexity": "high", "category": "medium"},
        "singapore": {
            "straight_length": 850,
            "complexity": "high",
            "category": "medium",
        },
        "abudhabi": {"straight_length": 920, "complexity": "low", "category": "medium"},
        # 短直道赛道 (<600m) - 技术型发车，位置优势重要
        "monaco": {
            "straight_length": 450,
            "complexity": "very_high",
            "category": "short",
        },
        "azerbaijan": {
            "straight_length": 590,
            "complexity": "very_high",
            "category": "short",
        },
        "brazil": {"straight_length": 550, "complexity": "high", "category": "short"},
        "china": {"straight_length": 580, "complexity": "medium", "category": "short"},
        "saudiarabia": {
            "straight_length": 560,
            "complexity": "medium",
            "category": "short",
        },
        "miami": {"straight_length": 520, "complexity": "medium", "category": "short"},
        "qatar": {"straight_length": 580, "complexity": "low", "category": "short"},
        "lasvegas": {"straight_length": 550, "complexity": "low", "category": "short"},
    }


# 车手起步特性数据库 - 基于历史统计数据
def get_driver_start_characteristics():
    """获取车手的起步特性数据"""
    return {
        # 顶级起步车手 - 反应快，加速度好
        "Hamilton": {
            "reaction_avg": 0.185,
            "reaction_std": 0.015,
            "acceleration_factor": 1.05,
            "consistency": 0.95,
        },
        "Verstappen": {
            "reaction_avg": 0.188,
            "reaction_std": 0.012,
            "acceleration_factor": 1.06,
            "consistency": 0.97,
        },
        "Leclerc": {
            "reaction_avg": 0.190,
            "reaction_std": 0.018,
            "acceleration_factor": 1.04,
            "consistency": 0.92,
        },
        "Sainz": {
            "reaction_avg": 0.192,
            "reaction_std": 0.016,
            "acceleration_factor": 1.03,
            "consistency": 0.94,
        },
        # 优秀起步车手
        "Russell": {
            "reaction_avg": 0.194,
            "reaction_std": 0.020,
            "acceleration_factor": 1.02,
            "consistency": 0.91,
        },
        "Norris": {
            "reaction_avg": 0.193,
            "reaction_std": 0.017,
            "acceleration_factor": 1.02,
            "consistency": 0.93,
        },
        "Alonso": {
            "reaction_avg": 0.196,
            "reaction_std": 0.019,
            "acceleration_factor": 1.01,
            "consistency": 0.96,
        },  # 经验丰富
        "Ricciardo": {
            "reaction_avg": 0.191,
            "reaction_std": 0.022,
            "acceleration_factor": 1.03,
            "consistency": 0.88,
        },  # 爆发起步
        # 平均起步车手
        "Bottas": {
            "reaction_avg": 0.198,
            "reaction_std": 0.021,
            "acceleration_factor": 1.00,
            "consistency": 0.90,
        },
        "Pérez": {
            "reaction_avg": 0.197,
            "reaction_std": 0.023,
            "acceleration_factor": 1.00,
            "consistency": 0.89,
        },
        "Ocon": {
            "reaction_avg": 0.199,
            "reaction_std": 0.020,
            "acceleration_factor": 0.99,
            "consistency": 0.91,
        },
        "Gasly": {
            "reaction_avg": 0.200,
            "reaction_std": 0.022,
            "acceleration_factor": 0.99,
            "consistency": 0.88,
        },
        # 需要改进起步的车手
        "Tsunoda": {
            "reaction_avg": 0.205,
            "reaction_std": 0.025,
            "acceleration_factor": 0.98,
            "consistency": 0.85,
        },
        "Magnussen": {
            "reaction_avg": 0.203,
            "reaction_std": 0.024,
            "acceleration_factor": 0.98,
            "consistency": 0.86,
        },
        "Albon": {
            "reaction_avg": 0.202,
            "reaction_std": 0.023,
            "acceleration_factor": 0.99,
            "consistency": 0.87,
        },
        "Stroll": {
            "reaction_avg": 0.206,
            "reaction_std": 0.026,
            "acceleration_factor": 0.97,
            "consistency": 0.84,
        },
        # 新人/数据不足 - 使用平均值
        "default": {
            "reaction_avg": 0.200,
            "reaction_std": 0.020,
            "acceleration_factor": 1.00,
            "consistency": 0.90,
        },
    }


def calculate_grid_gap_penalty(grid_position):
    """
    计算发车格位置差距的时间惩罚

    基于F1发车格设计：
    - 每个发车位间隔8米
    - 斜向排列，前后排距离约16米
    - 起步角度和视野影响

    参数:
    - grid_position: 发车位次 (1=Pole Position)

    返回:
    - gap_penalty: 位置差距的时间惩罚 (秒)
    """
    # 基础距离惩罚
    if grid_position == 1:
        base_penalty = 0.0  # Pole位置最佳
    elif grid_position == 2:
        base_penalty = 0.05  # 第2位稍差
    elif grid_position <= 4:  # 第1排
        base_penalty = 0.10
    elif grid_position <= 6:  # 第2排
        base_penalty = 0.18
    elif grid_position <= 8:  # 第3排
        base_penalty = 0.28
    elif grid_position <= 10:  # 第4排
        base_penalty = 0.40
    elif grid_position <= 15:  # 第5-8排
        base_penalty = 0.55 + (grid_position - 11) * 0.08
    else:  # 第9排及以后
        base_penalty = 0.85 + (grid_position - 16) * 0.10

    # 视野和空气动力学影响
    # 前车尾流对后车起步的影响（负面，因为湍流）
    aero_penalty = 0.0
    if grid_position > 1:
        # 前车数量越多，受尾流影响越大
        front_cars = grid_position - 1
        aero_penalty = min(0.15, front_cars * 0.01)

    total_penalty = base_penalty + aero_penalty
    return total_penalty


def calculate_reaction_time_acceleration(driver_name, driver_r_value, track_chars=None):
    """
    计算车手的反应时间和起步加速度对时间的影响

    参数:
    - driver_name: 车手姓名
    - driver_r_value: 车手R值
    - track_chars: 赛道特性（可选）

    返回:
    - reaction_impact: 反应时间和加速度的时间影响 (秒)
    - details: 详细分解
    """
    driver_chars = get_driver_start_characteristics()

    # 获取车手特性，如果没有则使用默认值
    name_key = None
    for key in driver_chars.keys():
        if key.lower() in driver_name.lower():
            name_key = key
            break

    if name_key is None:
        name_key = "default"

    char_data = driver_chars[name_key]

    # 1. 反应时间影响
    # F1标准反应时间约0.200秒，优秀车手可达0.185秒
    reaction_time = np.random.normal(
        char_data["reaction_avg"], char_data["reaction_std"] / char_data["consistency"]
    )

    # 反应时间与基准的差值
    baseline_reaction = 0.200  # F1平均水平
    reaction_impact = reaction_time - baseline_reaction

    # 2. 起步加速度影响
    # 基于车手的加速度特性
    acceleration_bonus = (
        char_data["acceleration_factor"] - 1.0
    ) * 0.3  # 最大±0.15秒影响

    # R值对加速度的微调
    r_adjustment = (driver_r_value - 300) * 0.002  # R值每高1点，快0.002秒

    total_acceleration_impact = acceleration_bonus + r_adjustment

    # 3. 赛道条件影响
    track_adjustment = 0.0
    if track_chars:
        # 低抓地力赛道对起步的要求更高
        if track_chars.get("abrasion", 3) <= 2:
            track_adjustment = 0.02  # 低磨损赛道通常抓地力较低

        # 高应力赛道对起步技巧要求更高
        if track_chars.get("stress", 3) >= 4:
            track_adjustment += 0.01

    # 4. 总影响
    total_impact = reaction_impact + total_acceleration_impact + track_adjustment

    details = {
        "reaction_time": reaction_time,
        "reaction_impact": reaction_impact,
        "acceleration_bonus": acceleration_bonus,
        "r_adjustment": r_adjustment,
        "total_acceleration_impact": total_acceleration_impact,
        "track_adjustment": track_adjustment,
        "total_impact": total_impact,
        "driver_characteristics": char_data,
    }

    return total_impact, details


def calculate_start_lap_delta(
    grid_position,
    driver_name,
    driver_r_value,
    track_name,
    track_chars=None,
    is_red_flag_restart=False,
):
    """
    计算发车圈时间附加 - 完整版本，包含位置差距和起步加速度

    参数:
    - grid_position: 发车位次 (1=Pole Position)
    - driver_name: 车手姓名
    - driver_r_value: 车手R值
    - track_name: 赛道名称
    - track_chars: 赛道特性 (可选)
    - is_red_flag_restart: 是否为红旗重启 (False为正常发车)

    返回:
    - delta_time: 时间附加 (秒)
    - breakdown: 时间附加分解说明
    """
    straight_data = get_start_straight_data()
    track_key = track_name.lower().replace(" ", "")

    # 处理特殊映射
    mappings = {
        "saudiarabia": "saudi_arabia",
        "unitedstates": "usa",
        "greatbritain": "britain",
        "abudhabi": "abudhabi",
    }
    track_key = mappings.get(track_key, track_key)

    if track_key not in straight_data:
        return 0.0, {
            "error": f"Track {track_name} not found",
            "special_events": [],
            "grid_penalty": 0.0,
            "reaction_acceleration": 0.0,
            "track_info": {
                "straight_length": 0,
                "complexity": "unknown",
                "category": "unknown",
            },
        }

    track_info = straight_data[track_key]
    straight_length = track_info["straight_length"]
    complexity = track_info["complexity"]

    # 1. 基础时间 (基于直道长度)
    if straight_length >= 1000:
        base_delta = 0.8  # 长直道
    elif straight_length >= 600:
        base_delta = 1.2  # 中等直道
    else:
        base_delta = 2.0  # 短直道

    # 2. 复杂度影响
    complexity_factors = {
        "very_high": 1.5,  # 摩纳哥, 巴库
        "high": 1.2,  # 银石, 新加坡
        "medium": 1.0,  # 中等
        "low": 0.8,  # 蒙扎, 墨西哥城
    }
    base_delta *= complexity_factors.get(complexity, 1.0)

    # 3. 发车格位置差距惩罚
    grid_penalty = calculate_grid_gap_penalty(grid_position)

    # 4. 反应时间和起步加速度
    reaction_accel_impact, reaction_details = calculate_reaction_time_acceleration(
        driver_name, driver_r_value, track_chars
    )

    # 5. 车手技能影响 (基于R值) - 除了反应时间之外的额外技能
    skill_adjustment = -(driver_r_value - 300) * 0.003  # 高R值获得优势

    # 6. 红旗重启调整
    restart_factor = 0.6 if is_red_flag_restart else 1.0

    # 7. 随机因素和特殊事件
    random_factor = np.random.normal(0, 0.08)  # 减小随机性，因为已经有更详细的建模
    event_delta = 0.0
    special_events = []

    # 坏起步概率 - 基于车手特性
    driver_chars = get_driver_start_characteristics()
    name_key = None
    for key in driver_chars.keys():
        if key.lower() in driver_name.lower():
            name_key = key
            break
    if name_key is None:
        name_key = "default"

    char_data = driver_chars[name_key]
    bad_start_prob = max(0.005, 0.03 - char_data["consistency"] * 0.02)
    if random.random() < bad_start_prob:
        event_delta += np.random.uniform(0.4, 1.0)
        special_events.append("Bad Start")

    # 完美起步概率
    perfect_start_prob = min(0.015, 0.005 + char_data["consistency"] * 0.01)
    if random.random() < perfect_start_prob:
        event_delta -= np.random.uniform(0.15, 0.4)
        special_events.append("Perfect Start")

    # 8. 发车碰撞风险 - 基于位置和赛道复杂度
    collision_risk = 0.0
    if complexity in ["high", "very_high"] and grid_position <= 6:
        collision_risk_prob = 0.02 * (6 - grid_position + 1) / 6  # 前排风险更高
        if random.random() < collision_risk_prob:
            collision_risk += np.random.uniform(0.2, 0.5)
            special_events.append("Minor Collision")

    # 总时间附加
    total_delta = (
        base_delta
        + grid_penalty
        + reaction_accel_impact
        + skill_adjustment
        + random_factor
        + event_delta
        + collision_risk
    ) * restart_factor

    total_delta = max(0.0, min(total_delta, 3.5))  # 限制在0-3.5秒之间

    breakdown = {
        "base_delta": base_delta,
        "grid_penalty": grid_penalty,
        "reaction_acceleration": reaction_accel_impact,
        "reaction_details": reaction_details,
        "skill_adjustment": skill_adjustment,
        "random_factor": random_factor,
        "event_delta": event_delta,
        "collision_risk": collision_risk,
        "restart_factor": restart_factor,
        "special_events": special_events,
        "track_info": track_info,
    }

    return total_delta, breakdown


def analyze_start_characteristics():
    """分析所有车手的起步特性"""
    driver_chars = get_driver_start_characteristics()

    print(f"\n{'=' * 80}")
    print(f"F1 车手起步特性分析")
    print(f"{'=' * 80}")
    print(
        f"{'车手':<15} {'平均反应':<10} {'反应稳定':<10} {'加速系数':<10} {'起步一致性':<10}"
    )
    print(f"{'-' * 80}")

    for name, data in driver_chars.items():
        if name != "default":
            print(
                f"{name:<15} {data['reaction_avg']:<10.3f} {data['reaction_std']:<10.3f} "
                f"{data['acceleration_factor']:<10.3f} {data['consistency']:<10.3f}"
            )


def simulate_start_lap_for_all_drivers(drivers_info, track_name, track_chars=None):
    """
    为所有车手模拟发车圈

    参数:
    - drivers_info: 车手信息字典 {车手名: {grid_position, R_Value, ...}}
    - track_name: 赛道名称
    - track_chars: 赛道特性

    返回:
    - start_results: {车手名: {delta_time, breakdown, grid_position}}
    """

    start_results = {}

    # 按发车位次排序
    sorted_drivers = sorted(
        drivers_info.items(), key=lambda x: x[1].get("grid_position", 999)
    )

    for driver_name, driver_info in sorted_drivers:
        grid_position = driver_info.get("grid_position", 1)
        r_value = driver_info.get("R_Value", 300)

        delta_time, breakdown = calculate_start_lap_delta(
            grid_position, driver_name, r_value, track_name, track_chars
        )

        start_results[driver_name] = {
            "delta_time": delta_time,
            "breakdown": breakdown,
            "grid_position": grid_position,
            "r_value": r_value,
        }

    return start_results


def print_start_lap_analysis(start_results, track_name, top_n=10):
    """打印发车圈分析报告"""

    straight_data = get_start_straight_data()
    track_key = track_name.lower().replace(" ", "")

    # 处理特殊映射
    mappings = {
        "saudiarabia": "saudi_arabia",
        "unitedstates": "usa",
        "greatbritain": "britain",
        "abudhabi": "abudhabi",
    }
    track_key = mappings.get(track_key, track_key)

    print(f"\n{'=' * 80}")
    print(f"F1 发车模拟详细分析 - {track_name.upper()}")
    print(f"{'=' * 80}")

    if track_key in straight_data:
        track_info = straight_data[track_key]
        print(f"🏁 赛道特性:")
        print(
            f"   发车直道长度: {track_info['straight_length']}m ({track_info['category']})"
        )
        print(f"   复杂度等级: {track_info['complexity']}")
        print(
            f"   预期发车难度: {'高' if track_info['complexity'] in ['high', 'very_high'] else '中' if track_info['complexity'] == 'medium' else '低'}"
        )

    print(f"\n📊 发车时间附加排名 (前{min(top_n, len(start_results))}名):")
    print(
        f"{'排名':<4} {'车手':<20} {'发车位':<6} {'R值':<8} {'时间附加':<10} {'主要影响'}"
    )
    print(f"{'-' * 80}")

    # 按时间附加排序
    sorted_results = sorted(start_results.items(), key=lambda x: x[1]["delta_time"])

    for i, (driver_name, result) in enumerate(sorted_results[:top_n]):
        delta = result["delta_time"]
        grid_pos = result["grid_position"]
        r_value = result["r_value"]
        breakdown = result["breakdown"]

        # 检查breakdown是否为None
        if breakdown is None:
            special_events = []
            main_factors = ["正常起步"]
        else:
            special_events = breakdown.get("special_events", [])

            # 分析主要影响因素
            main_factors = []
            if breakdown.get("grid_penalty", 0) > 0.1:
                main_factors.append(f"位置惩罚{breakdown.get('grid_penalty', 0):.2f}s")
            if abs(breakdown.get("reaction_acceleration", 0)) > 0.05:
                reaction = breakdown.get("reaction_acceleration", 0)
                sign = "+" if reaction > 0 else ""
                main_factors.append(f"反应{sign}{reaction:.2f}s")
            if special_events:
                main_factors.append(",".join(special_events))

            if not main_factors:
                main_factors = ["正常起步"]

        main_factor_str = ", ".join(main_factors) if main_factors else "正常起步"

        print(
            f"{i + 1:<4} {driver_name:<20} {grid_pos:<6} {r_value:<8.1f} {delta:<10.3f} {main_factor_str}"
        )

    # 统计信息
    all_deltas = [result["delta_time"] for result in start_results.values()]
    avg_delta = np.mean(all_deltas)
    std_delta = np.std(all_deltas)

    print(f"\n📈 发车统计:")
    print(f"   平均时间附加: {avg_delta:.3f}s")
    print(f"   标准差: {std_delta:.3f}s")
    print(f"   最小时间附加: {min(all_deltas):.3f}s")
    print(f"   最大时间附加: {max(all_deltas):.3f}s")

    # 特殊事件统计
    all_events = []
    for result in start_results.values():
        breakdown = result["breakdown"]
        if breakdown is not None:
            all_events.extend(breakdown.get("special_events", []))

    if all_events:
        event_counts = {}
        for event in all_events:
            event_counts[event] = event_counts.get(event, 0) + 1

        print(f"\n⚠️  特殊事件统计:")
        for event, count in event_counts.items():
            print(f"   {event}: {count}次")


def calculate_wear_compensation(abrasion_level):
    """Calculate compensation factor based on track wear level"""
    normalized_abrasion = (abrasion_level - 3) / 2.0
    wear_factor = 1 + 0.2 * normalized_abrasion
    return wear_factor


def calculate_pressure_compensation(actual_pressure, target_pressure):
    """Calculate compensation factor based on tire pressure deviation"""
    pressure_diff = actual_pressure - target_pressure
    pressure_factor = 1 + 0.05 * pressure_diff
    return pressure_factor


def get_universal_tyre_params_with_cliff():
    """Get tire parameters based on Pirelli technical documentation"""
    return {
        "C1": {
            "base_lap": 30,
            "base_degradation": 0.025,
            "cliff_lap": 28,
            "cliff_severity": 0.15,
        },
        "C2": {
            "base_lap": 25,
            "base_degradation": 0.030,
            "cliff_lap": 23,
            "cliff_severity": 0.12,
        },
        "C3": {
            "base_lap": 20,
            "base_degradation": 0.035,
            "cliff_lap": 18,
            "cliff_severity": 0.10,
        },
        "C4": {
            "base_lap": 15,
            "base_degradation": 0.045,
            "cliff_lap": 13,
            "cliff_severity": 0.08,
        },
        "C5": {
            "base_lap": 12,
            "base_degradation": 0.060,
            "cliff_lap": 10,
            "cliff_severity": 0.06,
        },
    }


def calculate_degradation_with_cliff(
    lap_number, tyre_compound, r_value, r_max, track_chars, pit_lap_count
):
    """Calculate tire degradation with cliff effect"""
    tyre_params = get_universal_tyre_params_with_cliff()
    compound_params = tyre_params[tyre_compound]

    # Non-linear scaling
    scaled_lap = nonlinear_scaling(r_value, compound_params["base_lap"], r_max)

    # Track characteristics compensation
    wear_factor = calculate_wear_compensation(track_chars["abrasion"])

    # Base degradation rate
    base_degradation = compound_params["base_degradation"] * wear_factor

    # Cliff effect
    cliff_lap = compound_params["cliff_lap"]
    cliff_severity = compound_params["cliff_severity"]

    if lap_number > cliff_lap:
        cliff_factor = 1 + cliff_severity * ((lap_number - cliff_lap) / cliff_lap)
    else:
        cliff_factor = 1.0

    # Calculate cumulative degradation
    degradation = base_degradation * (lap_number / scaled_lap) * cliff_factor

    return degradation


def read_driver_data(csv_file):
    """Read driver data from CSV file"""
    try:
        candidate_paths = []

        if os.path.isabs(csv_file):
            candidate_paths.append(csv_file)
        else:
            candidate_paths.append(csv_file)
            candidate_paths.append(os.path.join("tables", csv_file))

        csv_path = next(
            (path for path in candidate_paths if os.path.exists(path)), None
        )
        if csv_path is None:
            raise FileNotFoundError(f"CSV file not found: {csv_file}")

        df = pd.read_csv(csv_path, encoding="utf-8")
        driver_data = {}

        for index, row in df.iterrows():
            driver_name = row["Driver"]
            team_name = row["Team"]
            dr_value = row["DR"]
            ro_value = row["RO"]  # RO value used as R value

            if pd.notna(driver_name) and pd.notna(dr_value) and pd.notna(ro_value):
                driver_data[driver_name] = {
                    "Team": team_name,
                    "R_Value": float(ro_value),
                    "DR_Value": float(dr_value),
                }

        return driver_data

    except Exception as e:
        print(f"Error reading CSV file: {e}")
        return {}


def calculate_dr_based_std(dr_value, dr_min, dr_max, base_std):
    """Calculate standard deviation based on DR value"""
    if dr_max != dr_min:
        dr_normalized = (dr_value - dr_min) / (dr_max - dr_min)
    else:
        dr_normalized = 0

    std = base_std * (0.1 + 0.9 * (1 - dr_normalized) ** 2)
    return std


def load_pit_stop_data():
    """Load pit stop data"""
    try:
        df = pd.read_csv("data/pit_stop_strategies_2022_2024.csv")
        return df
    except FileNotFoundError:
        print("Pit stop data file not found: data/pit_stop_strategies_2022_2024.csv")
        return None


def load_pitlane_time_data():
    """Load pitlane time data from pitlane_time.csv"""
    try:
        df = pd.read_csv("data/pitlane_time.csv")
        return df
    except FileNotFoundError:
        print("Pitlane time data file not found: data/pitlane_time.csv")
        return None


def roll_pit_stop_time():
    """
    Simulate pit stop time using dice rolling mechanism

    First stage: D10 roll
    - 1-2 (20%): Fast tire change: 2.0-2.3 seconds
    - 3-7 (50%): Normal tire change: 2.3-3.0 seconds
    - 8-9 (20%): Slow tire change: 3.0-3.5 seconds
    - 10 (10%): Second stage D2 roll

    Second stage: D2 roll (only when D10=10)
    - 10→1 (5% total): Great success: 1.8-2.0 seconds
    - 10→2 (5% total): Great failure: Realistic problematic pit stop
      * Uses truncated normal distribution N(6.0, 2.0²)
      * Range: 3.5-15 seconds (realistic F1 problem range)
      * ~20%: Minor issues (3.5-5s)
      * ~50%: Clear problems (5-8s)
      * ~25%: Serious issues (8-12s)
      * ~5%: Disaster scenarios (12-15s)
    """
    d10 = random.randint(1, 10)

    if d10 <= 2:
        # 1-2: 2.0 - 2.3 seconds (fast change)
        return random.uniform(2.0, 2.3)
    elif d10 <= 7:
        # 3-7: 2.3 - 3.0 seconds (normal change)
        return random.uniform(2.3, 3.0)
    elif d10 <= 9:
        # 8-9: 3.0 - 3.5 seconds (slow change)
        return random.uniform(3.0, 3.5)
    else:
        # d10 = 10: Roll d2 for success/failure
        d2 = random.randint(1, 2)
        if d2 == 1:
            # Great success: 1.8 - 2.0 seconds (exceptional pit crew performance)
            return random.uniform(1.8, 2.0)
        else:
            # Great failure: Realistic problematic pit stop distribution
            # Based on actual F1 data for problematic stops (wheel nut issues, etc.)
            mean = 6.0  # Mean time for problematic stops
            std = 2.0  # Standard deviation for realistic spread

            # Use truncated normal distribution in realistic F1 range [3.5, 15]
            # This eliminates unrealistic extremes while preserving drama
            max_attempts = 100
            for _ in range(max_attempts):
                value = np.random.normal(mean, std)
                if 3.5 <= value <= 15:
                    return value

            # Fallback: if somehow no value generated in range, use boundary values
            return random.uniform(3.5, 15)


def ensure_f1_tyre_compliance(tyre_sequence, available_compounds=None):
    """
    确保轮胎序列遵守F1规则：必须使用两种或以上不同种类的轮胎
    """
    if not tyre_sequence:
        return tyre_sequence

    unique_compounds = set(tyre_sequence)

    # 如果已经合规，直接返回
    if len(unique_compounds) >= 2:
        return tyre_sequence

    # 需要添加不同种类的轮胎
    if available_compounds is None:
        available_compounds = ["C1", "C2", "C3", "C4", "C5"]

    current_compound = tyre_sequence[0]
    alternatives = [c for c in available_compounds if c != current_compound]

    if alternatives and len(tyre_sequence) > 1:
        # 随机替换一个非发车胎
        replace_index = random.randint(1, len(tyre_sequence) - 1)
        tyre_sequence[replace_index] = random.choice(alternatives)

    return tyre_sequence


def smart_tyre_selection(
    track_name, current_sequence, avoid_compound=None, force_different=False
):
    """
    智能轮胎选择，考虑F1规则合规性
    """
    available = get_available_compounds_for_track(track_name)

    # 如果必须选择不同种类的轮胎
    if force_different or len(set(current_sequence)) < 2:
        # 优先选择未使用的轮胎
        used_compounds = set(current_sequence)
        unused_compounds = [c for c in available if c not in used_compounds]

        if unused_compounds:
            # 选择一个未使用的轮胎
            return random.choice(unused_compounds)
        elif avoid_compound and len(available) > 1:
            # 选择一个与avoid_compound不同的轮胎
            alternatives = [c for c in available if c != avoid_compound]
            return (
                random.choice(alternatives)
                if alternatives
                else random.choice(available)
            )

    # 正常选择
    return roll_tyre_for_track(track_name, avoid_compound=avoid_compound)


def validate_f1_tyre_rules(tyre_sequence, driver_name="Driver"):
    """
    验证轮胎序列是否遵守F1规则
    返回验证结果和详细信息
    """
    if not tyre_sequence:
        return False, "No tires specified"

    unique_compounds = set(tyre_sequence)
    is_compliant = len(unique_compounds) >= 2

    if is_compliant:
        return (
            True,
            f"✓ Compliant: Uses {len(unique_compounds)} different tire types: {sorted(unique_compounds)}",
        )
    else:
        return (
            False,
            f"❌ Violation: Only uses {len(unique_compounds)} tire type: {unique_compounds}. F1 rules require at least 2 different compounds!",
        )


def print_tyre_rule_summary(results):
    """
    打印所有车手的轮胎规则合规性总结
    """
    print(f"\n=== F1 Tire Rule Compliance Summary ===")

    compliant_count = 0
    total_count = 0

    for driver_name, result in results.items():
        tyre_sequence = result.get("tyre_sequence", [])
        is_compliant, message = validate_f1_tyre_rules(tyre_sequence, driver_name)

        total_count += 1
        if is_compliant:
            compliant_count += 1

        print(f"{driver_name:15s}: {message}")

    compliance_rate = (compliant_count / total_count * 100) if total_count > 0 else 0
    print(
        f"\nOverall Compliance: {compliant_count}/{total_count} drivers ({compliance_rate:.1f}%)"
    )

    if compliant_count < total_count:
        print("⚠️  Some drivers are not compliant with F1 tire rules!")
    else:
        print("✅ All drivers are compliant with F1 tire rules!")


def test_pit_stop_distribution():
    """
    测试函数：验证新的停站时间分布
    运行1000次骰点，分析结果分布
    """
    print("\n=== Testing Pit Stop Time Distribution ===")

    import numpy as np

    results = []
    great_success_count = 0
    great_failure_count = 0
    distribution_ranges = {
        "1.8-2.0 (Great Success)": 0,
        "2.0-2.3 (Fast)": 0,
        "2.3-3.0 (Normal)": 0,
        "3.0-3.5 (Slow)": 0,
        "3.5-5.0 (Minor Issues)": 0,
        "5.0-8.0 (Clear Problems)": 0,
        "8.0-12.0 (Serious Issues)": 0,
        "12.0-15.0 (Disaster)": 0,
    }

    # 运行1000次测试
    for _ in range(1000):
        time = roll_pit_stop_time()
        results.append(time)

        # 统计特殊事件
        if time < 2.0:
            great_success_count += 1
        elif time > 10.0:
            great_failure_count += 1

        # 统计分布区间
        if time < 2.0:
            distribution_ranges["1.8-2.0 (Great Success)"] += 1
        elif time < 2.3:
            distribution_ranges["2.0-2.3 (Fast)"] += 1
        elif time < 3.0:
            distribution_ranges["2.3-3.0 (Normal)"] += 1
        elif time < 3.5:
            distribution_ranges["3.0-3.5 (Slow)"] += 1
        elif time < 5.0:
            distribution_ranges["3.5-5.0 (Minor Issues)"] += 1
        elif time < 8.0:
            distribution_ranges["5.0-8.0 (Clear Problems)"] += 1
        elif time < 12.0:
            distribution_ranges["8.0-12.0 (Serious Issues)"] += 1
        else:
            distribution_ranges["12.0-15.0 (Disaster)"] += 1

    # 输出统计结果
    print(f"Total samples: 1000")
    print(f"Average time: {np.mean(results):.2f}s")
    print(f"Min time: {min(results):.2f}s")
    print(f"Max time: {max(results):.2f}s")
    print(f"Standard deviation: {np.std(results):.2f}s")

    print(f"\nSpecial Events:")
    print(
        f"Great Success (<2.0s): {great_success_count}/1000 ({great_success_count / 10:.1f}%)"
    )
    print(
        f"Disaster (>10.0s): {great_failure_count}/1000 ({great_failure_count / 10:.1f}%)"
    )

    print(f"\nDistribution by Range:")
    for range_name, count in distribution_ranges.items():
        percentage = count / 10.0
        print(f"{range_name:25s}: {count:3d} samples ({percentage:5.1f}%)")

    # 验证是否符合预期
    expected_great_success = 50  # 5% of 1000
    expected_disaster = 50  # ~5% of 1000 (from new distribution)

    print(f"\nCompliance Check:")
    print(
        f"Great Success rate: {'✓' if abs(great_success_count - expected_great_success) <= 20 else '✗'} "
        f"(expected ~{expected_great_success}, got {great_success_count})"
    )
    print(
        f"Disaster rate: {'✓' if great_failure_count <= 100 else '✗'} "
        f"(expected <100, got {great_failure_count})"
    )
    print(
        f"Max time reasonable: {'✓' if max(results) < 20 else '✗'} (max was {max(results):.2f}s)"
    )


def determine_pit_strategy(track_name, pit_data):
    """Determine pit strategy using weighted dice based on actual proportions and sample size adjustment"""
    track_data = pit_data[pit_data["Track"] == track_name]

    if track_data.empty:
        print(f"No pit stop data found for track {track_name}")
        return "2"

    track_info = track_data.iloc[0]

    # Get counts for each strategy
    one_stop_count = track_info.get("One_Stop_Count", 0)
    two_stop_count = track_info.get("Two_Stop_Count", 0)
    three_stop_count = track_info.get("Three_Stop_Count", 0)
    four_stop_count = track_info.get("Four_Stop_Count", 0)
    five_stop_count = track_info.get("Five_Stop_Count", 0)

    # Compatibility with old version data
    if pd.isna(three_stop_count):
        three_stop_count = track_info.get("Three_Plus_Stop_Count", 0)

    total_count = (
        one_stop_count
        + two_stop_count
        + three_stop_count
        + four_stop_count
        + five_stop_count
    )

    if total_count == 0:
        return "2"

    # Calculate sample size adjusted weights
    # Penalize small sample strategies to avoid over-amplifying low-probability strategies
    min_sample_threshold = 5  # Minimum sample threshold
    sample_adjustment_factor = 0.3  # Small sample penalty factor

    def calculate_adjusted_weight(count, total):
        """Calculate adjusted weight"""
        if count == 0:
            return 0

        base_weight = count / total

        # Penalize small samples
        if count < min_sample_threshold:
            # Use logarithmic smoothing to avoid completely excluding low-probability strategies
            adjustment = sample_adjustment_factor * (
                np.log(count + 1) / np.log(min_sample_threshold)
            )
            return base_weight * adjustment

        return base_weight

    # Calculate adjusted weights for each strategy
    strategy_weights = {
        "1": calculate_adjusted_weight(one_stop_count, total_count),
        "2": calculate_adjusted_weight(two_stop_count, total_count),
        "3": calculate_adjusted_weight(three_stop_count, total_count),
        "4": calculate_adjusted_weight(four_stop_count, total_count),
        "5": calculate_adjusted_weight(five_stop_count, total_count),
    }

    # Filter valid strategies
    strategies = []
    weights = []
    for strategy, weight in strategy_weights.items():
        if weight > 0:
            strategies.append(strategy)
            weights.append(weight)

    # Normalize weights
    total_weight = sum(weights)
    if total_weight > 0:
        weights = [w / total_weight for w in weights]
    else:
        # If all weights are 0, fallback to simple probability
        strategies = ["2"]
        weights = [1.0]

    # Randomly select strategy based on weights
    strategy = random.choices(strategies, weights=weights)[0]

    return strategy


def generate_pit_laps(track_name, strategy, pit_data):
    """Generate specific pit lap numbers based on strategy"""
    track_data = pit_data[pit_data["Track"] == track_name]

    if track_data.empty:
        return []

    track_info = track_data.iloc[0]
    pit_laps = []

    if strategy == "1":
        if track_info.get("One_Stop_Avg_Lap") and not pd.isna(
            track_info.get("One_Stop_Avg_Lap")
        ):
            avg_lap = track_info.get("One_Stop_Avg_Lap")
            # Random deviation of -10 to +10
            deviation = random.uniform(-10, 10)
            pit_lap = max(1, min(66, int(round(avg_lap + deviation))))
            pit_laps.append(pit_lap)
        else:
            pit_laps = [20]

    elif strategy == "2":
        if track_info.get("Two_Stop_First_Avg") and track_info.get(
            "Two_Stop_Second_Avg"
        ):
            first_avg = track_info.get("Two_Stop_First_Avg")
            second_avg = track_info.get("Two_Stop_Second_Avg")

            # First pit stop
            deviation1 = random.uniform(-10, 10)
            first_pit = max(1, min(66, int(round(first_avg + deviation1))))

            # Second pit stop
            deviation2 = random.uniform(-10, 10)
            second_pit = max(
                first_pit + 5, min(66, int(round(second_avg + deviation2)))
            )

            pit_laps = [first_pit, second_pit]
        else:
            # Use default values
            pit_laps = [12, 28]

    elif strategy == "3":
        # For 3 stops, if not enough data, use 2-stop data as base
        if not (
            track_info.get("Three_Stop_First_Avg")
            and track_info.get("Three_Stop_Second_Avg")
            and track_info.get("Three_Stop_Third_Avg")
        ):
            # Fallback to 2-stop strategy data
            if track_info.get("Two_Stop_First_Avg") and track_info.get(
                "Two_Stop_Second_Avg"
            ):
                first_avg = track_info.get("Two_Stop_First_Avg")
                second_avg = track_info.get("Two_Stop_Second_Avg")
                # Calculate third pit stop (based on second delayed by ~8 laps)
                third_avg = min(66, second_avg + 8)
            else:
                # Use default values
                first_avg, second_avg, third_avg = 12, 28, 48
        else:
            first_avg = track_info.get("Three_Stop_First_Avg")
            second_avg = track_info.get("Three_Stop_Second_Avg")
            third_avg = track_info.get("Three_Stop_Third_Avg")

        # Three pit stops
        deviation1 = random.uniform(-10, 10)
        first_pit = max(1, min(66, int(round(first_avg + deviation1))))

        deviation2 = random.uniform(-10, 10)
        second_pit = max(first_pit + 5, min(66, int(round(second_avg + deviation2))))

        deviation3 = random.uniform(-10, 10)
        third_pit = max(second_pit + 5, min(66, int(round(third_avg + deviation3))))

        pit_laps = [first_pit, second_pit, third_pit]

    elif strategy == "4":
        # For 4 stops, if not enough data, use 3-stop data as base
        if not (
            track_info.get("Four_Stop_First_Avg")
            and track_info.get("Four_Stop_Second_Avg")
            and track_info.get("Four_Stop_Third_Avg")
            and track_info.get("Four_Stop_Fourth_Avg")
        ):
            # Fallback to 3-stop strategy data
            if (
                track_info.get("Three_Stop_First_Avg")
                and track_info.get("Three_Stop_Second_Avg")
                and track_info.get("Three_Stop_Third_Avg")
            ):
                first_avg = track_info.get("Three_Stop_First_Avg")
                second_avg = track_info.get("Three_Stop_Second_Avg")
                third_avg = track_info.get("Three_Stop_Third_Avg")
                # Calculate fourth pit stop (based on third delayed by ~6 laps)
                fourth_avg = min(66, third_avg + 6)
            else:
                # Use default values
                first_avg, second_avg, third_avg, fourth_avg = 8, 20, 32, 44
        else:
            first_avg = track_info.get("Four_Stop_First_Avg")
            second_avg = track_info.get("Four_Stop_Second_Avg")
            third_avg = track_info.get("Four_Stop_Third_Avg")
            fourth_avg = track_info.get("Four_Stop_Fourth_Avg")

        # Four pit stops
        deviation1 = random.uniform(-10, 10)
        first_pit = max(1, min(66, int(round(first_avg + deviation1))))

        deviation2 = random.uniform(-10, 10)
        second_pit = max(first_pit + 5, min(66, int(round(second_avg + deviation2))))

        deviation3 = random.uniform(-10, 10)
        third_pit = max(second_pit + 5, min(66, int(round(third_avg + deviation3))))

        deviation4 = random.uniform(-10, 10)
        fourth_pit = max(third_pit + 5, min(66, int(round(fourth_avg + deviation4))))

        pit_laps = [first_pit, second_pit, third_pit, fourth_pit]

    elif strategy == "5":
        # For 5 stops, use default values
        first_avg, second_avg, third_avg, fourth_avg, fifth_avg = 6, 16, 26, 36, 46

        # Five pit stops
        deviation1 = random.uniform(-10, 10)
        first_pit = max(1, min(66, int(round(first_avg + deviation1))))

        deviation2 = random.uniform(-10, 10)
        second_pit = max(first_pit + 5, min(66, int(round(second_avg + deviation2))))

        deviation3 = random.uniform(-10, 10)
        third_pit = max(second_pit + 5, min(66, int(round(third_avg + deviation3))))

        deviation4 = random.uniform(-10, 10)
        fourth_pit = max(third_pit + 5, min(66, int(round(fourth_avg + deviation4))))

        deviation5 = random.uniform(-10, 10)
        fifth_pit = max(fourth_pit + 5, min(66, int(round(fifth_avg + deviation5))))

        pit_laps = [first_pit, second_pit, third_pit, fourth_pit, fifth_pit]

    return pit_laps


def simulate_race_with_pit_stops(
    driver_name,
    driver_info,
    num_laps,
    track_name,
    track_chars,
    r_max,
    dr_min,
    dr_max,
    pit_data,
    team_strategies=None,
):
    """Simulate race with pit stops"""

    # Load pitlane time data
    pitlane_data = load_pitlane_time_data()

    # Get track pit time from pitlane_time.csv
    track_pit_time = 25.0  # Default fallback
    if pitlane_data is not None:
        track_row = pitlane_data[pitlane_data["Track"] == track_name]
        if len(track_row) > 0:
            track_pit_time = float(track_row["Pit Time"].iloc[0])
        else:
            print(
                f"Warning: Track {track_name} not found in tables/pitlane_time.csv, using default 25.0s"
            )
    else:
        print(
            "Warning: tables/pitlane_time.csv not found, using default 25.0s pit time"
        )

    # 如果提供了车队策略，使用车队统一的策略
    if team_strategies and driver_name in team_strategies:
        team_strategy = team_strategies[driver_name]
        strategy = team_strategy["strategy"]

        # 为每个车手独立生成进站圈数（保持随机性）
        pit_laps = generate_pit_laps(track_name, strategy, pit_data)

        # 为车手生成个性化的轮胎序列顺序
        tyre_compounds_set = team_strategy["tyre_compounds_set"]
        tyre_sequence = generate_individual_tyre_sequence(tyre_compounds_set)

        # 验证车队轮胎集合是否合规
        unique_compounds = set(tyre_compounds_set)
        if len(unique_compounds) < 2:
            print(
                f"  Team Strategy Warning: {driver_name} team only has {len(unique_compounds)} compound type"
            )
            print(f"  Available compounds: {tyre_compounds_set}")
    else:
        # 兜底方案：生成个人策略（向后兼容）
        strategy = determine_pit_strategy(track_name, pit_data)
        pit_laps = generate_pit_laps(track_name, strategy, pit_data)
        tyre_sequence = [roll_tyre_for_track(track_name)]

        for i in range(len(pit_laps)):
            # 使用智能轮胎选择确保F1规则合规
            force_different = len(set(tyre_sequence)) < 2
            avoid_compound = tyre_sequence[-1] if i > 0 else None

            pit_tyre = smart_tyre_selection(
                track_name,
                tyre_sequence,
                avoid_compound=avoid_compound,
                force_different=force_different,
            )
            tyre_sequence.append(pit_tyre)

        # 最终验证：确保至少有两种不同轮胎
        tyre_sequence = ensure_f1_tyre_compliance(
            tyre_sequence, get_available_compounds_for_track(track_name)
        )

    print(
        f"{driver_name}: {strategy}-stop strategy, pit laps: {pit_laps}, tyre sequence: {tyre_sequence}"
    )

    # 验证轮胎规则
    unique_tyres = set(tyre_sequence)
    if len(unique_tyres) < 2:
        print(
            f"  WARNING: {driver_name} only uses {len(unique_tyres)} type of tire: {unique_tyres}"
        )
        print(
            f"  This violates F1 rules requiring at least 2 different tire compounds!"
        )
    else:
        print(
            f"  ✓ F1 Rule Compliant: Uses {len(unique_tyres)} different tire types: {unique_tyres}"
        )

    # Simulate race
    lap_times = []
    cumulative_time = 0
    current_tyre_index = 0
    lap_count_on_current_tyre = 0

    # Data storage for analysis
    tyre_ages = []
    tyre_compounds = []
    pit_events = []

    # Initialize start lap variables
    start_lap_delta = 0.0
    start_lap_breakdown = {
        "error": "No start simulation performed",
        "special_events": [],
        "grid_penalty": 0.0,
        "reaction_acceleration": 0.0,
        "track_info": {
            "straight_length": 0,
            "complexity": "unknown",
            "category": "unknown",
        },
    }

    for lap in range(1, num_laps + 1):
        # Start lap simulation (仅第1圈)
        if lap == 1:
            # 获取发车位次（如果没有提供，默认为1）
            grid_position = driver_info.get("grid_position", 1)

            # 计算发车时间附加
            start_lap_delta, start_lap_breakdown = calculate_start_lap_delta(
                grid_position,
                driver_name,  # 使用车手姓名而不是R值
                driver_info["R_Value"],
                track_name,
                track_chars,
            )

            print(
                f"{driver_name} 发车附加: {start_lap_delta:.3f}s (发车位: {grid_position})"
            )

        # Check if pit stop
        if lap in pit_laps:
            # Calculate pit stop time: track base time + dice roll for tire change
            tire_change_time = roll_pit_stop_time()
            pit_time = track_pit_time + tire_change_time
            cumulative_time += pit_time
            current_tyre_index += 1
            lap_count_on_current_tyre = 0
            # Record pit stop information
            pit_events.append(
                {
                    "lap": lap,
                    "driver": driver_name,
                    "stop_number": current_tyre_index,
                    "pit_time": pit_time,
                    "track_base_time": track_pit_time,
                    "tire_change_time": tire_change_time,
                }
            )

        # Calculate lap time
        current_tyre = tyre_sequence[current_tyre_index]
        lap_count_on_current_tyre += 1

        # Save lap time data
        tyre_ages.append(lap_count_on_current_tyre)
        tyre_compounds.append(current_tyre)

        # Calculate base lap time using track-specific formula
        # Uses the new TRACK_BASE_LAP_TIMES configuration
        base_lap_time = calculate_base_lap_time(driver_info["R_Value"], track_name)

        # Tire degradation
        degradation = calculate_degradation_with_cliff(
            lap_count_on_current_tyre,
            current_tyre,
            driver_info["R_Value"],
            r_max,
            track_chars,
            len(pit_laps),
        )

        # DR value related standard deviation
        # Increased from 0.25 to 0.45 for more realistic lap time variance
        # Real F1 lap times show ~1.5-2.0s std dev during race
        noise_std = calculate_dr_based_std(
            driver_info["DR_Value"], dr_min, dr_max, 0.45
        )

        # Final lap time
        lap_time = base_lap_time + degradation * 10 + np.random.normal(0, noise_std)

        # 仅第1圈添加发车时间附加
        if lap == 1:
            lap_time += start_lap_delta

        cumulative_time += lap_time
        lap_times.append(lap_time)

    return {
        "total_time": cumulative_time,
        "lap_times": lap_times,
        "strategy": strategy,
        "pit_laps": pit_laps,
        "tyre_sequence": tyre_sequence[: len(pit_laps) + 1],
        "tyre_ages": tyre_ages,
        "tyre_compounds": tyre_compounds,
        "pit_events": pit_events,
        "driver_name": driver_name,
        "start_lap_delta": start_lap_delta,
        "start_lap_breakdown": start_lap_breakdown,
        "grid_position": driver_info.get("grid_position", 1),
    }


DEFAULT_LAP_COUNTS = {
    "bahrain": 57,
    "spain": 66,
    "monaco": 78,
    "canada": 70,
    "azerbaijan": 51,
    "austria": 71,
    "britain": 52,
    "hungary": 70,
    "belgium": 44,
    "netherlands": 72,
    "italy": 53,
    "singapore": 61,
    "japan": 53,
    "usa": 56,
    "mexico": 71,
    "brazil": 71,
    "abudhabi": 58,
}


def build_arg_parser():
    """Create the CLI argument parser for the race simulation."""

    parser = argparse.ArgumentParser(
        description="Run the long distance F1 race simulation with configurable inputs."
    )
    parser.add_argument(
        "--year",
        type=int,
        default=2022,
        help="Season year metadata used in reporting.",
    )
    parser.add_argument(
        "--gp-name",
        default="Spain",
        help="Grand Prix name (used to locate tables/<gp>.csv and track metadata).",
    )
    parser.add_argument(
        "--csv-file",
        help="Explicit driver CSV path. Defaults to tables/<gp-name>.csv if omitted.",
    )
    parser.add_argument(
        "--num-laps",
        type=int,
        help="Override the race lap count. Defaults to a track-specific value when available.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        help="Seed for random number generators to make the simulation reproducible.",
    )
    parser.add_argument(
        "--test-pit-distribution",
        action="store_true",
        help="Run only the pit stop distribution diagnostic and exit.",
    )
    return parser


def resolve_lap_count(gp_name, override):
    """Determine the number of race laps, allowing overrides and per-track defaults."""

    if override is not None:
        return override

    track_key = gp_name.lower().replace(" ", "")
    return DEFAULT_LAP_COUNTS.get(track_key, 66)


def main(argv=None):
    """Run the long distance simulation with CLI argument support."""

    parser = build_arg_parser()
    args = parser.parse_args(argv)

    if args.test_pit_distribution:
        test_pit_stop_distribution()
        return

    if args.seed is not None:
        random.seed(args.seed)
        np.random.seed(args.seed)

    # Set parameters based on CLI options
    year = args.year
    gp_name = args.gp_name
    csv_file = args.csv_file or os.path.join("outputs/tables", f"{gp_name}.csv")
    csv_file = os.path.normpath(csv_file)
    num_laps = resolve_lap_count(gp_name, args.num_laps)

    print("=== F1 Race Simulation - with Pit Strategy ===")
    print(f"Track: {gp_name}, Year: {year}")
    print("Run with --test-pit-distribution to test pit stop time distribution")
    print(f"Driver data CSV: {csv_file}")
    if args.seed is not None:
        print(f"Random seed set to {args.seed}")

    # 1. Load driver data
    print(f"\n=== Loading Driver Data ===")
    driver_data = read_driver_data(csv_file)
    print(f"Loaded {len(driver_data)} drivers' R and DR values from CSV")

    if not driver_data:
        print("Error: No driver data loaded, please check CSV file format")
        return

    # Calculate R and DR min/max values
    r_values = [data["R_Value"] for data in driver_data.values()]
    dr_values = [data["DR_Value"] for data in driver_data.values()]
    r_max = max(r_values)
    r_min = min(r_values)
    dr_max = max(dr_values)
    dr_min = min(dr_values)

    print(f"R value range: {r_min:.3f} - {r_max:.3f}")
    print(f"DR value range: {dr_min:.1f} - {dr_max:.1f}")

    # 2. Load pit stop data
    print(f"\n=== Loading Pit Stop Data ===")
    pit_data = load_pit_stop_data()
    if pit_data is None:
        return

    # 3. Get track characteristics
    track_chars = get_track_characteristics()
    track_key = gp_name.lower()
    if track_key not in track_chars:
        print(f"Track {gp_name} characteristics data not found")
        return

    current_track_chars = track_chars[track_key]

    # Collect all drivers' lap times and positions for plotting
    all_drivers_laptimes = {}
    all_drivers_positions = {}

    # 4. Generate team strategies (车队统一策略)
    print(f"\n=== Generating Team Strategies ===")
    team_strategies_data, driver_teams = assign_team_strategies(
        driver_data, gp_name, num_laps, pit_data
    )

    # 为每个车手分配对应的车队策略
    driver_team_strategies = {}
    for driver_name, driver_info in driver_data.items():
        team_name = driver_info.get("Team", "Unknown")
        driver_team_strategies[driver_name] = team_strategies_data[team_name]

    # 显示车队策略
    for team_name, strategy in team_strategies_data.items():
        if team_name != "Unknown":
            team_drivers = [
                driver for driver, team in driver_teams.items() if team == team_name
            ]
            print(
                f"{team_name}: {strategy['strategy']}-stop, tyre set: {strategy['tyre_compounds_set']} (drivers: {', '.join(team_drivers)})"
            )

    # 5. 为车手分配随机发车位次
    print(f"\n=== Assigning Grid Positions ===")
    all_driver_names = list(driver_data.keys())
    np.random.shuffle(all_driver_names)  # 随机打乱顺序

    for i, driver_name in enumerate(all_driver_names):
        driver_data[driver_name]["grid_position"] = i + 1

    # 显示发车格
    print("发车格:")
    for driver_name in sorted(
        all_driver_names, key=lambda x: driver_data[x]["grid_position"]
    ):
        grid_pos = driver_data[driver_name]["grid_position"]
        print(f"  {grid_pos:2d}: {driver_name}")

    # 6. Simulate race for each driver
    print(f"\n=== Starting Race Simulation ===")
    print(f"Total laps: {num_laps}")
    results = {}

    # Also collect pit stop data for display
    all_pit_events = []

    for driver_name, driver_info in driver_data.items():
        result = simulate_race_with_pit_stops(
            driver_name,
            driver_info,
            num_laps,
            gp_name,
            current_track_chars,
            r_max,
            dr_min,
            dr_max,
            pit_data,
            team_strategies=driver_team_strategies,
        )
        results[driver_name] = result
        result["driver_name"] = driver_name

        # Collect all pit stop events for overall display
        for pit_event in result.get("pit_events", []):
            all_pit_events.append(
                {
                    "lap": pit_event["lap"],
                    "driver": driver_name,
                    "stop_number": pit_event["stop_number"],
                    "pit_time": pit_event.get("pit_time", 0),
                    "track_base_time": pit_event.get("track_base_time", 0),
                    "tire_change_time": pit_event.get("tire_change_time", 0),
                }
            )

    # 5. Output results
    print(f"\n=== Final Race Results ===")
    sorted_results = sorted(results.items(), key=lambda x: x[1]["total_time"])

    for i, (driver_name, result) in enumerate(sorted_results, 1):
        time_str = f"{result['total_time']:.1f} seconds"
        time_minutes = result["total_time"] / 60
        grid_pos = result.get("grid_position", 1)
        start_delta = result.get("start_lap_delta", 0)
        print(
            f"{i:2d}. {driver_name}: {time_str} ({time_minutes:.1f} min) - {result['strategy']} stop, Grid: {grid_pos}, Start: +{start_delta:.3f}s"
        )

    # 6. 分析发车表现
    print(f"\n=== Start Performance Analysis ===")
    start_results = {}
    for driver_name, result in results.items():
        if "start_lap_delta" in result:
            # 安全获取r_value，防止key error
            r_value = 300.0  # 默认值
            if driver_name in driver_data and "R_Value" in driver_data[driver_name]:
                r_value = driver_data[driver_name]["R_Value"]

            start_results[driver_name] = {
                "delta_time": result["start_lap_delta"],
                "breakdown": result.get("start_lap_breakdown", {}),
                "grid_position": result.get("grid_position", 1),
                "r_value": r_value,
            }

    if start_results:
        print_start_lap_analysis(start_results, gp_name)

    # 7. Output F1 tire rule compliance summary
    print_tyre_rule_summary(results)

    # 7. Output detailed pit stop information
    if all_pit_events:
        print(f"\n=== Detailed Pit Stop Information ===")

        # Group pit stops by driver for better readability
        driver_pits = defaultdict(list)
        for event in all_pit_events:
            driver_pits[event["driver"]].append(event)

        # Sort drivers by their final race position
        sorted_drivers = sorted(results.items(), key=lambda x: x[1]["total_time"])

        for driver_name, result in sorted_drivers:
            if driver_name in driver_pits:
                driver_events = driver_pits[driver_name]
                print(f"\n{driver_name} ({result['strategy']}-stop strategy):")

                # Sort pit stops by lap number
                driver_events.sort(key=lambda x: x["lap"])

                total_pit_time = 0
                for event in driver_events:
                    pit_time = event.get("pit_time", 0)
                    track_base_time = event.get("track_base_time", 0)
                    tire_change_time = event.get("tire_change_time", 0)

                    pit_time_str = (
                        f"{pit_time:.2f}s"
                        if isinstance(pit_time, (int, float))
                        else f"{pit_time}s"
                    )
                    base_time_str = (
                        f"{track_base_time:.1f}s"
                        if isinstance(track_base_time, (int, float))
                        else f"{track_base_time}s"
                    )
                    tire_time_str = (
                        f"{tire_change_time:.2f}s"
                        if isinstance(tire_change_time, (int, float))
                        else f"{tire_change_time}s"
                    )

                    # Add special indicators for exceptional pit stops
                    indicator = ""
                    if isinstance(tire_change_time, (int, float)):
                        if tire_change_time < 2.0:
                            indicator = " ⚡ (EXCELLENT!)"
                        elif tire_change_time > 8.0:
                            indicator = " ❌ (DISASTER!)"
                        elif tire_change_time > 5.0:
                            indicator = " ⚠️  (SLOW!)"

                    print(
                        f"  Lap {event['lap']:2d}: Total {pit_time_str} (Base {base_time_str} + Tire {tire_time_str}){indicator}"
                    )

                    if isinstance(pit_time, (int, float)):
                        total_pit_time += pit_time

                if total_pit_time > 0:
                    print(f"  Total time spent in pits: {total_pit_time:.2f}s")

        # Summary statistics
        print(f"\n=== Pit Stop Summary ===")
        total_pits = len(all_pit_events)
        pit_times = [
            event.get("pit_time", 0)
            for event in all_pit_events
            if isinstance(event.get("pit_time"), (int, float))
        ]
        tire_times = [
            event.get("tire_change_time", 0)
            for event in all_pit_events
            if isinstance(event.get("tire_change_time"), (int, float))
        ]

        if pit_times:
            avg_pit_time = sum(pit_times) / len(pit_times)
            min_pit_time = min(pit_times)
            max_pit_time = max(pit_times)

            # Find drivers with fastest and slowest stops
            fastest_event = min(
                all_pit_events,
                key=lambda x: (
                    x.get("pit_time", float("inf"))
                    if isinstance(x.get("pit_time"), (int, float))
                    else float("inf")
                ),
            )
            slowest_event = max(
                all_pit_events,
                key=lambda x: (
                    x.get("pit_time", 0)
                    if isinstance(x.get("pit_time"), (int, float))
                    else 0
                ),
            )

            print(f"Total pit stops across all drivers: {total_pits}")
            print(f"Average pit time: {avg_pit_time:.2f}s")
            print(
                f"Fastest pit stop: {min_pit_time:.2f}s ({fastest_event['driver']}, Lap {fastest_event['lap']})"
            )
            print(
                f"Slowest pit stop: {max_pit_time:.2f}s ({slowest_event['driver']}, Lap {slowest_event['lap']})"
            )

        if tire_times:
            avg_tire_time = sum(tire_times) / len(tire_times)
            min_tire_time = min(tire_times)
            max_tire_time = max(tire_times)

            # Count exceptional tire changes
            excellent_changes = sum(1 for t in tire_times if t < 2.0)
            disaster_changes = sum(1 for t in tire_times if t > 10.0)

            print(f"Average tire change time: {avg_tire_time:.2f}s")
            print(f"Fastest tire change: {min_tire_time:.2f}s")
            print(f"Slowest tire change: {max_tire_time:.2f}s")

            if excellent_changes > 0:
                print(f"Excellent tire changes (<2.0s): {excellent_changes}")
            if disaster_changes > 0:
                print(f"Disaster tire changes (>10.0s): {disaster_changes}")

        # Pit stop efficiency by lap
        print(f"\n=== Pit Stop Activity by Lap ===")
        lap_stats = defaultdict(list)
        for event in all_pit_events:
            lap_stats[event["lap"]].append(event)

        for lap in sorted(lap_stats.keys()):
            events = lap_stats[lap]
            drivers = [event["driver"] for event in events]
            avg_time = sum(
                event.get("pit_time", 0)
                for event in events
                if isinstance(event.get("pit_time"), (int, float))
            ) / len([e for e in events if isinstance(e.get("pit_time"), (int, float))])

            print(
                f"Lap {lap:2d}: {len(events)} pit stop(s) - {', '.join(drivers)} (Avg: {avg_time:.2f}s)"
            )

    # 7. Generate charts
    print(f"\n=== Generating Analysis Charts ===")

    # Calculate position data per lap
    positions_by_lap = defaultdict(list)
    driver_names = list(results.keys())
    num_laps = len(results[driver_names[0]]["lap_times"])

    for lap in range(1, num_laps + 1):
        # Collect cumulative times for all drivers in current lap
        current_times = {}

        for driver_name in driver_names:
            if lap <= len(results[driver_name]["lap_times"]):
                # Cumulative lap time (including previous pit stop times)
                lap_time_sum = sum(results[driver_name]["lap_times"][:lap])
                # Add pit stop times
                pit_penalty = 0.0
                for pit_event in results[driver_name].get("pit_events", []):
                    if pit_event["lap"] <= lap:
                        pit_penalty += 25.0  # 25 seconds per pit stop

                current_times[driver_name] = lap_time_sum + pit_penalty

        # Sort by time to determine positions
        sorted_drivers = sorted(current_times.items(), key=lambda x: x[1])

        for position, (driver_name, _) in enumerate(sorted_drivers, 1):
            positions_by_lap[driver_name].append(position)

    # Generate charts
    generate_position_chart(positions_by_lap, gp_name)
    generate_laptime_scatter(results, positions_by_lap, gp_name, sorted_results)

    # Generate Markdown report
    generate_markdown_report(
        results, sorted_results, all_pit_events, start_results, gp_name, year
    )


def generate_position_chart(positions_by_lap, track_name):
    """Generate driver position progression line chart"""
    print("Generating position chart...")

    plt.figure(figsize=(20, 14))
    plt.style.use("default")

    driver_names = list(positions_by_lap.keys())
    num_drivers = len(driver_names)
    colors = plt.colormaps.get_cmap("tab20")(np.linspace(0, 1, num_drivers))

    # Use smart legend handling
    legend_indices = get_smart_legend_indices(num_drivers, max_display=15)
    legend_set = set(legend_indices)

    for i, driver_name in enumerate(driver_names):
        laps = list(range(1, len(positions_by_lap[driver_name]) + 1))
        positions = positions_by_lap[driver_name]

        # Draw line chart
        plt.plot(
            laps,
            positions,
            color=colors[i],
            linewidth=2,
            alpha=0.8,
            marker="o",
            markersize=3,  # Smaller markers for better visibility
            label=f"{driver_name}" if i in legend_set else None,  # Smart labeling
        )

    plt.gca().invert_yaxis()  # Invert Y-axis so position 1 is at the top
    plt.xlabel("Lap Number", fontsize=14)
    plt.ylabel("Position", fontsize=14)
    plt.title(
        f"F1 {track_name} Race Position Progression",
        fontsize=16,
        fontweight="bold",
        pad=15,
    )
    plt.grid(True, alpha=0.3)

    # Adjust legend with better positioning
    if num_drivers > 15:
        plt.legend(bbox_to_anchor=(1.02, 1), loc="upper left", fontsize=8, ncol=2)
    else:
        plt.legend(bbox_to_anchor=(1.02, 1), loc="upper left", fontsize=9)

    # Use subplots_adjust instead of tight_layout to avoid warnings
    plt.subplots_adjust(
        left=0.08, right=0.85, top=0.93, bottom=0.08, hspace=0.3, wspace=0.2
    )

    # Save chart to output figs subfolder
    os.makedirs(FIGS_OUTPUT_DIR, exist_ok=True)
    chart_filename = os.path.join(
        FIGS_OUTPUT_DIR, f"{track_name.lower()}_position_progression.png"
    )
    plt.savefig(chart_filename, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close()

    print(f"Position progression chart saved as: {chart_filename}")


def generate_laptime_scatter(results, positions_by_lap, track_name, sorted_results):
    """Generate lap time change scatter plot"""
    print("Generating lap time scatter plot...")

    plt.figure(figsize=(18, 12))
    plt.style.use("default")

    # Get drivers sorted by final position
    driver_names = [driver_name for driver_name, _ in sorted_results]
    num_drivers = len(driver_names)
    colors = plt.colormaps.get_cmap("tab20")(np.linspace(0, 1, num_drivers))

    # Initialize list to collect all pit events for intelligent labeling
    driver_pit_events = []

    # Different markers for different tire compounds (shapes only, no colors)
    compound_markers = {
        "C1": "o",  # Circle for C1
        "C2": "s",  # Square for C2
        "C3": "^",  # Triangle for C3
        "C4": "D",  # Diamond for C4
        "C5": "v",  # Inverted triangle for C5
        "UNKNOWN": "x",  # X for unknown
    }

    # Create scatter plot for each driver
    for i, driver_name in enumerate(driver_names):
        result = results[driver_name]
        lap_times = result["lap_times"]
        tyre_compounds = result["tyre_compounds"]
        pit_events = result.get("pit_events", [])

        # Create lap numbers list
        laps = list(range(1, len(lap_times) + 1))

        # Group laps by tire compound
        current_compound = tyre_compounds[0] if tyre_compounds else "UNKNOWN"
        current_compound_start = 1

        for lap_idx in range(len(lap_times)):
            lap_num = lap_idx + 1

            # Check if we need to switch compound groups
            if (
                lap_idx < len(tyre_compounds)
                and tyre_compounds[lap_idx] != current_compound
            ):
                # Plot previous compound group
                compound_laps = laps[current_compound_start - 1 : lap_idx]
                compound_times = lap_times[current_compound_start - 1 : lap_idx]

                marker = compound_markers.get(current_compound, "o")
                # Use driver color for all tire types
                color = colors[i]

                plt.scatter(
                    compound_laps,
                    compound_times,
                    c=[color],  # Use driver color
                    marker=marker,  # Use tire shape
                    s=60,
                    alpha=0.8,
                    label=f"{driver_name}" if current_compound_start == 1 else None,
                    edgecolors="white",
                    linewidth=0.5,
                )

                # Update for new compound
                current_compound = tyre_compounds[lap_idx]
                current_compound_start = lap_num

        # Plot the last compound group
        if current_compound_start <= len(laps):
            compound_laps = laps[current_compound_start - 1 :]
            compound_times = lap_times[current_compound_start - 1 :]

            marker = compound_markers.get(current_compound, "o")
            # Use driver color for all tire types
            color = colors[i]

            plt.scatter(
                compound_laps,
                compound_times,
                c=[color],  # Use driver color
                marker=marker,  # Use tire shape
                s=60,
                alpha=0.8,
                label=f"{driver_name}" if current_compound_start == 1 else None,
                edgecolors="white",
                linewidth=0.5,
            )

        # Collect all pit events for this driver for later processing
        driver_pit_events.extend(
            [
                (pit_lap, pit_event, i)
                for pit_event in pit_events
                if (pit_lap := pit_event["lap"]) <= len(lap_times)
            ]
        )

        # Mark pit stop vertical lines
        for pit_event in pit_events:
            pit_lap = pit_event["lap"]
            if pit_lap <= len(lap_times):
                plt.axvline(
                    x=pit_lap, color=colors[i], linestyle="--", alpha=0.3, linewidth=1
                )

    # Process all pit events together to avoid overlapping labels
    if driver_pit_events:
        # Group pit events by lap number
        pit_groups = {}
        for pit_lap, pit_event, driver_idx in driver_pit_events:
            if pit_lap not in pit_groups:
                pit_groups[pit_lap] = []
            pit_groups[pit_lap].append((pit_event, driver_idx))

        # Add labels with intelligent positioning
        plot_height = plt.ylim()[1] - plt.ylim()[0]
        base_y = plt.ylim()[0] + plot_height * 0.015  # Very close to bottom

        for pit_lap, events in sorted(pit_groups.items()):
            # Sort events by driver index to maintain consistent ordering
            events.sort(key=lambda x: x[1])

            for idx, (pit_event, driver_idx) in enumerate(events):
                # Calculate vertical offset to avoid overlap
                vertical_spacing = plot_height * 0.018  # Compact spacing
                y_offset = idx * vertical_spacing

                # Ensure we don't exceed the maximum allowed height
                max_y = plt.ylim()[0] + plot_height * 0.12  # Max 12% of plot height
                final_y = min(base_y + y_offset, max_y)

                plt.text(
                    pit_lap,
                    final_y,
                    f"P{pit_event['stop_number']}",
                    rotation=90,
                    fontsize=4,
                    color=colors[driver_idx],
                    alpha=0.8,
                    va="bottom",
                    ha="center",
                    weight="bold",
                )

    # Note: driver_pit_events will be reinitialized for each function call
    # No need to reset here as it's local to this function

    plt.xlabel("Lap Number", fontsize=14)
    plt.ylabel("Lap Time (seconds)", fontsize=14)
    plt.title(
        f"F1 {track_name} Race - Lap Time Analysis",
        fontsize=16,
        fontweight="bold",
    )

    # Add subtitle explaining the color/shape system
    plt.figtext(
        0.5,
        0.98,
        "Colors = Drivers | Shapes = Tire Compounds",
        ha="center",
        va="top",
        fontsize=12,
        style="italic",
        alpha=0.8,
    )
    plt.grid(True, alpha=0.3)

    # Create tire compound legend (shapes only, no colors)
    compound_handles = []
    compound_labels = []

    # Check which compounds are actually used
    used_compounds = set()
    for result in results.values():
        used_compounds.update(result.get("tyre_compounds", []))

    for compound in sorted(used_compounds):
        if compound in compound_markers:
            handle = plt.scatter(
                [],
                [],
                c="black",  # Use black for better visibility
                marker=compound_markers[compound],
                s=80,  # Slightly larger for better visibility
                alpha=0.9,
                edgecolors="white",
                linewidth=1.0,
            )
            compound_handles.append(handle)
            compound_labels.append(f"Compound {compound}")

    # Create two legends: one for drivers, one for compounds
    # Use smart legend handling for drivers
    legend_indices = get_smart_legend_indices(num_drivers, max_display=12)
    driver_handles = [
        plt.scatter([], [], c=[colors[i]], marker="o", s=60, alpha=0.8)
        for i in legend_indices
    ]
    driver_labels = [driver_names[i] for i in legend_indices]

    # Create driver legend first
    driver_legend = plt.legend(
        handles=driver_handles,
        labels=driver_labels,
        title="Drivers",
        bbox_to_anchor=(1.02, 1),
        loc="upper left",
        fontsize=8,
    )

    # Create tire compound legend (only if we have compounds)
    if compound_handles:
        compound_legend = plt.legend(
            compound_handles,
            compound_labels,
            title="Tire Compounds\n(Shapes)",
            bbox_to_anchor=(1.02, 0.35),
            loc="upper left",
            fontsize=8,
        )

        # Add driver legend back to the plot
        plt.gca().add_artist(driver_legend)
    else:
        # If no compounds, just use driver legend
        plt.gca().add_artist(driver_legend)

    # Use subplots_adjust instead of tight_layout to avoid warnings
    plt.subplots_adjust(
        left=0.08, right=0.88, top=0.90, bottom=0.10, hspace=0.3, wspace=0.2
    )

    # Save chart to output figs subfolder
    os.makedirs(FIGS_OUTPUT_DIR, exist_ok=True)
    chart_filename = os.path.join(
        FIGS_OUTPUT_DIR, f"{track_name.lower()}_laptime_scatter.png"
    )
    plt.savefig(chart_filename, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close()

    print(f"Lap time scatter plot saved as: {chart_filename}")


def generate_markdown_report(
    results, sorted_results, all_pit_events, start_results, gp_name, year
):
    """Generate comprehensive Markdown race report"""

    # Create reports directory if it doesn't exist
    os.makedirs(REPORT_OUTPUT_DIR, exist_ok=True)

    # Generate filename
    timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
    markdown_file = os.path.join(
        REPORT_OUTPUT_DIR, f"{gp_name.lower()}_race_report_{timestamp}.md"
    )

    # Resolve relative paths for figures used in the report
    position_chart_filename = f"{gp_name.lower()}_position_progression.png"
    laptime_chart_filename = f"{gp_name.lower()}_laptime_scatter.png"
    markdown_dir = os.path.dirname(markdown_file)
    position_chart_rel = os.path.relpath(
        os.path.join(FIGS_OUTPUT_DIR, position_chart_filename),
        start=markdown_dir,
    ).replace("\\", "/")
    laptime_chart_rel = os.path.relpath(
        os.path.join(FIGS_OUTPUT_DIR, laptime_chart_filename),
        start=markdown_dir,
    ).replace("\\", "/")

    with open(markdown_file, "w", encoding="utf-8") as f:
        # Header
        f.write(f"# F1 {gp_name} {year} Race Simulation Report\n\n")
        f.write(
            f"**Generated on:** {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        )

        # Part 1: Race Results
        f.write("## 🏁 Race Results\n\n")
        f.write(
            "| Pos | Driver | Total Time | Minutes | Strategy | Grid | Start Delta |\n"
        )
        f.write(
            "|-----|--------|------------|----------|-----------|-------|-------------|\n"
        )

        for i, (driver_name, result) in enumerate(sorted_results, 1):
            total_time = result["total_time"]
            minutes = total_time / 60
            strategy = result["strategy"]
            grid_pos = result.get("grid_position", "N/A")
            start_delta = result.get("start_lap_delta", 0)

            f.write(
                f"| {i} | {driver_name} | {total_time:.1f}s | {minutes:.1f}min | "
                f"{strategy} | {grid_pos} | +{start_delta:.3f}s |\n"
            )

        # Part 2: Pit Stop Analysis (Strategy Details)
        f.write("\n## 🛠️ Pit Stop Strategy Analysis\n\n")
        f.write(
            "| Driver | Strategy | Pit Laps | Pit Times | Tire Change Times | Tire Sequence |\n"
        )
        f.write(
            "|--------|-----------|-----------|------------|-------------------|---------------|\n"
        )

        for driver_name, result in sorted_results:
            strategy = result["strategy"]
            pit_laps = result.get("pit_laps", [])
            pit_events = result.get("pit_events", [])
            tyre_sequence = result.get("tyre_sequence", [])

            # Format pit laps
            pit_laps_str = (
                ", ".join(str(lap) for lap in pit_laps) if pit_laps else "None"
            )

            # Format pit times (total pit time including track time)
            pit_times_str = []
            for event in pit_events:
                pit_time = event.get("pit_time", 0)
                if isinstance(pit_time, (int, float)):
                    pit_times_str.append(f"{pit_time:.2f}s")
                else:
                    pit_times_str.append(str(pit_time))

            pit_times_str = ", ".join(pit_times_str) if pit_times_str else "N/A"

            # Format tire change times (only the tire change portion)
            tire_change_times_str = []
            for event in pit_events:
                tire_change_time = event.get("tire_change_time", 0)
                if isinstance(tire_change_time, (int, float)):
                    tire_change_times_str.append(f"{tire_change_time:.2f}s")
                else:
                    tire_change_times_str.append(str(tire_change_time))

            tire_change_times_str = (
                ", ".join(tire_change_times_str) if tire_change_times_str else "N/A"
            )

            # Format tire sequence
            tyre_sequence_str = " → ".join(tyre_sequence) if tyre_sequence else "N/A"

            f.write(
                f"| {driver_name} | {strategy} | {pit_laps_str} | {pit_times_str} | "
                f"{tire_change_times_str} | {tyre_sequence_str} |\n"
            )

        # Part 3: Start Performance Analysis
        if start_results:
            f.write("\n## 🚀 Start Performance Analysis\n\n")

            # Track information
            straight_data = get_start_straight_data()
            track_key = gp_name.lower().replace(" ", "")
            mappings = {
                "saudiarabia": "saudi_arabia",
                "unitedstates": "usa",
                "greatbritain": "britain",
                "abudhabi": "abudhabi",
            }
            track_key = mappings.get(track_key, track_key)

            if track_key in straight_data:
                track_info = straight_data[track_key]
                f.write("### 🏁 Track Characteristics\n\n")
                f.write(
                    f"- **Start Straight Length:** {track_info['straight_length']}m\n"
                )
                f.write(f"- **Complexity Level:** {track_info['complexity']}\n")
                f.write(f"- **Category:** {track_info['category']}\n\n")

            # Start performance table
            f.write("### 📊 Start Performance Rankings\n\n")
            f.write("| Pos | Driver | Grid | R-Value | Start Delta | Main Factors |\n")
            f.write("|-----|--------|------|----------|-------------|--------------|\n")

            # Sort by start delta
            start_sorted = sorted(
                start_results.items(), key=lambda x: x[1]["delta_time"]
            )
            for i, (driver_name, result) in enumerate(start_sorted, 1):
                grid_pos = result["grid_position"]
                r_value = result["r_value"]
                delta = result["delta_time"]
                breakdown = result["breakdown"]

                # Analyze main factors
                main_factors = []
                if breakdown and isinstance(breakdown, dict):
                    if breakdown.get("grid_penalty", 0) > 0.1:
                        main_factors.append(
                            f"Grid penalty {breakdown.get('grid_penalty', 0):.2f}s"
                        )
                    if abs(breakdown.get("reaction_acceleration", 0)) > 0.05:
                        reaction = breakdown.get("reaction_acceleration", 0)
                        sign = "+" if reaction > 0 else ""
                        main_factors.append(f"Reaction {sign}{reaction:.2f}s")

                    special_events = breakdown.get("special_events", [])
                    if special_events:
                        main_factors.extend(special_events)

                main_factors_str = (
                    ", ".join(main_factors) if main_factors else "Normal start"
                )

                f.write(
                    f"| {i} | {driver_name} | {grid_pos} | {r_value:.1f} | "
                    f"{delta:.3f}s | {main_factors_str} |\n"
                )

            # Start statistics
            all_deltas = [result["delta_time"] for result in start_results.values()]
            avg_delta = np.mean(all_deltas)
            std_delta = np.std(all_deltas)

            f.write("\n### 📈 Start Statistics\n\n")
            f.write(f"- **Average Start Delta:** {avg_delta:.3f}s\n")
            f.write(f"- **Standard Deviation:** {std_delta:.3f}s\n")
            f.write(f"- **Minimum Start Delta:** {min(all_deltas):.3f}s\n")
            f.write(f"- **Maximum Start Delta:** {max(all_deltas):.3f}s\n")

            # Special events
            all_events = []
            for result in start_results.values():
                breakdown = result.get("breakdown", {})
                if breakdown and isinstance(breakdown, dict):
                    all_events.extend(breakdown.get("special_events", []))

            if all_events:
                event_counts = {}
                for event in all_events:
                    event_counts[event] = event_counts.get(event, 0) + 1

                f.write("\n### ⚠️ Special Events\n\n")
                for event, count in event_counts.items():
                    f.write(f"- **{event}:** {count} occurrence(s)\n")

        # Charts section
        f.write("\n## 📊 Race Visualization\n\n")
        f.write("### 🏁 Position Progression\n\n")
        f.write(f"![Position Progression]({position_chart_rel})\n\n")
        f.write("### ⏱️ Lap Time Distribution\n\n")
        f.write(f"![Lap Time Scatter]({laptime_chart_rel})\n\n")

        # Footer
        f.write("---\n")
        f.write(f"*Report generated by F1 Race Simulation System*\n")
        f.write(
            f"*Simulation time: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}*\n"
        )

    print(f"Markdown report saved as: {markdown_file}")
    return markdown_file


if __name__ == "__main__":
    main()
