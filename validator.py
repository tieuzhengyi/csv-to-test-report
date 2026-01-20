import pandas as pd

REQUIRED_COLUMNS = {
    "sample_id",
    "test_name",
    "value",
    "lower_limit",
    "upper_limit"
}

def validate_csv(path):
    df = pd.read_csv(path)

    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    for col in ["value", "lower_limit", "upper_limit"]:
        if not pd.api.types.is_numeric_dtype(df[col]):
            raise ValueError(f"Column '{col}' must be numeric")

    return df
