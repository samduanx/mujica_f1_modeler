import fastf1
from fastf1 import get_session
import pandas as pd
import numpy as np
import os
from tqdm import tqdm
import warnings

warnings.filterwarnings("ignore")

# 启用FastF1缓存
fastf1.Cache.enable_cache("outputs/f1_cache")
fastf1.set_log_level("ERROR")

# 完整的2022-2024年F1分站映射表
TRACK_MAPPING = {
    "bahrain": "Bahrain International Circuit",
    "saudiarabia": "Jeddah Corniche Circuit",
    "australia": "Melbourne Grand Prix Circuit",
    "imola": "Autodromo Enzo e Dino Ferrari",
    "miami": "Miami International Autodrome",
    "spain": "Circuit de Barcelona-Catalunya",
    "monaco": "Circuit de Monaco",
    "azerbaijan": "Baku City Circuit",
    "canada": "Circuit Gilles-Villeneuve",
    "britain": "Silverstone Circuit",
    "austria": "Red Bull Ring",
    "france": "Circuit Paul Ricard",
    "hungary": "Hungaroring",
    "belgium": "Circuit de Spa-Francorchamps",
    "netherlands": "Circuit Zandvoort",
    "italy": "Monza Circuit",
    "singapore": "Marina Bay Street Circuit",
    "japan": "Suzuka Circuit",
    "usa": "Circuit of the Americas",
    "mexico": "Autodromo Hermanos Rodriguez",
    "brazil": "Interlagos Circuit",
    "abudhabi": "Yas Marina Circuit",
    "qatar": "Lusail International Circuit",
    "lasvegas": "Las Vegas Strip Circuit",
    "shanghai": "Shanghai International Circuit",
    "jeddah": "Jeddah Corniche Circuit",
    "melbourne": "Melbourne Grand Prix Circuit",
    "albert_park": "Melbourne Grand Prix Circuit",
    "paul_ricard": "Circuit Paul Ricard",
    "silverstone": "Silverstone Circuit",
    "red_bull_ring": "Red Bull Ring",
    "spa": "Circuit de Spa-Francorchamps",
    "zandvoort": "Circuit Zandvoort",
    "monza": "Monza Circuit",
    "marina_bay": "Marina Bay Street Circuit",
    "suzuka": "Suzuka Circuit",
    "cota": "Circuit of the Americas",
    "americas": "Circuit of the Americas",
    "rodriguez": "Autodromo Hermanos Rodriguez",
    "interlagos": "Interlagos Circuit",
    "yas_marina": "Yas Marina Circuit",
    "losail": "Lusail International Circuit",
}

# 各年份的实际分站列表
YEAR_TRACKS = {
    2022: [
        "bahrain",
        "saudiarabia",
        "australia",
        "imola",
        "miami",
        "spain",
        "monaco",
        "azerbaijan",
        "canada",
        "britain",
        "austria",
        "france",
        "hungary",
        "belgium",
        "netherlands",
        "italy",
        "singapore",
        "japan",
        "usa",
        "mexico",
        "brazil",
        "abudhabi",
    ],
    2023: [
        "bahrain",
        "saudiarabia",
        "australia",
        "azerbaijan",
        "miami",
        "spain",
        "monaco",
        "canada",
        "austria",
        "britain",
        "hungary",
        "belgium",
        "netherlands",
        "italy",
        "singapore",
        "japan",
        "qatar",
        "usa",
        "mexico",
        "brazil",
        "lasvegas",
        "abudhabi",
    ],
    2024: [
        "bahrain",
        "saudiarabia",
        "australia",
        "japan",
        "shanghai",
        "miami",
        "imola",
        "monaco",
        "canada",
        "spain",
        "austria",
        "britain",
        "hungary",
        "belgium",
        "netherlands",
        "italy",
        "azerbaijan",
        "singapore",
        "usa",
        "mexico",
        "brazil",
        "lasvegas",
        "qatar",
        "abudhabi",
    ],
}

# 赛道显示名称映射
TRACK_DISPLAY_NAMES = {
    "bahrain": "Bahrain",
    "saudiarabia": "Saudi Arabia",
    "australia": "Australia",
    "imola": "Emilia Romagna",
    "miami": "Miami",
    "spain": "Spain",
    "monaco": "Monaco",
    "azerbaijan": "Azerbaijan",
    "canada": "Canada",
    "britain": "Britain",
    "austria": "Austria",
    "france": "France",
    "hungary": "Hungary",
    "belgium": "Belgium",
    "netherlands": "Netherlands",
    "italy": "Italy",
    "singapore": "Singapore",
    "japan": "Japan",
    "usa": "USA",
    "mexico": "Mexico",
    "brazil": "Brazil",
    "abudhabi": "Abu Dhabi",
    "qatar": "Qatar",
    "lasvegas": "Las Vegas",
    "shanghai": "China",
}


def remove_outliers_iqr(data, multiplier=1.5):
    """使用IQR方法去除异常值"""
    if len(data) < 4:
        return data
    q1 = np.percentile(data, 25)
    q3 = np.percentile(data, 75)
    iqr = q3 - q1
    lower_bound = q1 - multiplier * iqr
    upper_bound = q3 + multiplier * iqr
    filtered_data = [x for x in data if lower_bound <= x <= upper_bound]
    return filtered_data


def try_get_session(year, track_key):
    """尝试获取比赛会话，处理各种可能的赛道名称"""
    try:
        session = get_session(year, track_key, "R")
        session.load()
        return session
    except Exception:
        pass

    for key, name in TRACK_MAPPING.items():
        if key == track_key:
            try:
                session = get_session(year, key, "R")
                session.load()
                return session
            except Exception:
                continue
    return None


def analyze_pit_stops_by_strategy():
    """按停站次数分析每条赛道的平均进站圈数"""
    years = [2022, 2023, 2024]

    # 存储所有赛道的进站数据，按停站次数分类
    # 结构: {track: {1: [lap_numbers], 2: [[lap1, lap2], ...], 3: [[lap1, lap2, lap3], ...], 4: [[lap1, lap2, lap3, lap4], ...], 5: [[lap1, lap2, lap3, lap4, lap5], ...]}}
    pit_stop_data = {
        track: {1: [], 2: [], 3: [], 4: [], 5: []}
        for track in set().union(*YEAR_TRACKS.values())
    }

    print("开始分析赛道进站数据（按策略分类）...")

    for year in tqdm(years, desc="分析年份"):
        tracks_for_year = YEAR_TRACKS.get(year, [])

        for track in tqdm(tracks_for_year, desc=f"分析{year}年赛道", leave=False):
            try:
                session = try_get_session(year, track)
                if session is None:
                    continue

                laps = session.laps
                pit_laps = laps[laps["PitInTime"].notna()]
                grouped = pit_laps.groupby("Driver")

                for driver, driver_pits in grouped:
                    driver_pits = driver_pits.sort_values("LapNumber")
                    stop_laps = driver_pits["LapNumber"].tolist()

                    # 过滤掉不合理的进站
                    stop_laps = [lap for lap in stop_laps if 2 <= lap <= 70]

                    num_stops = len(stop_laps)
                    if num_stops == 0:
                        continue

                    # 根据停站次数分类存储
                    if num_stops == 1:
                        pit_stop_data[track][1].append(stop_laps[0])
                    elif num_stops == 2:
                        pit_stop_data[track][2].append(stop_laps)
                    elif num_stops == 3:
                        pit_stop_data[track][3].append(stop_laps)
                    elif num_stops == 4:
                        pit_stop_data[track][4].append(stop_laps)
                    elif num_stops == 5:
                        pit_stop_data[track][5].append(stop_laps)

            except Exception as e:
                continue

    # 计算每条赛道的进站统计
    results = []

    for track in sorted(pit_stop_data.keys()):
        track_results = {
            "Track": TRACK_DISPLAY_NAMES.get(track, track),
            "Total_Races": sum(1 for y in years if track in YEAR_TRACKS.get(y, [])),
        }

        # 分析一停策略
        one_stop_laps = pit_stop_data[track][1]
        if one_stop_laps:
            filtered_one_stop = remove_outliers_iqr(one_stop_laps)
            track_results.update(
                {
                    "One_Stop_Count": len(one_stop_laps),
                    "One_Stop_Avg_Lap": round(np.mean(filtered_one_stop), 1)
                    if filtered_one_stop
                    else None,
                    "One_Stop_Median_Lap": round(np.median(filtered_one_stop), 1)
                    if filtered_one_stop
                    else None,
                    "One_Stop_Range": f"{min(filtered_one_stop)}-{max(filtered_one_stop)}"
                    if filtered_one_stop
                    else "N/A",
                }
            )
        else:
            track_results.update(
                {
                    "One_Stop_Count": 0,
                    "One_Stop_Avg_Lap": None,
                    "One_Stop_Median_Lap": None,
                    "One_Stop_Range": "N/A",
                }
            )

        # 分析两停策略
        two_stop_stints = pit_stop_data[track][2]
        if two_stop_stints:
            first_stops = [stops[0] for stops in two_stop_stints]
            second_stops = [stops[1] for stops in two_stop_stints]

            filtered_first = remove_outliers_iqr(first_stops)
            filtered_second = remove_outliers_iqr(second_stops)

            track_results.update(
                {
                    "Two_Stop_Count": len(two_stop_stints),
                    "Two_Stop_First_Avg": round(np.mean(filtered_first), 1)
                    if filtered_first
                    else None,
                    "Two_Stop_First_Median": round(np.median(filtered_first), 1)
                    if filtered_first
                    else None,
                    "Two_Stop_Second_Avg": round(np.mean(filtered_second), 1)
                    if filtered_second
                    else None,
                    "Two_Stop_Second_Median": round(np.median(filtered_second), 1)
                    if filtered_second
                    else None,
                }
            )
        else:
            track_results.update(
                {
                    "Two_Stop_Count": 0,
                    "Two_Stop_First_Avg": None,
                    "Two_Stop_First_Median": None,
                    "Two_Stop_Second_Avg": None,
                    "Two_Stop_Second_Median": None,
                }
            )

        # 分析三停策略
        three_stop_stints = pit_stop_data[track][3]
        if three_stop_stints:
            first_stops = [stops[0] for stops in three_stop_stints]
            second_stops = [stops[1] for stops in three_stop_stints]
            third_stops = [stops[2] for stops in three_stop_stints]

            filtered_first = remove_outliers_iqr(first_stops)
            filtered_second = remove_outliers_iqr(second_stops)
            filtered_third = remove_outliers_iqr(third_stops)

            track_results.update(
                {
                    "Three_Stop_Count": len(three_stop_stints),
                    "Three_Stop_First_Avg": round(np.mean(filtered_first), 1)
                    if filtered_first
                    else None,
                    "Three_Stop_First_Median": round(np.median(filtered_first), 1)
                    if filtered_first
                    else None,
                    "Three_Stop_Second_Avg": round(np.mean(filtered_second), 1)
                    if filtered_second
                    else None,
                    "Three_Stop_Second_Median": round(np.median(filtered_second), 1)
                    if filtered_second
                    else None,
                    "Three_Stop_Third_Avg": round(np.mean(filtered_third), 1)
                    if filtered_third
                    else None,
                    "Three_Stop_Third_Median": round(np.median(filtered_third), 1)
                    if filtered_third
                    else None,
                }
            )
        else:
            track_results.update(
                {
                    "Three_Stop_Count": 0,
                    "Three_Stop_First_Avg": None,
                    "Three_Stop_First_Median": None,
                    "Three_Stop_Second_Avg": None,
                    "Three_Stop_Second_Median": None,
                    "Three_Stop_Third_Avg": None,
                    "Three_Stop_Third_Median": None,
                }
            )

        # 分析四停策略
        four_stop_stints = pit_stop_data[track][4]
        if four_stop_stints:
            first_stops = [stops[0] for stops in four_stop_stints]
            second_stops = [stops[1] for stops in four_stop_stints]
            third_stops = [stops[2] for stops in four_stop_stints]
            fourth_stops = [stops[3] for stops in four_stop_stints]

            filtered_first = remove_outliers_iqr(first_stops)
            filtered_second = remove_outliers_iqr(second_stops)
            filtered_third = remove_outliers_iqr(third_stops)
            filtered_fourth = remove_outliers_iqr(fourth_stops)

            track_results.update(
                {
                    "Four_Stop_Count": len(four_stop_stints),
                    "Four_Stop_First_Avg": round(np.mean(filtered_first), 1)
                    if filtered_first
                    else None,
                    "Four_Stop_First_Median": round(np.median(filtered_first), 1)
                    if filtered_first
                    else None,
                    "Four_Stop_Second_Avg": round(np.mean(filtered_second), 1)
                    if filtered_second
                    else None,
                    "Four_Stop_Second_Median": round(np.median(filtered_second), 1)
                    if filtered_second
                    else None,
                    "Four_Stop_Third_Avg": round(np.mean(filtered_third), 1)
                    if filtered_third
                    else None,
                    "Four_Stop_Third_Median": round(np.median(filtered_third), 1)
                    if filtered_third
                    else None,
                    "Four_Stop_Fourth_Avg": round(np.mean(filtered_fourth), 1)
                    if filtered_fourth
                    else None,
                    "Four_Stop_Fourth_Median": round(np.median(filtered_fourth), 1)
                    if filtered_fourth
                    else None,
                }
            )
        else:
            track_results.update(
                {
                    "Four_Stop_Count": 0,
                    "Four_Stop_First_Avg": None,
                    "Four_Stop_First_Median": None,
                    "Four_Stop_Second_Avg": None,
                    "Four_Stop_Second_Median": None,
                    "Four_Stop_Third_Avg": None,
                    "Four_Stop_Third_Median": None,
                    "Four_Stop_Fourth_Avg": None,
                    "Four_Stop_Fourth_Median": None,
                }
            )

        # 分析五停策略
        five_stop_stints = pit_stop_data[track][5]
        if five_stop_stints:
            first_stops = [stops[0] for stops in five_stop_stints]
            second_stops = [stops[1] for stops in five_stop_stints]
            third_stops = [stops[2] for stops in five_stop_stints]
            fourth_stops = [stops[3] for stops in five_stop_stints]
            fifth_stops = [stops[4] for stops in five_stop_stints]

            filtered_first = remove_outliers_iqr(first_stops)
            filtered_second = remove_outliers_iqr(second_stops)
            filtered_third = remove_outliers_iqr(third_stops)
            filtered_fourth = remove_outliers_iqr(fourth_stops)
            filtered_fifth = remove_outliers_iqr(fifth_stops)

            track_results.update(
                {
                    "Five_Stop_Count": len(five_stop_stints),
                    "Five_Stop_First_Avg": round(np.mean(filtered_first), 1)
                    if filtered_first
                    else None,
                    "Five_Stop_First_Median": round(np.median(filtered_first), 1)
                    if filtered_first
                    else None,
                    "Five_Stop_Second_Avg": round(np.mean(filtered_second), 1)
                    if filtered_second
                    else None,
                    "Five_Stop_Second_Median": round(np.median(filtered_second), 1)
                    if filtered_second
                    else None,
                    "Five_Stop_Third_Avg": round(np.mean(filtered_third), 1)
                    if filtered_third
                    else None,
                    "Five_Stop_Third_Median": round(np.median(filtered_third), 1)
                    if filtered_third
                    else None,
                    "Five_Stop_Fourth_Avg": round(np.mean(filtered_fourth), 1)
                    if filtered_fourth
                    else None,
                    "Five_Stop_Fourth_Median": round(np.median(filtered_fourth), 1)
                    if filtered_fourth
                    else None,
                    "Five_Stop_Fifth_Avg": round(np.mean(filtered_fifth), 1)
                    if filtered_fifth
                    else None,
                    "Five_Stop_Fifth_Median": round(np.median(filtered_fifth), 1)
                    if filtered_fifth
                    else None,
                }
            )
        else:
            track_results.update(
                {
                    "Five_Stop_Count": 0,
                    "Five_Stop_First_Avg": None,
                    "Five_Stop_First_Median": None,
                    "Five_Stop_Second_Avg": None,
                    "Five_Stop_Second_Median": None,
                    "Five_Stop_Third_Avg": None,
                    "Five_Stop_Third_Median": None,
                    "Five_Stop_Fourth_Avg": None,
                    "Five_Stop_Fourth_Median": None,
                    "Five_Stop_Fifth_Avg": None,
                    "Five_Stop_Fifth_Median": None,
                }
            )

        results.append(track_results)

    # 创建DataFrame并保存为CSV
    df = pd.DataFrame(results)
    df = df.sort_values("Track")

    output_file = "outputs/tables/pit_stop_analysis_by_strategy_2022_2024.csv"
    df.to_csv(output_file, index=False)
    print(f"\n进站策略分析完成，结果已保存到 {output_file}")

    # 打印结果摘要
    print("\n赛道进站策略分析摘要:")
    # 选择关键列进行显示，使输出更清晰
    display_cols = [
        "Track",
        "One_Stop_Count",
        "One_Stop_Avg_Lap",
        "Two_Stop_Count",
        "Two_Stop_First_Avg",
        "Two_Stop_Second_Avg",
        "Three_Stop_Count",
        "Three_Stop_First_Avg",
        "Three_Stop_Second_Avg",
        "Three_Stop_Third_Avg",
        "Four_Stop_Count",
        "Five_Stop_Count",
    ]
    print(df[display_cols].to_string(index=False))

    return df


if __name__ == "__main__":
    analyze_pit_stops_by_strategy()
