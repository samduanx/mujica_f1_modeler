import os
import csv
import json
import pandas as pd
import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
reports = os.path.join(ROOT, "outputs", "reports")
folders = [d for d in os.listdir(reports) if d.startswith("monte_carlo_weekend_")]
if not folders:
    raise SystemExit("No monte_carlo_weekend_* reports found")
folders.sort()
latest = folders[-1]
report_dir = os.path.join(reports, latest)

p = os.path.join(report_dir, "rating_position_distribution.csv")
b = os.path.join(report_dir, "rating_bucket_summary.csv")
if not os.path.exists(p):
    raise SystemExit(f"{p} not found")

# load per-driver table
df = pd.read_csv(p)
# normalize columns
if "rating" in df.columns:
    df["rating"] = pd.to_numeric(df["rating"], errors="coerce")
if "mean_position" in df.columns:
    df["mean_position"] = pd.to_numeric(df["mean_position"], errors="coerce")
if "top3_pct" in df.columns:
    df["top3_pct_num"] = df["top3_pct"].str.replace("%", "").astype(float) / 100.0
else:
    df["top3_pct_num"] = 0.0

# Filter rows with rating
df_valid = df.dropna(subset=["rating", "mean_position"])

# compute correlations
pearson_mean = df_valid["rating"].corr(df_valid["mean_position"], method="pearson")
spearman_mean = df_valid["rating"].corr(df_valid["mean_position"], method="spearman")
pearson_top3 = df_valid["rating"].corr(df_valid["top3_pct_num"], method="pearson")
spearman_top3 = df_valid["rating"].corr(df_valid["top3_pct_num"], method="spearman")

results = {
    "pearson_rating_mean_position": pearson_mean,
    "spearman_rating_mean_position": spearman_mean,
    "pearson_rating_top3": pearson_top3,
    "spearman_rating_top3": spearman_top3,
}

with open(
    os.path.join(report_dir, "rating_correlation_summary.json"), "w", encoding="utf-8"
) as f:
    json.dump(results, f, indent=2)

print(
    "Correlations saved to", os.path.join(report_dir, "rating_correlation_summary.json")
)

# Plot 1: Rating vs Mean Position (scatter + linear fit)
plt.figure(figsize=(6, 4))
plt.scatter(df_valid["rating"], df_valid["mean_position"], s=60, alpha=0.8)
# linear fit
m, b = np.polyfit(df_valid["rating"], df_valid["mean_position"], 1)
xs = np.linspace(df_valid["rating"].min(), df_valid["rating"].max(), 100)
plt.plot(xs, m * xs + b, color="red", lw=1)
plt.xlabel("Rating (DR)")
plt.ylabel("Mean Position")
plt.title(
    f"Rating vs Mean Position\nPearson={pearson_mean:.3f}, Spearman={spearman_mean:.3f}"
)
plt.grid(alpha=0.2)
out1 = os.path.join(report_dir, "plot_rating_vs_mean_position.png")
plt.tight_layout()
plt.savefig(out1, dpi=150)
plt.close()

# Plot 2: Rating vs Top3 % (scatter + fit)
plt.figure(figsize=(6, 4))
plt.scatter(df_valid["rating"], df_valid["top3_pct_num"] * 100, s=60, alpha=0.8)
# linear fit
m2, b2 = np.polyfit(df_valid["rating"], df_valid["top3_pct_num"] * 100, 1)
plt.plot(xs, m2 * xs + b2, color="red", lw=1)
plt.xlabel("Rating (DR)")
plt.ylabel("Top 3 %")
plt.title(f"Rating vs Top3%\nPearson={pearson_top3:.3f}, Spearman={spearman_top3:.3f}")
plt.grid(alpha=0.2)
out2 = os.path.join(report_dir, "plot_rating_vs_top3_pct.png")
plt.tight_layout()
plt.savefig(out2, dpi=150)
plt.close()

# Plot 3: Bucket summary bar chart
if os.path.exists(b):
    bdf = pd.read_csv(b)
    # parse top3_pct
    if "top3_pct" in bdf.columns:
        bdf["top3_pct_num"] = bdf["top3_pct"].str.replace("%", "").astype(float)
    else:
        bdf["top3_pct_num"] = 0.0
    plt.figure(figsize=(6, 4))
    plt.bar(bdf["bucket"], bdf["top3_pct_num"], color="C0", alpha=0.8)
    plt.xlabel("Rating Bucket")
    plt.ylabel("Top3 % (bucket total races)")
    plt.title("Top3% by Rating Bucket")
    for i, v in enumerate(bdf["top3_pct_num"]):
        plt.text(i, v + 0.2, f"{v:.2f}%", ha="center")
    out3 = os.path.join(report_dir, "plot_bucket_top3_pct.png")
    plt.tight_layout()
    plt.savefig(out3, dpi=150)
    plt.close()
    print("Wrote bucket plot to", out3)

print("Wrote plots:", out1, out2)
print("Done")
