import pandas as pd
import numpy as np

# 2022赛季F1各站比赛的轮胎配方设定
# 数据来源：基于F1官方公布的轮胎配方信息
tyre_compounds_2022 = {
    "Race": [
        "Bahrain",
        "Saudi Arabia",
        "Australia",
        "Imola",
        "Miami",
        "Spain",
        "Monaco",
        "Azerbaijan",
        "Canada",
        "Great Britain",
        "Austria",
        "France",
        "Hungary",
        "Belgium",
        "Netherlands",
        "Italy",
        "Singapore",
        "Japan",
        "United States",
        "Mexico",
        "Brazil",
        "Abu Dhabi",
    ],
    "Hard_Compound": [
        "C1",
        "C2",
        "C2",
        "C2",
        "C2",
        "C1",
        "C3",
        "C2",
        "C2",
        "C1",
        "C3",
        "C2",
        "C2",
        "C2",
        "C1",
        "C2",
        "C3",
        "C1",
        "C2",
        "C2",
        "C2",
        "C2",
    ],
    "Medium_Compound": [
        "C2",
        "C3",
        "C3",
        "C3",
        "C3",
        "C2",
        "C4",
        "C3",
        "C3",
        "C2",
        "C4",
        "C3",
        "C3",
        "C3",
        "C2",
        "C3",
        "C4",
        "C2",
        "C3",
        "C3",
        "C3",
        "C3",
    ],
    "Soft_Compound": [
        "C3",
        "C4",
        "C4",
        "C4",
        "C4",
        "C3",
        "C5",
        "C4",
        "C4",
        "C3",
        "C5",
        "C4",
        "C4",
        "C4",
        "C3",
        "C4",
        "C5",
        "C3",
        "C4",
        "C4",
        "C4",
        "C4",
    ],
    "Date": [
        "2022-03-20",
        "2022-03-27",
        "2022-04-10",
        "2022-04-24",
        "2022-05-08",
        "2022-05-22",
        "2022-05-29",
        "2022-06-12",
        "2022-06-19",
        "2022-07-03",
        "2022-07-10",
        "2022-07-24",
        "2022-07-31",
        "2022-08-28",
        "2022-09-04",
        "2022-09-11",
        "2022-10-02",
        "2022-10-09",
        "2022-10-23",
        "2022-10-30",
        "2022-11-13",
        "2022-11-20",
    ],
}

# 创建DataFrame
df_tyre_compounds = pd.DataFrame(tyre_compounds_2022)

# 保存为CSV文件
csv_filename = "tables/f1_2022_tyre_compounds.csv"
df_tyre_compounds.to_csv(csv_filename, index=False, encoding="utf-8-sig")

print(f"2022赛季F1轮胎配方设定已保存到: {csv_filename}")
print("\n表格预览:")
print(df_tyre_compounds.head(10))

# 显示完整的表格信息
print("\n完整的2022赛季F1轮胎配方设定:")
print(df_tyre_compounds.to_string(index=False))

# 额外创建一个简化版本，只包含比赛名称和轮胎配方
simple_compounds = {
    "Race": tyre_compounds_2022["Race"],
    "Hard": tyre_compounds_2022["Hard_Compound"],
    "Medium": tyre_compounds_2022["Medium_Compound"],
    "Soft": tyre_compounds_2022["Soft_Compound"],
}

df_simple = pd.DataFrame(simple_compounds)
simple_csv_filename = "tables/f1_2022_tyre_compounds_simple.csv"
df_simple.to_csv(simple_csv_filename, index=False, encoding="utf-8-sig")

print(f"\n简化版轮胎配方设定已保存到: {simple_csv_filename}")
print("\n简化版表格预览:")
print(df_simple.to_string(index=False))
