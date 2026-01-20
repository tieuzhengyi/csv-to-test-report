from validator import validate_csv

def evaluate(df):
    df["status"] = (
        (df["value"] >= df["lower_limit"]) &
        (df["value"] <= df["upper_limit"])
    )

    df["status"] = df["status"].map({True: "PASS", False: "FAIL"})

    summary = {
    "total": int(len(df)),
    "pass_count": int((df["status"] == "PASS").sum()),
    "fail_count": int((df["status"] == "FAIL").sum()),
}

    summary["pass_rate"] = float(
    round(summary["pass_count"] / summary["total"] * 100, 2)
    )

    summary["overall_verdict"] = (
        "PASS" if summary["fail_count"] == 0 else "FAIL"
    )

    return df, summary


