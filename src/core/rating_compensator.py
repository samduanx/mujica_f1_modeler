"""
R值隐藏补偿系统 - Rating Compensator

用于缩小前排车队一二号车手之间的成绩差距。
只补偿R值（用于圈速计算），不补偿DR（用于稳定性计算）和PR（用于轮胎衰竭计算）。
"""

from dataclasses import dataclass
from typing import Dict, Optional, Tuple
import json

# 车队层级配置
TEAM_TIERS = {
    "TOP": {
        "teams": {"red_bull", "ferrari", "mercedes", "mclaren", "aston_martin"},
        "max_compensation": 0.35,  # 最大补偿R值
        "compensation_factor": 0.5,  # 差距系数：差距 × 此系数 = 补偿量
    },
    "MID": {
        "teams": {"alpine", "williams"},
        "max_compensation": 0.25,
        "compensation_factor": 0.5,
    },
    "BACK": {
        "teams": {"alphatauri", "alfa_romeo", "haas"},
        "max_compensation": 0.15,
        "compensation_factor": 0.5,
    },
}

# 特殊车手处理
SPECIAL_DRIVER_CONFIG = {
    "TSUNODA": {
        "compensation_multiplier": 0.5,  # 角田裕毅补偿减半
        "reason": "二号车手特殊情况",
    }
}

# 补偿衰减配置
DECAY_CONFIG = {
    "leader_ratio_threshold": 0.92,  # 达到老大R的92%时开始衰减
    "r_improvement_threshold": 0.5,  # 每提升0.5R
    "r_improvement_decay_rate": 0.2,  # 减少20%补偿
}


@dataclass
class CompensationResult:
    """补偿计算结果"""

    original_r: float  # 原始R值
    compensated_r: float  # 补偿后的R值
    compensation_value: float  # 补偿量
    gap_to_leader: float  # 与老大的差距
    team_tier: str  # 车队层级
    decay_applied: bool  # 是否应用了衰减


def get_team_tier(team_id: str) -> str:
    """获取车队层级"""
    team_id_lower = team_id.lower()
    for tier, config in TEAM_TIERS.items():
        if team_id_lower in config["teams"]:
            return tier
    return "MID"  # 默认中游


def calculate_base_compensation(
    base_r: float, team_leader_r: float, team_tier: str, is_number_2_driver: bool
) -> Tuple[float, float]:
    """
    计算基础补偿量

    Returns:
        (compensation_value, gap_to_leader)
    """
    # 只有二号车手获得补偿
    if not is_number_2_driver:
        return 0.0, 0.0

    # 计算与老大的差距
    gap_to_leader = team_leader_r - base_r

    # 如果已经超过老大，不补偿
    if gap_to_leader <= 0:
        return 0.0, 0.0

    # 获取车队配置
    tier_config = TEAM_TIERS.get(team_tier, TEAM_TIERS["MID"])
    max_compensation = tier_config["max_compensation"]
    compensation_factor = tier_config["compensation_factor"]

    # 计算补偿量：差距 × 系数，不超过最大值
    compensation = min(gap_to_leader * compensation_factor, max_compensation)

    return max(0.0, compensation), gap_to_leader


def apply_decay(
    compensation: float,
    base_r: float,
    team_leader_r: float,
    base_r_previous: Optional[float] = None,
) -> Tuple[float, bool]:
    """
    应用衰减 - 仅在车手R值实际提升时衰减

    Returns:
        (decayed_compensation, decay_applied)
    """
    decay_applied = False

    # 只在提供了历史R值时才应用衰减
    # 这意味着补偿默认不会自动减少，除非车手实际提升了R
    if base_r_previous is not None:
        r_improvement = base_r - base_r_previous
        if r_improvement > 0:
            improvement_threshold = DECAY_CONFIG["r_improvement_threshold"]
            decay_rate = DECAY_CONFIG["r_improvement_decay_rate"]

            # 计算衰减次数
            decay_count = int(r_improvement / improvement_threshold)
            decay_multiplier = max(0.4, (1 - decay_rate) ** decay_count)

            compensation *= decay_multiplier
            decay_applied = True

    return max(0.0, compensation), decay_applied


def apply_special_driver_adjustment(compensation: float, driver_id: str) -> float:
    """应用特殊车手调整"""
    driver_id_upper = driver_id.upper()

    if driver_id_upper in SPECIAL_DRIVER_CONFIG:
        multiplier = SPECIAL_DRIVER_CONFIG[driver_id_upper]["compensation_multiplier"]
        return compensation * multiplier

    return compensation


def calculate_compensated_r(
    dr_value: float,
    pr_value: float,
    driver_id: str,
    team_id: str,
    is_number_2_driver: bool,
    team_leader_r: float,
    base_r_previous: Optional[float] = None,
) -> CompensationResult:
    """
    计算补偿后的R值（主函数）

    Args:
        dr_value: 车手DR值（保持原值，不补偿）
        pr_value: 车队PR值（保持原值，不补偿）
        driver_id: 车手ID
        team_id: 车队ID
        is_number_2_driver: 是否为二号车手
        team_leader_r: 车队一号车手R值
        base_r_previous: 上一次的基础R值（用于计算衰减）

    Returns:
        CompensationResult对象
    """
    # 计算基础R值
    base_r = dr_value * pr_value / 100.0

    # 获取车队层级
    team_tier = get_team_tier(team_id)

    # 计算基础补偿
    compensation, gap_to_leader = calculate_base_compensation(
        base_r=base_r,
        team_leader_r=team_leader_r,
        team_tier=team_tier,
        is_number_2_driver=is_number_2_driver,
    )

    # 应用衰减
    compensation, decay_applied = apply_decay(
        compensation=compensation,
        base_r=base_r,
        team_leader_r=team_leader_r,
        base_r_previous=base_r_previous,
    )

    # 应用特殊车手调整
    compensation = apply_special_driver_adjustment(compensation, driver_id)

    # 计算补偿后的R值
    compensated_r = base_r + compensation

    return CompensationResult(
        original_r=base_r,
        compensated_r=compensated_r,
        compensation_value=compensation,
        gap_to_leader=gap_to_leader,
        team_tier=team_tier,
        decay_applied=decay_applied,
    )


def get_team_leader_r(team_id: str, drivers_data: Dict) -> float:
    """
    从车手数据中获取车队一号车手的R值

    Args:
        team_id: 车队ID
        drivers_data: 车手数据字典，格式为 {driver_id: {dr: float, is_number_2: bool}}

    Returns:
        车队一号车手的R值
    """
    team_drivers = [
        (did, ddata)
        for did, ddata in drivers_data.items()
        if ddata.get("team") == team_id
    ]

    # 找出一号车手（is_number_2为False，或DR最高）
    leader = None
    max_r = 0.0

    for driver_id, data in team_drivers:
        dr = data.get("dr", 0.0)
        pr = data.get("pr", 300.0)
        r_value = dr * pr / 100.0

        if not data.get("is_number_2", False):
            # 明确标记为一号车手
            return r_value

        if r_value > max_r:
            max_r = r_value
            leader = driver_id

    return max_r if leader else 300.0


# 快捷函数，用于在模拟中直接调用
def get_effective_r_for_laptime(
    dr: float,
    pr: float,
    driver_id: str,
    team_id: str,
    is_number_2: bool,
    team_leader_r: float,
) -> float:
    """
    获取用于圈速计算的有效R值

    这是主要的对外接口函数，在圈速计算时调用
    """
    result = calculate_compensated_r(
        dr_value=dr,
        pr_value=pr,
        driver_id=driver_id,
        team_id=team_id,
        is_number_2_driver=is_number_2,
        team_leader_r=team_leader_r,
    )
    return result.compensated_r


if __name__ == "__main__":
    # 测试示例
    print("=== R值隐藏补偿系统测试 ===\n")

    # 示例1: 红牛车队
    print("1. 红牛车队示例:")
    print(f"   一号车手: VER, DR=100.5, PR=305")
    print(f"   二号车手: PER, DR=99.8, PR=305")

    # 计算车队老大R值
    ver_r = 100.5 * 305 / 100.0
    print(f"   维斯塔潘R值: {ver_r:.2f}")

    # 计算佩雷兹补偿
    result_per = calculate_compensated_r(
        dr_value=99.8,
        pr_value=305,
        driver_id="PER",
        team_id="red_bull",
        is_number_2_driver=True,
        team_leader_r=ver_r,
    )
    print(f"   佩雷兹原始R: {result_per.original_r:.2f}")
    print(f"   佩雷兹补偿R: {result_per.compensated_r:.2f}")
    print(f"   补偿量: {result_per.compensation_value:.2f}")
    print(f"   与老大差距: {result_per.gap_to_leader:.2f}")
    print(f"   补偿后差距: {ver_r - result_per.compensated_r:.2f}")
    print()

    # 示例2: Alpine车队（奥康）
    print("2. Alpine车队示例:")
    print(f"   一号车手: ALO, DR=100.5, PR=305")
    print(f"   二号车手: OCO, DR=99.7, PR=305")

    alo_r = 100.5 * 305 / 100.0
    print(f"   阿隆索R值: {alo_r:.2f}")

    result_oco = calculate_compensated_r(
        dr_value=99.7,
        pr_value=305,
        driver_id="OCO",
        team_id="alpine",
        is_number_2_driver=True,
        team_leader_r=alo_r,
    )
    print(f"   奥康原始R: {result_oco.original_r:.2f}")
    print(f"   奥康补偿R: {result_oco.compensated_r:.2f}")
    print(f"   补偿量: {result_oco.compensation_value:.2f}")
    print(f"   车队层级: {result_oco.team_tier}")
    print()

    # 示例3: 角田裕毅（特殊处理）
    print("3. 小红牛 - 角田裕毅（特殊处理）:")
    result_tsunoda = calculate_compensated_r(
        dr_value=99.75,
        pr_value=298,
        driver_id="TSUNODA",
        team_id="alphatauri",
        is_number_2_driver=True,
        team_leader_r=100.1 * 298 / 100.0,
    )
    print(f"   角田原始R: {result_tsunoda.original_r:.2f}")
    print(f"   角田补偿R: {result_tsunoda.compensated_r:.2f}")
    print(f"   补偿量: {result_tsunoda.compensation_value:.2f} (已减半)")
    print()

    print("=== 测试完成 ===")
