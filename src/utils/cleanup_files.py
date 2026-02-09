import os
import glob
import shutil

def cleanup_and_organize():
    """清理和整理文件"""

    # 创建文件夹
    os.makedirs("figs", exist_ok=True)
    os.makedirs("tables", exist_ok=True)

    # 移动CSV文件到tables文件夹
    csv_files = glob.glob("*.csv")
    for csv_file in csv_files:
        if not csv_file.startswith("f1_"):  # 保留原始的f1_相关文件
            target = os.path.join("tables", csv_file)
            shutil.move(csv_file, target)
            print(f"移动 {csv_file} 到 {target}")

    # 移动PNG文件到figs文件夹
    png_files = glob.glob("*.png")
    for png_file in png_files:
        target = os.path.join("figs", png_file)
        shutil.move(png_file, target)
        print(f"移动 {png_file} 到 {target}")

    print("文件整理完成!")

if __name__ == "__main__":
    cleanup_and_organize()