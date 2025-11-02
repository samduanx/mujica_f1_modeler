import pandas as pd
import fastf1
from thefuzz import process
import warnings
import os

# 忽略FastF1的警告
warnings.filterwarnings("ignore")

# --- 修复点 1: 提供离线后备数据，防止网络失败导致程序崩溃 ---
FALLBACK_EVENTS = {
    "Sakhir": {"EventName": "Bahrain Grand Prix", "Year": 2022},
    "Jeddah": {"EventName": "Saudi Arabian Grand Prix", "Year": 2022},
    "Melbourne": {"EventName": "Australian Grand Prix", "Year": 2022},
    "Imola": {"EventName": "Emilia Romagna Grand Prix", "Year": 2022},
    "Miami": {"EventName": "Miami Grand Prix", "Year": 2022},
    "Barcelona": {"EventName": "Spanish Grand Prix", "Year": 2022},
    "Monte Carlo": {"EventName": "Monaco Grand Prix", "Year": 2022},
    "Baku": {"EventName": "Azerbaijan Grand Prix", "Year": 2022},
    "Montreal": {"EventName": "Canadian Grand Prix", "Year": 2022},
    "Silverstone": {"EventName": "British Grand Prix", "Year": 2022},
    "Spielberg": {"EventName": "Austrian Grand Prix", "Year": 2022},
    "Paul Ricard": {"EventName": "French Grand Prix", "Year": 2022},
    "Budapest": {"EventName": "Hungarian Grand Prix", "Year": 2022},
    "Spa": {"EventName": "Belgian Grand Prix", "Year": 2022},
    "Zandvoort": {"EventName": "Dutch Grand Prix", "Year": 2022},
    "Monza": {"EventName": "Italian Grand Prix", "Year": 2022},
    "Singapore": {"EventName": "Singapore Grand Prix", "Year": 2022},
    "Suzuka": {"EventName": "Japanese Grand Prix", "Year": 2022},
    "Austin": {"EventName": "United States Grand Prix", "Year": 2022},
    "Mexico City": {"EventName": "Mexico City Grand Prix", "Year": 2022},
    "São Paulo": {"EventName": "São Paulo Grand Prix", "Year": 2022},
    "Yas Marina": {"EventName": "Abu Dhabi Grand Prix", "Year": 2022},
    "Shanghai": {"EventName": "Chinese Grand Prix", "Year": 2024},  # 使用2024年数据
}


def get_fastf1_events():
    """
    获取F1赛事信息。如果网络失败，则使用离线后备数据。
    """
    all_events = {}
    years_to_check = [2022, 2024, 2025]
    network_success = False

    print("正在尝试从FastF1获取赛事信息...")
    for year in years_to_check:
        try:
            # 启用缓存，避免重复下载
            cache_dir = os.path.join(os.path.dirname(__file__), "f1_cache")
            fastf1.Cache.enable_cache(cache_dir)

            schedule = fastf1.get_event_schedule(year, include_testing=False)
            for _, event in schedule.iterrows():
                location = event["LocationName"]
                if location and location not in all_events:
                    all_events[location] = {
                        "EventName": event["EventName"],
                        "Year": year,
                    }
            network_success = True
            break  # 只要有一年成功，就不再尝试其他年份
        except Exception as e:
            print(f"  -> 获取 {year} 年赛程失败: {e}")
            print("  -> 这可能是由于网络连接问题。")

    if not network_success or not all_events:
        print("\n警告：无法从网络获取FastF1赛事数据。将使用内置的后备数据集。")
        print("后备数据可能不完整或不是最新的。\n")
        return FALLBACK_EVENTS

    print("  -> 成功从网络获取数据！")
    return all_events


def align_track_names(excel_file_path):
    """
    将Excel中的赛道名称与FastF1的官方名称对齐。
    """
    if not os.path.exists(excel_file_path):
        print(f"错误：找不到Excel文件 '{excel_file_path}'。请检查文件路径。")
        return None

    df = pd.read_excel(excel_file_path)
    fastf1_events = get_fastf1_events()
    fastf1_track_names = list(fastf1_events.keys())

    # --- 修复点 2: 检查赛道名称列表是否为空 ---
    if not fastf1_track_names:
        print("错误：无法获取任何FastF1赛道名称。程序将退出。")
        return None

    print("\n可用的FastF1赛道名称:")
    for name in sorted(fastf1_track_names):
        print(f"  - {name}")

    # --- 修复点 3: 更新特殊映射，使其与FastF1的LocationName一致 ---
    special_mapping = {
        "abudhabi": "Yas Marina",
        "australia": "Melbourne",
        "austria": "Spielberg",
        "azerbaijan": "Baku",
        "bahrain": "Sakhir",
        "british": "Silverstone",
        "canada": "Montreal",
        "china": "Shanghai",
        "dutch": "Zandvoort",
        "french": "Paul Ricard",
        "hungary": "Budapest",
        "imola": "Imola",
        "italy": "Monza",
        "japanese": "Suzuka",
        "mexico": "Mexico City",
        "miami": "Miami",
        "monaco": "Monte Carlo",
        "saudi": "Jeddah",
        "singapore": "Singapore",
        "spain": "Barcelona",
        "us": "Austin",
        "brazil": "São Paulo",
        "belgian": "Spa",
    }

    aligned_df = df.copy()
    aligned_df["fastf1_location"] = None
    aligned_df["fastf1_eventname"] = None
    aligned_df["source_year"] = None

    print("\n开始对齐赛道名称...")
    for index, row in df.iterrows():
        excel_track = row["track"].lower()

        matched_name = None
        if excel_track in special_mapping:
            candidate_name = special_mapping[excel_track]
            if candidate_name in fastf1_events:
                matched_name = candidate_name
                print(
                    f"  [特殊映射] '{row['track']}' -> '{matched_name}' (来自 {fastf1_events[matched_name]['Year']} 年)"
                )

        # 如果特殊映射失败，则进行模糊匹配
        if not matched_name:
            # --- 修复点 4: 安全地处理 extractOne 的返回值 ---
            best_match_result = process.extractOne(
                excel_track, fastf1_track_names, score_cutoff=80
            )
            if best_match_result:
                best_match, score = best_match_result
                matched_name = best_match
                print(
                    f"  [模糊匹配] '{row['track']}' -> '{matched_name}' (置信度: {score}%, 来自 {fastf1_events[matched_name]['Year']} 年)"
                )
            else:
                print(f"  [匹配失败] '{row['track']}'")

        # 如果找到了匹配，更新DataFrame
        if matched_name:
            aligned_df.at[index, "fastf1_location"] = matched_name
            aligned_df.at[index, "fastf1_eventname"] = fastf1_events[matched_name][
                "EventName"
            ]
            aligned_df.at[index, "source_year"] = fastf1_events[matched_name]["Year"]

    output_csv = "tables/aligned_track_characteristics.csv"
    aligned_df.to_csv(output_csv, index=False)
    print(f"\n对齐完成！结果已保存到: {output_csv}")

    return aligned_df


if __name__ == "__main__":
    excel_file = "tables/track_characteristics.xlsx"
    aligned_data = align_track_names(excel_file)

    if aligned_data is not None:
        print("\n--- 对齐结果摘要 ---")
        print(aligned_data[["track", "fastf1_location", "source_year"]].to_string())
