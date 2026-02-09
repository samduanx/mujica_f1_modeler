import fastf1
from fastf1 import get_session
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import FuncFormatter

plt.rcParams['font.family'] = ['monospace', 'Sarasa Term SC Nerd Font']
plt.rcParams['font.size'] = 20

# 启用FastF1缓存
fastf1.Cache.enable_cache('outputs/f1_cache')
fastf1.set_log_level("ERROR")

def get_qualifying_fastest_lap(year, gp_name):
    """提取指定赛季和分站排位赛的最快圈速"""
    try:
        session = get_session(year, gp_name, 'Q')
        session.load()
        laps = session.laps
        
        # 筛选排位赛有效圈速
        qualifying_laps = laps[(laps['IsPersonalBest'] == True) & 
                               (laps['PitOutTime'].isna()) & 
                               (laps['PitInTime'].isna())]
        
        fastest_lap = qualifying_laps['LapTime'].min()
        return fastest_lap.total_seconds()
    except Exception as e:
        print(f"获取数据时出错: {e}")
        return None

# 提取2022赛季迈阿密站排位赛最快圈速
year = 2022
gp_name = 'Miami'
fastest_lap_seconds = get_qualifying_fastest_lap(year, gp_name)

if fastest_lap_seconds is None:
    print("未能获取基准圈速数据")
    exit()

print(f"2022赛季{gp_name}站排位赛最快圈速: {fastest_lap_seconds:.3f}秒")

# 迈阿密站车手R值数据 (RO列)
driver_r_values = {
    'LEC': 301.3004,      # 勒克莱尔
    'VER': 301.2864375,   # 维斯塔潘
    'HAM': 300.6478,      # 汉密尔顿
    'SAI': 299.7999,      # 塞恩斯
    'PER': 299.4877125,   # 佩雷兹
    'RUS': 299.300275,    # 拉塞尔
    'GAS': 291.466175,    # 加斯利
    'TSU': 290.59265,     # 角田裕毅
    'ALO': 289.615875,    # 阿隆索
    'VET': 289.3655,      # 维特尔
    'OCO': 287.7427375,   # 奥康
    'STR': 287.49025,     # 斯特罗尔
    'BOT': 286.935225,    # 博塔斯
    'ZHO': 285.21705,     # 周冠宇
    'NOR': 285.209925,    # 诺里斯
    'RIC': 284.4976125,   # 皮亚斯特里, 但标签只有大牙
    'MAG': 283.33305,     # 马格努森
    'MSC': 282.059325,    # 米克
    'ALB': 280.33005,     # 阿尔本
    'LAT': 278.9298       # 拉提菲
}

# 计算R最大值
r_max = max(driver_r_values.values())
print(f"最大R值: {r_max:.3f}")

# 获取实际排位赛数据
session = get_session(year, gp_name, 'Q')
session.load()
laps = session.laps

# 筛选排位赛有效圈速
qualifying_laps = laps[(laps['IsPersonalBest'] == True) & 
                       (laps['PitOutTime'].isna()) & 
                       (laps['PitInTime'].isna())]

# 按车手分组获取最快圈速
driver_fastest_laps = qualifying_laps.groupby('Driver')['LapTime'].min()

# 创建结果DataFrame
results = []
ratio = 0.35

for driver_code, r_value in driver_r_values.items():
    # 计算模拟圈速
    simulated_lap = fastest_lap_seconds * (1 + ratio * (1 - r_value / r_max))
    
    # 获取实际圈速
    if driver_code in driver_fastest_laps:
        actual_lap = driver_fastest_laps[driver_code].total_seconds()
    else:
        actual_lap = np.nan
    
    # 获取车手姓名
    driver_name = session.get_driver(driver_code).Abbreviation
    
    results.append({
        'Driver': driver_name,
        'DriverCode': driver_code,
        'R_Value': r_value,
        'Actual_Lap': actual_lap,
        'Simulated_Lap': simulated_lap,
        'Difference': actual_lap - simulated_lap if not np.isnan(actual_lap) else np.nan
    })

# 转换为DataFrame
df = pd.DataFrame(results)

# 按模拟圈速排序
df = df.sort_values('Simulated_Lap')

# 打印结果表格
print("\n车手圈速对比结果:")
print(df.to_string(index=False, float_format="%.3f"))

# 创建图表
plt.figure(figsize=(16, 10))

# 子图1: R值和模拟圈速对比
ax1 = plt.subplot(2, 1, 1)
ax2 = ax1.twinx()

# 条形图宽度
bar_width = 0.35
x = np.arange(len(df))

# R值条形图
bars1 = ax1.bar(x - bar_width/2, df['R_Value'], bar_width, 
                color='skyblue', label='R值')

# 模拟圈速条形图
bars2 = ax2.bar(x + bar_width/2, df['Simulated_Lap'], bar_width, 
                color='salmon', label='模拟圈速')

# 设置轴标签和标题
ax1.set_xlabel('车手')
ax1.set_ylabel('R值', color='skyblue')
ax2.set_ylabel('模拟圈速 (秒)', color='salmon')
plt.title('车手R值与模拟圈速对比 (迈阿密站)')
ax1.set_xticks(x)
ax1.set_xticklabels(df['Driver'], rotation=45, ha='right')

# 添加图例
lines1, labels1 = ax1.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper right')

# 添加数值标签
for bar in bars1:
    height = bar.get_height()
    ax1.text(bar.get_x() + bar.get_width()/2., height,
             f'{height:.1f}', ha='center', va='bottom', fontsize=14)

for bar in bars2:
    height = bar.get_height()
    ax2.text(bar.get_x() + bar.get_width()/2., height,
             f'{height:.3f}', ha='center', va='bottom', fontsize=14)

# 子图2: 实际圈速与模拟圈速对比
plt.subplot(2, 1, 2)
plt.scatter(df['Simulated_Lap'], df['Actual_Lap'], color='blue', alpha=0.7)

# 添加理想线 (y=x)
min_val = min(df['Simulated_Lap'].min(), df['Actual_Lap'].min())
max_val = max(df['Simulated_Lap'].max(), df['Actual_Lap'].max())
plt.plot([min_val, max_val], [min_val, max_val], 'r--', alpha=0.5, label='理想线 (y=x)')

# 添加车手标签
for i, row in df.iterrows():
    if not np.isnan(row['Actual_Lap']):
        plt.annotate(row['Driver'], 
                    (row['Simulated_Lap'], row['Actual_Lap']),
                    textcoords="offset points", xytext=(5,5), ha='left', fontsize=14)

# 设置轴标签和标题
plt.xlabel('模拟圈速 (秒)')
plt.ylabel('实际圈速 (秒)')
plt.title('实际圈速 vs 模拟圈速 (迈阿密站)')
plt.legend()
plt.grid(True, alpha=0.3)

# 调整布局
plt.tight_layout()

# 显示图表
plt.show()

# 计算并打印统计信息
print("\n统计信息:")
print(f"平均差异: {df['Difference'].mean():.3f}秒")
print(f"最大差异: {df['Difference'].abs().max():.3f}秒")
print(f"最小差异: {df['Difference'].abs().min():.3f}秒")
print(f"差异标准差: {df['Difference'].std():.3f}秒")

# 找出最接近和最偏离理想的车手
closest = df.loc[df['Difference'].abs().idxmin()]
furthest = df.loc[df['Difference'].abs().idxmax()]

print(f"\n最接近理想的车手: {closest['Driver']} (差异: {closest['Difference']:.3f}秒)")
print(f"最偏离理想的车手: {furthest['Driver']} (差异: {furthest['Difference']:.3f}秒)")
