import matplotlib.pyplot as plt

def plot_auc_clean(budgets, ms_spreadex, ms_random, auc_sp, auc_rn, title):

    plt.figure(figsize=(5,4))  # square compact plot

    # Line width + smaller markers for compact look
    plt.plot(budgets, ms_spreadex, '-o', color='#1f77b4', linewidth=2, markersize=8,
             label=f"SpreadEx (nAUC={auc_sp:.3f})")
    plt.plot(budgets, ms_random, '-o', color='#ff7f0e', linewidth=2, markersize=8,
             label=f"Random (nAUC={auc_rn:.3f})")
    # leg = plt.legend(fontsize=11, framealpha=0.9)
    #
    # for text in leg.get_texts():
    #     text.set_fontweight('bold')

    plt.xticks(fontsize=12, weight='bold')
    plt.yticks(fontsize=12, weight='bold')

    # Title + labels
    plt.title(title, fontsize=13, weight='bold')
    plt.xlabel("Budget", fontsize=12)
    plt.ylabel("Mean Mutation Score", fontsize=12)

    # Ticks
    plt.xticks(fontsize=11)
    plt.yticks(fontsize=11)

    # Grid
    plt.grid(alpha=0.25, linestyle='--')

    # Keep limits tight
    plt.ylim(0, 1.05)

    # Legend inside plot to save space
    plt.legend(fontsize=10, loc='lower right', framealpha=0.9)

    plt.tight_layout(pad=0.2)  # minimal padding
    plt.savefig("auc_graaljs.png", bbox_inches='tight', dpi=300)
    plt.show()

budgets = [5, 10, 15, 20, 25, 30, 35, 40, 45, 50,55,60,65,70,75,80,85,90,95,100]
ms_random=[
0.4430333,
0.5799667,
0.6486666,
0.6905332,
0.7307667,
0.7567667,
0.7768999,
0.7931,
0.8047667,
0.8164,
0.8237,
0.8334333,
0.8418334,
0.8487667,
0.8535666,
0.8596,
0.8658667,
0.8698,
0.8746333,
0.8771666
]
ms_spreadex = [
0.4733333,
0.65,
0.7116667,
0.7116667,
0.745,
0.7983332,
0.8483333,
0.8483333,
0.8483333,
0.8683333,
0.8683333,
0.8683333,
0.8933333,
0.8933333,
0.8933333,
0.8933333,
0.8933333,
0.8933333,
0.8933333,
0.8933333
]
auc_sp = 0.78516664
auc_rn = 0.7464583225

plot_auc_clean(
    budgets,
    ms_spreadex,
    ms_random,
    auc_sp,
    auc_rn,
    title="GRAALJS — MS vs Budget"
)

