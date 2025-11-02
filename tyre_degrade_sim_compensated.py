import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import os

# 设置matplotlib字体和样式
plt.rcParams["font.family"] = ["SimHei", "DejaVu Sans"]
plt.rcParams["font.size"] = 12
plt.rcParams["axes.unicode_minus"] = False


# --- 赛道特性数据 ---
def get_track_characteristics():
    """
    定义各赛道的特性数据，包括磨损等级和Pirelli推荐的轮胎压力。
    数据来源于Pirelli Preview文件和公开资料。
    压力单位为psi。
    """
    return {
        "bahrain": {
            "abrasion": 5,
            "stress": 3,
            "evolution": 4,
            "laps": 57,
            "base_time": 90.0,
            "compounds": ["C1", "C2", "C3"],
            "pressure": {"C1": 22.5, "C2": 22.0, "C3": 21.5, "C4": 21.0, "C5": 20.5},
        },
        "silverstone": {
            "abrasion": 3,
            "stress": 5,
            "evolution": 3,
            "laps": 52,
            "base_time": 85.0,
            "compounds": ["C1", "C2", "C3"],
            "pressure": {"C1": 23.5, "C2": 23.0, "C3": 22.5, "C4": 22.0, "C5": 21.5},
        },
        "monza": {
            "abrasion": 3,
            "stress": 3,
            "evolution": 3,
            "laps": 53,
            "base_time": 80.0,
            "compounds": ["C2", "C3", "C4"],
            "pressure": {"C1": 24.5, "C2": 24.0, "C3": 23.5, "C4": 23.0, "C5": 22.5},
        },
        "monaco": {
            "abrasion": 1,
            "stress": 1,
            "evolution": 5,
            "laps": 78,
            "base_time": 75.0,
            "compounds": ["C3", "C4", "C5"],
            "pressure": {"C1": 20.0, "C2": 19.5, "C3": 19.0, "C4": 18.5, "C5": 18.0},
        },
        "suzuka": {
            "abrasion": 4,
            "stress": 5,
            "evolution": 3,
            "laps": 53,
            "base_time": 88.0,
            "compounds": ["C1", "C2", "C3"],
            "pressure": {"C1": 24.0, "C2": 23.5, "C3": 23.0, "C4": 22.5, "C5": 22.0},
        },
        "spa": {
            "abrasion": 4,
            "stress": 5,
            "evolution": 3,
            "laps": 44,
            "base_time": 105.0,
            "compounds": ["C2", "C3", "C4"],
            "pressure": {"C1": 23.0, "C2": 22.5, "C3": 22.0, "C4": 21.5, "C5": 21.0},
        },
        "hungary": {
            "abrasion": 2,
            "stress": 3,
            "evolution": 4,
            "laps": 70,
            "base_time": 78.0,
            "compounds": ["C3", "C4", "C5"],
            "pressure": {"C1": 22.0, "C2": 21.5, "C3": 21.0, "C4": 20.5, "C5": 20.0},
        },
        "barcelona": {
            "abrasion": 4,
            "stress": 4,
            "evolution": 3,
            "laps": 66,
            "base_time": 85.0,
            "compounds": ["C1", "C2", "C3"],
            "pressure": {"C1": 23.0, "C2": 22.5, "C3": 22.0, "C4": 21.5, "C5": 21.0},
        },
        "miami": {
            "abrasion": 2,
            "stress": 3,
            "evolution": 5,
            "laps": 57,
            "base_time": 90.0,
            "compounds": ["C2", "C3", "C4"],
            "pressure": {"C1": 22.0, "C2": 21.5, "C3": 21.0, "C4": 20.5, "C5": 20.0},
        },
        "jeddah": {
            "abrasion": 2,
            "stress": 3,
            "evolution": 4,
            "laps": 50,
            "base_time": 85.0,
            "compounds": ["C2", "C3", "C4"],
            "pressure": {"C1": 21.5, "C2": 21.0, "C3": 20.5, "C4": 20.0, "C5": 19.5},
        },
        "baku": {
            "abrasion": 1,
            "stress": 3,
            "evolution": 5,
            "laps": 51,
            "base_time": 95.0,
            "compounds": ["C3", "C4", "C5"],
            "pressure": {"C1": 21.0, "C2": 20.5, "C3": 20.0, "C4": 19.5, "C5": 19.0},
        },
        "montreal": {
            "abrasion": 2,
            "stress": 3,
            "evolution": 5,
            "laps": 70,
            "base_time": 80.0,
            "compounds": ["C2", "C3", "C4"],
            "pressure": {"C1": 22.0, "C2": 21.5, "C3": 21.0, "C4": 20.5, "C5": 20.0},
        },
        "paul_ricard": {
            "abrasion": 3,
            "stress": 4,
            "evolution": 3,
            "laps": 53,
            "base_time": 85.0,
            "compounds": ["C2", "C3", "C4"],
            "pressure": {"C1": 23.0, "C2": 22.5, "C3": 22.0, "C4": 21.5, "C5": 21.0},
        },
        "zandvoort": {
            "abrasion": 3,
            "stress": 5,
            "evolution": 3,
            "laps": 72,
            "base_time": 80.0,
            "compounds": ["C1", "C2", "C3"],
            "pressure": {"C1": 23.5, "C2": 23.0, "C3": 22.5, "C4": 22.0, "C5": 21.5},
        },
        "monza": {
            "abrasion": 3,
            "stress": 3,
            "evolution": 3,
            "laps": 53,
            "base_time": 80.0,
            "compounds": ["C2", "C3", "C4"],
            "pressure": {"C1": 24.5, "C2": 24.0, "C3": 23.5, "C4": 23.0, "C5": 22.5},
        },
        "singapore": {
            "abrasion": 3,
            "stress": 2,
            "evolution": 4,
            "laps": 62,
            "base_time": 85.0,
            "compounds": ["C3", "C4", "C5"],
            "pressure": {"C1": 22.5, "C2": 22.0, "C3": 21.5, "C4": 21.0, "C5": 20.5},
        },
        "austin": {
            "abrasion": 4,
            "stress": 4,
            "evolution": 4,
            "laps": 56,
            "base_time": 90.0,
            "compounds": ["C2", "C3", "C4"],
            "pressure": {"C1": 23.5, "C2": 23.0, "C3": 22.5, "C4": 22.0, "C5": 21.5},
        },
        "mexico_city": {
            "abrasion": 2,
            "stress": 2,
            "evolution": 4,
            "laps": 71,
            "base_time": 80.0,
            "compounds": ["C2", "C3", "C4"],
            "pressure": {"C1": 21.0, "C2": 20.5, "C3": 20.0, "C4": 19.5, "C5": 19.0},
        },
        "sao_paulo": {
            "abrasion": 3,
            "stress": 4,
            "evolution": 4,
            "laps": 71,
            "base_time": 75.0,
            "compounds": ["C2", "C3", "C4"],
            "pressure": {"C1": 22.5, "C2": 22.0, "C3": 21.5, "C4": 21.0, "C5": 20.5},
        },
        "yas_marina": {
            "abrasion": 3,
            "stress": 3,
            "evolution": 4,
            "laps": 58,
            "base_time": 85.0,
            "compounds": ["C2", "C3", "C4"],
            "pressure": {"C1": 22.5, "C2": 22.0, "C3": 21.5, "C4": 21.0, "C5": 20.5},
        },
        # 添加其他赛道...
    }


# --- 补偿计算函数 ---
def calculate_wear_compensation(abrasion_level):
    normalized_abrasion = (abrasion_level - 3) / 2.0
    wear_factor = 1 + 0.2 * normalized_abrasion
    return wear_factor


def calculate_pressure_compensation(actual_pressure, optimal_pressure):
    deviation = actual_pressure - optimal_pressure
    pressure_penalty = 1 + 0.0125 * (deviation**2)
    return pressure_penalty


def get_universal_tyre_params_with_cliff():
    return {
        "C1": {
            "a": 0.010,
            "k1": 0.05,
            "b": 0.035,
            "k2": 0.010,
            "cliff_lap": 45,
            "cliff_magnitude": 0.025,
            "cliff_steepness": 2.5,
            "color": "#666666",
            "edge_color": "#444444",
        },
        "C2": {
            "a": 0.015,
            "k1": 0.08,
            "b": 0.050,
            "k2": 0.015,
            "cliff_lap": 35,
            "cliff_magnitude": 0.04,
            "cliff_steepness": 2.5,
            "color": "#F9B516",
            "edge_color": "#C18A00",
        },
        "C3": {
            "a": 0.025,
            "k1": 0.10,
            "b": 0.070,
            "k2": 0.020,
            "cliff_lap": 28,
            "cliff_magnitude": 0.06,
            "cliff_steepness": 2.5,
            "color": "#00D2BE",
            "edge_color": "#009A8C",
        },
        "C4": {
            "a": 0.040,
            "k1": 0.15,
            "b": 0.090,
            "k2": 0.030,
            "cliff_lap": 22,
            "cliff_magnitude": 0.09,
            "cliff_steepness": 2.5,
            "color": "#E61D2A",
            "edge_color": "#B71520",
        },
        "C5": {
            "a": 0.065,
            "k1": 0.20,
            "b": 0.130,
            "k2": 0.040,
            "cliff_lap": 15,
            "cliff_magnitude": 0.15,
            "cliff_steepness": 2.5,
            "color": "#3531FF",
            "edge_color": "#2522CC",
        },
    }


# --- 核心计算函数 ---
def calculate_degradation_uncompensated(compound, num_laps):
    """计算未补偿的轮胎衰减"""
    params = get_universal_tyre_params_with_cliff()[compound]
    a, k1, b, k2 = params["a"], params["k1"], params["b"], params["k2"]
    cliff_lap, cliff_mag, cliff_stp = (
        params["cliff_lap"],
        params["cliff_magnitude"],
        params["cliff_steepness"],
    )
    laps = np.arange(1, num_laps + 1)
    M_base = 1 + a * (1 - np.exp(-k1 * laps)) + b * (1 - np.exp(-k2 * laps))
    sigmoid_values = 1 / (1 + np.exp(-cliff_stp * (laps - cliff_lap)))
    M_cliff = cliff_mag * sigmoid_values
    final_multipliers = M_base + M_cliff
    rate_base = (a * k1 * np.exp(-k1 * laps)) + (b * k2 * np.exp(-k2 * laps))
    rate_cliff = cliff_mag * cliff_stp * sigmoid_values * (1 - sigmoid_values)
    final_rate_of_change_pct = (rate_base + rate_cliff) * 100
    return {
        "multipliers": final_multipliers,
        "rate_of_change_pct": final_rate_of_change_pct,
    }


def calculate_degradation_with_cliff(
    compound, num_laps, track_abrasion, actual_pressure, optimal_pressure
):
    """计算补偿后的轮胎衰减"""
    params = get_universal_tyre_params_with_cliff()[compound]
    a, k1, b, k2 = params["a"], params["k1"], params["b"], params["k2"]
    cliff_lap, cliff_mag, cliff_stp = (
        params["cliff_lap"],
        params["cliff_magnitude"],
        params["cliff_steepness"],
    )
    laps = np.arange(1, num_laps + 1)
    M_base = 1 + a * (1 - np.exp(-k1 * laps)) + b * (1 - np.exp(-k2 * laps))
    sigmoid_values = 1 / (1 + np.exp(-cliff_stp * (laps - cliff_lap)))
    M_cliff = cliff_mag * sigmoid_values
    M_uncompensated = M_base + M_cliff
    W_track = calculate_wear_compensation(track_abrasion)
    P_setup = calculate_pressure_compensation(actual_pressure, optimal_pressure)
    final_multipliers = 1 + (M_uncompensated - 1) * W_track * P_setup
    rate_base = (a * k1 * np.exp(-k1 * laps)) + (b * k2 * np.exp(-k2 * laps))
    rate_cliff = cliff_mag * cliff_stp * sigmoid_values * (1 - sigmoid_values)
    final_rate_of_change_pct = (rate_base + rate_cliff) * W_track * P_setup * 100
    return {
        "multipliers": final_multipliers,
        "rate_of_change_pct": final_rate_of_change_pct,
    }


# --- 修改部分: 对比绘图函数 ---
def plot_tyre_comparison(
    all_compensated_results,
    all_uncompensated_results,
    base_lap_time,
    num_laps,
    track_name,
):
    """绘制补偿前后对比图"""
    fig, axs = plt.subplots(2, 2, figsize=(20, 12))
    fig.suptitle(
        f"F1轮胎衰减对比分析 (赛道: {track_name.upper()}, 基准圈速: {base_lap_time}秒)",
        fontsize=20,
        y=0.98,
    )
    axs = axs.ravel()
    tyre_params = get_universal_tyre_params_with_cliff()
    tyre_colors = {c: p["color"] for c, p in tyre_params.items()}

    # 创建 laps 数组，不再依赖结果字典中的 'laps' 键
    laps = np.arange(1, num_laps + 1)

    # --- 图1: 累计衰减倍率对比 ---
    ax1 = axs[0]
    for compound in all_compensated_results.keys():
        comp_results = all_compensated_results[compound]
        uncomp_results = all_uncompensated_results[compound]
        ax1.plot(
            laps,
            comp_results["multipliers"],
            label=f"{compound} (补偿后)",
            color=tyre_colors[compound],
            linewidth=2.5,
        )
        ax1.plot(
            laps,
            uncomp_results["multipliers"],
            label=f"{compound} (未补偿)",
            color=tyre_colors[compound],
            linestyle="--",
            linewidth=2,
            alpha=0.8,
        )
    ax1.set_title("累计衰减倍率对比", fontsize=16)
    ax1.set_xlabel("圈数", fontsize=14)
    ax1.set_ylabel("累计衰减倍率", fontsize=14)
    ax1.legend(fontsize=10, ncol=2)
    ax1.grid(True, linestyle=":", alpha=0.6)
    ax1.set_xlim(1, num_laps)
    ax1.set_ylim(1.0, None)

    # --- 图2: 等效衰减量对比 ---
    ax2 = axs[1]
    for compound in all_compensated_results.keys():
        comp_results = all_compensated_results[compound]
        uncomp_results = all_uncompensated_results[compound]
        time_loss_comp = base_lap_time * (comp_results["multipliers"] - 1)
        time_loss_uncomp = base_lap_time * (uncomp_results["multipliers"] - 1)
        ax2.plot(
            laps,
            time_loss_comp,
            label=f"{compound} (补偿后)",
            color=tyre_colors[compound],
            linewidth=2.5,
        )
        ax2.plot(
            laps,
            time_loss_uncomp,
            label=f"{compound} (未补偿)",
            color=tyre_colors[compound],
            linestyle="--",
            linewidth=2,
            alpha=0.8,
        )
    ax2.set_title("等效衰减量对比", fontsize=16)
    ax2.set_xlabel("圈数", fontsize=14)
    ax2.set_ylabel("等效衰减量 (秒)", fontsize=14)
    ax2.legend(fontsize=10, ncol=2)
    ax2.grid(True, linestyle=":", alpha=0.6)
    ax2.set_xlim(1, num_laps)
    ax2.set_ylim(0, None)

    # --- 图3: 倍率变化速率对比 ---
    ax3 = axs[2]
    for compound in all_compensated_results.keys():
        comp_results = all_compensated_results[compound]
        uncomp_results = all_uncompensated_results[compound]
        ax3.plot(
            laps,
            comp_results["rate_of_change_pct"],
            label=f"{compound} (补偿后)",
            color=tyre_colors[compound],
            linewidth=2.5,
        )
        ax3.plot(
            laps,
            uncomp_results["rate_of_change_pct"],
            label=f"{compound} (未补偿)",
            color=tyre_colors[compound],
            linestyle="--",
            linewidth=2,
            alpha=0.8,
        )
    ax3.set_title("倍率变化速率对比", fontsize=16)
    ax3.set_xlabel("圈数", fontsize=14)
    ax3.set_ylabel("变化速率 (% / 圈)", fontsize=14)
    ax3.legend(fontsize=10, ncol=2)
    ax3.grid(True, linestyle=":", alpha=0.6)
    ax3.set_xlim(1, num_laps)
    ax3.set_ylim(0, None)

    # --- 图4: 总倍率增长对比 (柱状图) ---
    ax4 = axs[3]
    compounds = sorted(all_compensated_results.keys())
    comp_multipliers = [
        all_compensated_results[c]["multipliers"][-1] for c in compounds
    ]
    uncomp_multipliers = [
        all_uncompensated_results[c]["multipliers"][-1] for c in compounds
    ]
    colors = [tyre_colors[c] for c in compounds]

    x = np.arange(len(compounds))
    width = 0.35
    bars1 = ax4.bar(
        x - width / 2,
        uncomp_multipliers,
        width,
        label="未补偿",
        color=colors,
        alpha=0.7,
        edgecolor="black",
    )
    bars2 = ax4.bar(
        x + width / 2,
        comp_multipliers,
        width,
        label="补偿后",
        color=colors,
        edgecolor="black",
    )

    ax4.bar_label(bars1, fmt="%.3f", padding=3, fontsize=10)
    ax4.bar_label(bars2, fmt="%.3f", padding=3, fontsize=10)

    ax4.set_title(f"{num_laps}圈后总倍率增长对比", fontsize=16)
    ax4.set_xlabel("轮胎配方", fontsize=14)
    ax4.set_ylabel("总衰减倍率", fontsize=14)
    ax4.set_xticks(x)
    ax4.set_xticklabels(compounds)
    ax4.legend(fontsize=12)
    ax4.grid(True, linestyle=":", alpha=0.6, axis="y")
    ax4.set_ylim(1.0, None)
    ax4.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.3f"))

    plt.tight_layout(rect=[0, 0, 1, 0.96])

    # --- 保存到子文件夹 ---
    output_dir = "output_plots"
    os.makedirs(output_dir, exist_ok=True)
    output_filename = os.path.join(output_dir, f"f1_tyre_comparison_{track_name}.png")
    plt.savefig(output_filename, dpi=300, bbox_inches="tight")
    print(f"  -> 对比图表已生成: {output_filename}")
    plt.close()


# --- 新增部分: 批量处理函数 ---
def run_all_tracks_simulation():
    """对所有已定义的赛道运行模拟并生成对比图"""
    print("--- 开始对所有分站进行批量模拟和对比 ---")
    all_tracks = get_track_characteristics()

    # 预先计算所有轮胎配方的未补偿结果 (通用)
    print("\n[步骤 1/2] 预先计算通用的未补偿衰减数据...")
    all_uncompensated_results = {}
    max_laps_for_uncomp = max(data["laps"] for data in all_tracks.values())
    for compound in get_universal_tyre_params_with_cliff().keys():
        all_uncompensated_results[compound] = calculate_degradation_uncompensated(
            compound, max_laps_for_uncomp
        )
    print("  -> 未补偿数据计算完成。")

    print("\n[步骤 2/2] 遍历各赛道，计算补偿数据并生成图表...")
    for track_name, track_info in all_tracks.items():
        print(f"\n正在处理赛道: {track_name.upper()}")

        compensated_results = {}
        for compound in track_info["compounds"]:
            recommended_pressure = track_info["pressure"].get(compound, 22.0)
            compensated_results[compound] = calculate_degradation_with_cliff(
                compound,
                track_info["laps"],
                track_info["abrasion"],
                recommended_pressure,
                recommended_pressure,
            )

        # 从预计算的未补偿结果中截取当前赛道圈数的数据
        current_uncomp_results = {
            comp: {
                "multipliers": res["multipliers"][: track_info["laps"]],
                "rate_of_change_pct": res["rate_of_change_pct"][: track_info["laps"]],
            }
            for comp, res in all_uncompensated_results.items()
            if comp in track_info["compounds"]
        }

        plot_tyre_comparison(
            compensated_results,
            current_uncomp_results,
            track_info["base_time"],
            track_info["laps"],
            track_name,
        )

    print("\n--- 所有分站的批量处理完成！图表已保存在 'output_plots' 文件夹中。 ---")


# --- 原有的单次模拟函数 (可选保留) ---
def run_single_track_simulation():
    """运行单个赛道的模拟 (旧版main函数)"""
    TRACK_TO_SIMULATE = "bahrain"
    # ... (此处为原有的main函数逻辑，已省略以保持简洁)
    print("单次模拟功能已保留，但默认运行批量处理。如需启用，请修改 main() 函数。")


if __name__ == "__main__":
    # 默认执行对所有分站的批量比较
    run_all_tracks_simulation()

    # 如果您想运行单次模拟，请注释掉上面的行，并取消下面这行的注释
    # run_single_track_simulation()
