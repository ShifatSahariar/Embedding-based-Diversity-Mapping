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


index = ["CodeSTRAL", "GraphCodeBERT", "OpenAI", "Qwen3", "UniXCoder"]
df = pd.DataFrame(data, index=index)

# Create a larger figure with better aspect ratio
plt.figure(figsize=(12, 4.5))  # Increased size for better visibility

# Create heatmap
sns.heatmap(
    df,
    annot=True,
    cmap="Oranges",
    center=0,          # symmetric around zero
    vmin=-0.3,
    vmax=0.8,
    linewidths=0.3,
    linecolor='white',
    annot_kws={"size": 16, "weight": "bold"},
    cbar_kws={'label': 'Correlation Coefficient'}  # Add label to colorbar
)

# Set titles and labels
# plt.title("Correlation of CC- MS per SUT", fontsize=15, pad=20,weight='bold')
# plt.xlabel("Subject Programs (SUTs)", fontsize=14, labelpad=10)
# plt.ylabel("Embedding Models", fontsize=14, labelpad=10)

# Adjust tick parameters for better visibility
plt.xticks(rotation=0, fontsize=13,weight='bold')
plt.yticks(rotation=0, fontsize=13,weight='bold')

# Ensure tight layout
plt.tight_layout()

# Alternative: Save to file to see full image
plt.savefig('correlation_heatmap.pdf', bbox_inches='tight')

plt.show()