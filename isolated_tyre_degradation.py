import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

# 设置matplotlib字体和样式
plt.rcParams["font.family"] = ["SimHei", "DejaVu Sans"]
plt.rcParams["font.size"] = 12
plt.rcParams['axes.unicode_minus'] = False

def get_universal_tyre_params_with_cliff():
    """
    定义包含悬崖点参数的通用轮胎参数库。
    参数已根据Pirelli官方信息和F1公开数据进行了校准和优化。
    """
    return {
        'C1': {  # 硬胎: 衰减最慢，悬崖点最晚
            'a': 0.010, 'k1': 0.05, 'b': 0.035, 'k2': 0.010,
            # 修正: 悬崖点参数更贴近现实
            'cliff_lap': 45, 'cliff_magnitude': 0.025, 'cliff_steepness': 2.5,
            'color': '#666666', 'edge_color': '#444444'
        },
        'C2': {  # 中硬胎: 平衡的选择
            'a': 0.015, 'k1': 0.08, 'b': 0.050, 'k2': 0.015,
            'cliff_lap': 35, 'cliff_magnitude': 0.04, 'cliff_steepness': 2.5,
            'color': '#F9B516', 'edge_color': '#C18A00'
        },
        'C3': {  # 中性胎: 标准比赛轮胎
            'a': 0.025, 'k1': 0.10, 'b': 0.070, 'k2': 0.020,
            'cliff_lap': 28, 'cliff_magnitude': 0.06, 'cliff_steepness': 2.5,
            'color': '#00D2BE', 'edge_color': '#009A8C'
        },
        'C4': {  # 软胎: 衰减较快，性能好
            'a': 0.040, 'k1': 0.15, 'b': 0.090, 'k2': 0.030,
            'cliff_lap': 22, 'cliff_magnitude': 0.09, 'cliff_steepness': 2.5,
            'color': '#E61D2A', 'edge_color': '#B71520'
        },
        'C5': {  # 最软胎: 极快衰减，悬崖点早且严重
            'a': 0.065, 'k1': 0.20, 'b': 0.130, 'k2': 0.040,
            'cliff_lap': 15, 'cliff_magnitude': 0.15, 'cliff_steepness': 2.5,
            'color': '#3531FF', 'edge_color': '#2522CC'
        }
    }

def calculate_degradation_with_cliff(compound, num_laps):
    """
    计算包含悬崖点效应的轮胎衰减模型数据。
    """
    params = get_universal_tyre_params_with_cliff()[compound]
    a, k1, b, k2 = params['a'], params['k1'], params['b'], params['k2']
    cliff_lap, cliff_mag, cliff_stp = params['cliff_lap'], params['cliff_magnitude'], params['cliff_steepness']

    laps = np.arange(1, num_laps + 1)

    # 1. 计算基础衰减倍率 M_base(lap)
    M_base = 1 + a * (1 - np.exp(-k1 * laps)) + b * (1 - np.exp(-k2 * laps))

    # 2. 计算悬崖点效应 M_cliff(lap)
    sigmoid_values = 1 / (1 + np.exp(-cliff_stp * (laps - cliff_lap)))
    M_cliff = cliff_mag * sigmoid_values

    # 3. 计算最终累计衰减倍率
    final_multipliers = M_base + M_cliff

    # 4. 计算倍率变化速率
    rate_base = (a * k1 * np.exp(-k1 * laps)) + (b * k2 * np.exp(-k2 * laps))
    rate_cliff = cliff_mag * cliff_stp * sigmoid_values * (1 - sigmoid_values)
    final_rate_of_change_pct = (rate_base + rate_cliff) * 100

    return {
        'laps': laps,
        'multipliers': final_multipliers,
        'rate_of_change_pct': final_rate_of_change_pct,
        'M_base': M_base,
        'M_cliff': M_cliff
    }

def plot_tyre_analysis_with_cliff(all_results, base_lap_time, num_laps):
    """
    绘制包含悬崖点效应的轮胎衰减分析图。
    """
    fig, axs = plt.subplots(2, 2, figsize=(20, 12))
    fig.suptitle(f'F1轮胎长距离衰减分析 (含悬崖点, 基准圈速: {base_lap_time}秒)', fontsize=20, y=0.98)
    axs = axs.ravel()

    tyre_params = get_universal_tyre_params_with_cliff()
    tyre_colors = {c: p['color'] for c, p in tyre_params.items()}
    tyre_edge_colors = {c: p['edge_color'] for c, p in tyre_params.items()}

    # --- 图1: 左上 - 累计衰减倍率变化 ---
    ax1 = axs[0]
    for compound, results in all_results.items():
        ax1.plot(results['laps'], results['multipliers'],
                 label=compound, color=tyre_colors[compound], linewidth=2.5)
        cliff_lap = tyre_params[compound]['cliff_lap']
        ax1.axvline(x=cliff_lap, color=tyre_colors[compound], linestyle=':', alpha=0.4)

    ax1.axhline(y=1.0, color='grey', linestyle='--', linewidth=1, alpha=0.7)
    ax1.set_title('累计衰减倍率变化 (含悬崖点)', fontsize=16)
    ax1.set_xlabel('圈数', fontsize=14)
    ax1.set_ylabel('累计衰减倍率', fontsize=14)
    ax1.legend(fontsize=12)
    ax1.grid(True, linestyle=':', alpha=0.6)
    ax1.set_xlim(1, num_laps)
    ax1.set_ylim(1.0, None)

    # --- 图2: 右上 - 等效衰减量 ---
    ax2 = axs[1]
    for compound, results in all_results.items():
        time_loss = base_lap_time * (results['multipliers'] - 1)
        ax2.plot(results['laps'], time_loss,
                 label=compound, color=tyre_colors[compound], linewidth=2.5)

    ax2.set_title('等效衰减量 (基于基准圈速)', fontsize=16)
    ax2.set_xlabel('圈数', fontsize=14)
    ax2.set_ylabel('等效衰减量 (秒)', fontsize=14)
    ax2.legend(fontsize=12)
    ax2.grid(True, linestyle=':', alpha=0.6)
    ax2.set_xlim(1, num_laps)
    ax2.set_ylim(0, None)

    # --- 图3: 左下 - 倍率变化速率 ---
    ax3 = axs[2]
    for compound, results in all_results.items():
        ax3.plot(results['laps'], results['rate_of_change_pct'],
                 label=compound, color=tyre_colors[compound], linewidth=2.5)

    ax3.set_title('倍率变化速率 (悬崖点处出现峰值)', fontsize=16)
    ax3.set_xlabel('圈数', fontsize=14)
    ax3.set_ylabel('变化速率 (% / 圈)', fontsize=14)
    ax3.legend(fontsize=12)
    ax3.grid(True, linestyle=':', alpha=0.6)
    ax3.set_xlim(1, num_laps)
    ax3.set_ylim(0, None)

    # --- 图4: 右下 - 总倍率增长对比 ---
    ax4 = axs[3]
    compounds = sorted(all_results.keys())
    final_multipliers = [all_results[c]['multipliers'][-1] for c in compounds]
    colors = [tyre_colors[c] for c in compounds]
    edge_colors = [tyre_edge_colors[c] for c in compounds]

    bars = ax4.bar(compounds, final_multipliers, color=colors, edgecolor=edge_colors, linewidth=1.5)
    ax4.bar_label(bars, fmt='%.3f', padding=3, fontsize=12)

    ax4.set_title(f'{num_laps}圈后总倍率增长对比', fontsize=16)
    ax4.set_xlabel('轮胎配方', fontsize=14)
    ax4.set_ylabel('总衰减倍率', fontsize=14)
    ax4.grid(True, linestyle=':', alpha=0.6, axis='y')
    ax4.set_ylim(1.0, None)
    ax4.yaxis.set_major_formatter(mticker.FormatStrFormatter('%.3f'))

    plt.tight_layout(rect=[0, 0, 1, 0.96])
    output_filename = 'f1_tyre_degradation_with_cliff_analysis_calibrated.png'
    plt.savefig(output_filename, dpi=300, bbox_inches='tight')
    print(f"校准后的分析图表已生成: {output_filename}")
    plt.close()

def main():
    """主程序入口"""
    NUM_LAPS = 66
    BASE_LAP_TIME = 85.0
    COMPOUNDS_TO_SIMULATE = ['C1', 'C2', 'C3', 'C4', 'C5']

    print("--- F1轮胎乘法衰减模型模拟 (含悬崖点, 已校准) ---")
    print(f"模拟圈数: {NUM_LAPS} 圈")
    print(f"基准圈速: {BASE_LAP_TIME} 秒")
    print(f"模拟轮胎配方: {', '.join(COMPOUNDS_TO_SIMULATE)}")
    print("-" * 35)

    all_simulation_results = {}
    tyre_params_all = get_universal_tyre_params_with_cliff()

    for compound in COMPOUNDS_TO_SIMULATE:
        print(f"正在计算 {compound} 轮胎的衰减数据...")
        results = calculate_degradation_with_cliff(compound, NUM_LAPS)
        all_simulation_results[compound] = results

        final_multiplier = results['multipliers'][-1]
        total_time_loss = BASE_LAP_TIME * (final_multiplier - 1)
        cliff_lap = tyre_params_all[compound]['cliff_lap']

        print(f"  -> {compound} 在 {NUM_LAPS} 圈后，总衰减倍率为 {final_multiplier:.4f}，等效总损失 {total_time_loss:.2f} 秒")
        print(f"  -> 预计悬崖点在: 第 {cliff_lap} 圈附近")

    print("-" * 35)

    plot_tyre_analysis_with_cliff(all_simulation_results, BASE_LAP_TIME, NUM_LAPS)

if __name__ == "__main__":
    main()
