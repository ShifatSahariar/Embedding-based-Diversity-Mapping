import matplotlib.pyplot as plt
import numpy as np


def plot_ms_cc_bar(generators, ms_values, cc_values,
                   title="MS and CC per generator",
                   sort_by_ms=True,
                   figsize=(9, 5)):

    generators = np.array(generators)
    ms_values = np.array(ms_values, dtype=float)
    cc_values = np.array(cc_values, dtype=float)

    # Sort descending by MS
    if sort_by_ms:
        order = np.argsort(-ms_values)
        generators = generators[order]
        ms_values = ms_values[order]
        cc_values = cc_values[order]

    x = np.arange(len(generators))

    # Reduced bar width → smaller gap
    width = 0.40  # WIDER bars → less space between tool groups
    shift = width * 0.60  # MS–CC bars closer together

    bars_ms = plt.bar(x - shift / 2, ms_values, width, color='#FECD57', label='MS')
    bars_cc = plt.bar(x + shift / 2, cc_values, width, color='#46CEAD', label='CC')

    # Vertical text inside bars
    for bar in bars_ms:
        h = bar.get_height()
        plt.text(
            bar.get_x() + bar.get_width() / 2,
            h / 2,
            f"{h:.2f}",
            ha='center',
            va='center',
            fontsize=10,
            rotation=90,  # <<<<< vertical
            fontweight='bold'
        )

    for bar in bars_cc:
        h = bar.get_height()
        plt.text(
            bar.get_x() + bar.get_width() / 2,
            h / 2,
            f"{h:.2f}",
            ha='center',
            va='center',
            fontsize=10,
            rotation=90,  # <<<<< vertical
            fontweight='bold'
        )

    # Title + axis labels
    plt.title(title, fontsize=15, weight='bold')
    # plt.xlabel("Generators (sorted by MS)" if sort_by_ms else "Generators",
    #            fontsize=14)
    plt.ylabel("Value", fontsize=14)

    # Bigger generator names
    plt.xticks(x, generators, rotation=25, ha='right', fontsize=12,weight='bold',color='#434445')
    plt.yticks(fontsize=12, weight='bold')

    # Y limit
    plt.ylim(0, max(ms_values.max(), cc_values.max()) + 0.1)

    # Grid
    plt.grid(axis='y', linestyle='--', alpha=0.35)

    plt.legend(fontsize=12)
    plt.tight_layout()

    plt.savefig("graaljs_histogram.png", dpi=600,bbox_inches="tight", facecolor="white")
    plt.show()



# CALC _RUN _5
generators = [
    "opn_n_gr",
    "fzz_pr",
    "fzz_eq",
    "isl_n_cn",
    "isl_cn",
    "fan_cn",
    "fan_n_cn",
    "opn_gr",


]

ms_values =  [0.879762,
0.7746429,
0.7603572,
0.6686906,
0.5776191,
0.5709525,
0.5742859,
0.5344048]
cc_values =  [0.2729827806,
0.2611509336,
0.2439741169,
0.2184256848,
0.2038710251,
0.1419448097,
0.139219313,
0.2033375734]
plot_ms_cc_bar(generators, ms_values, cc_values,
               title="GRAALJS")
