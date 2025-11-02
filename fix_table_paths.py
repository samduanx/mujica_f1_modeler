#!/usr/bin/env python3
"""
表格路径修复脚本 - 将所有CSV/XLSX文件引用指向tables/子文件夹
"""

import os
import re

def fix_file_paths(file_path, description=""):
    """修复单个文件中的表格路径"""
    print(f"\n🔧 修复 {description}: {file_path}")

    if not os.path.exists(file_path):
        print(f"⚠️  文件不存在: {file_path}")
        return False

    try:
        # 读取文件内容
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content

        # 修复CSV文件路径
        # 模式1: read_csv("filename.csv") -> read_csv("tables/filename.csv")
        content = re.sub(
            r'read_csv\(["\']([^"\']+\.csv)["\']\)',
            lambda m: f'read_csv("tables/{m.group(1)}")' if not m.group(1).startswith("tables/") else m.group(0),
            content
        )

        # 模式2: read_csv(filename.csv) -> read_csv("tables/filename.csv")
        content = re.sub(
            r'read_csv\(([^)]+\.csv[^)]*)\)',
            lambda m: f'read_csv("tables/" + {m.group(1).strip("\"\'")} + ")' if not m.group(1).strip().startswith('"tables/') else m.group(0),
            content
        )

        # 修复Excel文件路径
        # 模式1: "filename.xlsx" -> "tables/filename.xlsx"
        content = re.sub(
            r'excel_file\s*=\s*["\']([^"\']+\.xlsx)["\']',
            lambda m: f'excel_file = os.path.join("tables", "{m.group(1)}")' if not m.group(1).startswith("tables/") else m.group(0),
            content
        )

        # 修复输出文件路径 (CSV)
        # 模式: to_csv("filename.csv") -> to_csv("tables/filename.csv")
        content = re.sub(
            r'to_csv\(["\']([^"\']+\.csv)["\']\)',
            lambda m: f'to_csv("tables/{m.group(1)}")' if not m.group(1).startswith("tables/") else m.group(0),
            content
        )

        # 模式: output_file = "filename.csv" -> output_file = "tables/filename.csv"
        content = re.sub(
            r'output_file\s*=\s*["\']([^"\']+\.csv)["\']',
            lambda m: f'output_file = "tables/{m.group(1)}"' if not m.group(1).startswith("tables/") else m.group(0),
            content
        )

        # 检查是否有变化
        if content != original_content:
            # 写回文件
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ 已修复: {file_path}")
            return True
        else:
            print(f"ℹ️  无需修复: {file_path}")
            return False

    except Exception as e:
        print(f"❌ 修复失败 {file_path}: {e}")
        return False

def main():
    """主函数"""
    print("🔧 F1 表格路径修复工具")
    print("=" * 50)

    # 需要修复的文件列表
    files_to_fix = [
        ("mujica_f1_modeler/long_dist_sim_with_box.py", "主模拟文件"),
        ("mujica_f1_modeler/get_box_window.py", "进站分析文件"),
        ("mujica_f1_modeler/t_r_compare.py", "圈速对比文件"),
        ("mujica_f1_modeler/t_r_line.py", "线性圈速文件"),
        ("mujica_f1_modeler/t_r_nonlinear.py", "非线性圈速文件"),
        ("mujica_f1_modeler/align_tracks.py", "赛道对齐文件"),
        ("mujica_f1_modeler/tyre_types.py", "轮胎类型文件"),
    ]

    # 检查tables目录
    tables_dir = "mujica_f1_modeler/tables"
    if not os.path.exists(tables_dir):
        os.makedirs(tables_dir, exist_ok=True)
        print(f"📁 创建目录: {tables_dir}")

    # 修复各个文件
    fixed_count = 0
    total_count = len(files_to_fix)

    for file_path, description in files_to_fix:
        if fix_file_paths(file_path, description):
            fixed_count += 1

    # 总结
    print("\n" + "=" * 50)
    print(f"📊 修复总结: {fixed_count}/{total_count} 个文件已修复")

    if fixed_count > 0:
        print("\n✅ 修复内容:")
        print("  • CSV读取路径 -> tables/子文件夹")
        print("  • Excel读取路径 -> tables/子文件夹")
        print("  • CSV输出路径 -> tables/子文件夹")
        print("  • 文件引用路径标准化")

        print("\n🎯 影响的文件:")
        print("  • pitlane_time.csv")
        print("  • pit_stop_analysis_by_strategy_2022_2024.csv")
        print("  • Spain.csv")
        print("  • Spain.xlsx")
        print("  • track_characteristics.xlsx")
        print("  • 其他CSV/XLSX文件")

    print("\n🚀 使用说明:")
    print("  运行修复后，所有表格文件将:")
    print("  • 从 tables/ 目录读取")
    print("  • 写入到 tables/ 目录")
    print("  • 保持向后兼容性")

    return fixed_count > 0

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
