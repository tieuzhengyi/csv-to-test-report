import matplotlib.pyplot as plt
import matplotlib
matplotlib.use("Agg")

def generate_histogram(df, output_path):
    plt.figure()
    plt.hist(df["value"], bins=10)
    plt.xlabel("Value")
    plt.ylabel("Count")
    plt.title("Measurement Distribution")
    plt.savefig(output_path)
    plt.close()


def generate_scatter(df, output_path):
    plt.figure()
    plt.scatter(df["sample_id"], df["value"])
    plt.axhline(df["lower_limit"].iloc[0], linestyle="--")
    plt.axhline(df["upper_limit"].iloc[0], linestyle="--")
    plt.xticks(rotation=45)
    plt.title("Value vs Sample ID")
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()
