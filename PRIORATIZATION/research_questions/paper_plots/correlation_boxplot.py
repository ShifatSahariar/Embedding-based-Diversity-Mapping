import seaborn as sns
import matplotlib.pyplot as plt
import pandas as pd

# correlation matrix extracted from the table
data = {
    "CALC":     [0.150,	-0.340	,0.386,	0.302	,0.387],
    "BASIC":    [0.425	,0.375,	0.364,	0.455,	0.445],
    "KARATEJS": [0.793	,0.599,	0.705	,0.701	,0.803],
    "RHINO":    [0.344,	0.528	,0.423,	0.367	,0.456],
    "NASHORN":  [0.259	,0.454	,0.299	,0.235,	0.329],
    "GRAALJS":  [0.673	,0.530	,0.732	,0.702	,0.629]
}

# Define model names + colors
index = ["CodeSTRAL", "GraphCodeBERT", "OpenAI", "Qwen3", "UniXCoder"]

flat_colors = [
    "#00cec9",  # teal
    "#fdcb6e",  # sand-yellow
    "#00b894",  # green
    "#fab1a0",  # peach
    "#badc58"   # light green
]

FLATSAND = "#4f4f4f"   # light sand border
FLATWHITE = "#FBFAF5"   # paper-like white

df = pd.DataFrame(data, index=index)

# Melt for seaborn
df_melt = df.reset_index().melt(id_vars="index", var_name="SUT", value_name="Correlation")

# Figure
plt.figure(figsize=(7.5, 3.6))

# Boxplot (cleaner + thinner + flat sand borders)
sns.boxplot(
    data=df_melt,
    x="index",
    y="Correlation",
    hue="index",
    palette=flat_colors,
    width=0.25,                 # narrower boxes
    linewidth=1.4,
    boxprops=dict(edgecolor=FLATSAND),
    medianprops=dict(color=FLATSAND, linewidth=1.2),
    whiskerprops=dict(color=FLATSAND),
    capprops=dict(color=FLATSAND),
    fliersize=0,
    dodge=False,
    legend=False
)

# Swarmplot with lighter, smaller points
sns.swarmplot(
    data=df_melt,
    x="index",
    y="Correlation",
    hue="index",
    palette=["black"]*5,
    size=3,
    alpha=0.75,
    dodge=False,
    legend=False
)

# Reference zero line
plt.axhline(0, ls='--', lw=1.1, c='red', alpha=0.5)

# Labels
plt.xlabel("Embedding Model", fontsize=12, weight='bold')
plt.ylabel("Spearman's Correlation", fontsize=12, weight='bold')

plt.xticks(rotation=18, fontsize=11, weight='bold')
plt.yticks(fontsize=11)

plt.ylim(-0.28, 0.85)

# Light grid
plt.grid(axis='y', linestyle='--', alpha=0.25)

plt.tight_layout()

plt.savefig("correlation_boxplot_clean.pdf", bbox_inches="tight")
plt.savefig("correlation_boxplot_clean.png", dpi=600, bbox_inches="tight")

plt.show()
