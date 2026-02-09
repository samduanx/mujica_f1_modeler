import fastf1
from fastf1 import get_session
import pandas as pd
import numpy as np

# 启用FastF1缓存（推荐）
fastf1.Cache.enable_cache('outputs/f1_cache')  # 创建缓存目录
fastf1.set_log_level("ERROR")

def get_qualifying_fastest_lap(year, gp_name):
    """
    提取指定赛季和分站排位赛的最快圈速
    
    参数:
        year (int): 赛季年份
        gp_name (str): 分站名称 (如 'Spain')
    
    返回:
        float: 最快圈速（秒）
    """
    try:
        # 加载排位赛数据
        session = get_session(year, gp_name, 'Q')
        session.load()  # 加载所有数据
        
        # 获取所有车手的排位赛数据
        laps = session.laps
        
        # 筛选出排位赛的有效圈速（非进站圈、非虚拟圈）
        qualifying_laps = laps[(laps['IsPersonalBest'] == True) & 
                               (laps['PitOutTime'].isna()) & 
                               (laps['PitInTime'].isna())]
        
        # 找到最快圈速
        fastest_lap = qualifying_laps['LapTime'].min()
        
        # 转换为秒
        fastest_lap_seconds = fastest_lap.total_seconds()
        
        return fastest_lap_seconds
    
    except Exception as e:
        print(f"获取数据时出错: {e}")
        return None

# 提取2022赛季西班牙站排位赛最快圈速
year = 2022
gp_name = 'Miami'
fastest_lap = get_qualifying_fastest_lap(year, gp_name)

if fastest_lap is not None:
    print(f"2022赛季{gp_name}站排位赛最快圈速: {fastest_lap:.3f}")
    
    # 可选：显示所有车手的排位赛最快圈速
    session = get_session(year, gp_name, 'Q')
    session.load()
    laps = session.laps
    qualifying_laps = laps[(laps['IsPersonalBest'] == True) & 
                           (laps['PitOutTime'].isna()) & 
                           (laps['PitInTime'].isna())]
    
    # 按车手分组获取最快圈速
    driver_fastest_laps = qualifying_laps.groupby('Driver')['LapTime'].min()
    driver_fastest_laps = driver_fastest_laps.sort_values()
    
    print("\n所有车手排位赛最快圈速:")
    for driver, lap_time in driver_fastest_laps.items():
        driver_name = session.get_driver(driver).Abbreviation
        print(f"{driver_name}: {lap_time.total_seconds():.3f}")

else:
    print("未能获取数据")
