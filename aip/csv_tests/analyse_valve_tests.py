from pathlib import Path
import pandas as pd

# ============================================================
# SETTINGS
# ============================================================

# Folder containing this script and the valve CSV files
FOLDER = Path(__file__).resolve().parent

# Output summary file
OUTPUT_FILE = FOLDER / "valve_test_summary.csv"


# ============================================================
# ANALYSE ONE TEST
# ============================================================

def analyse_test(file_path):
    """Analyse one valve test CSV and return summary statistics."""

    df = pd.read_csv(file_path)

    # Convert columns to booleans if necessary
    if df["detected"].dtype != bool:
        df["detected"] = (
            df["detected"]
            .astype(str)
            .str.strip()
            .str.lower()
            .map({"true": True, "false": False})
            .fillna(False)
            .astype(bool)
        )

    if df["correct"].dtype != bool:
        df["correct"] = (
            df["correct"]
            .astype(str)
            .str.strip()
            .str.lower()
            .map({"true": True, "false": False})
            .fillna(False)
            .astype(bool)
        )

    # Test conditions
    distance = df["distance_m"].dropna().iloc[0]
    position = df["position"].dropna().iloc[0]
    true_state = df["true_state"].dropna().iloc[0]

    # Counts
    total_frames = len(df)
    detected_count = int(df["detected"].sum())
    not_detected_count = total_frames - detected_count

    correct_count = int(df["correct"].sum())
    incorrect_count = detected_count - correct_count

    # Rates
    detection_rate = (
        detected_count / total_frames * 100
        if total_frames > 0
        else 0
    )

    # Accuracy for frames where a valve was actually detected
    detected_accuracy = (
        correct_count / detected_count * 100
        if detected_count > 0
        else 0
    )

    # Overall success includes missed detections as failures
    overall_success_rate = (
        correct_count / total_frames * 100
        if total_frames > 0
        else 0
    )

    # Confidence statistics for detected valves only
    detected_confidence = df.loc[
        df["detected"], "valve_confidence"
    ].dropna()

    if len(detected_confidence) > 0:
        mean_confidence = detected_confidence.mean()
        median_confidence = detected_confidence.median()
        min_confidence = detected_confidence.min()
        max_confidence = detected_confidence.max()
        std_confidence = detected_confidence.std()
    else:
        mean_confidence = None
        median_confidence = None
        min_confidence = None
        max_confidence = None
        std_confidence = None

    return {
        "test_file": file_path.name,
        "true_state": true_state,
        "distance_m": distance,
        "position": position,

        "total_frames": total_frames,

        "detected": detected_count,
        "not_detected": not_detected_count,
        "detection_rate_percent": detection_rate,

        "correct": correct_count,
        "incorrect": incorrect_count,
        "detected_accuracy_percent": detected_accuracy,
        "overall_success_percent": overall_success_rate,

        "mean_confidence": mean_confidence,
        "median_confidence": median_confidence,
        "min_confidence": min_confidence,
        "max_confidence": max_confidence,
        "std_confidence": std_confidence,
    }


# ============================================================
# MAIN
# ============================================================

def main():
    # Find all CSV files beginning with "valve"
    valve_files = sorted(FOLDER.glob("valve*.csv"))

    # Don't accidentally analyse the summary from a previous run
    valve_files = [
        f for f in valve_files
        if f.name != OUTPUT_FILE.name
    ]

    if not valve_files:
        print(f"No valve CSV files found in:")
        print(FOLDER)
        return

    print(f"Found {len(valve_files)} valve test files.\n")

    summaries = []

    for file_path in valve_files:
        print(f"Analysing: {file_path.name}")

        try:
            summary = analyse_test(file_path)
            summaries.append(summary)

        except Exception as e:
            print(f"  ERROR: {e}")

    if not summaries:
        print("\nNo tests could be analysed.")
        return

    # Create one combined dataframe
    summary_df = pd.DataFrame(summaries)

    # Sort logically
    state_order = {"closed": 0, "open": 1}
    position_order = {"left": 0, "centre": 1, "center": 1, "right": 2}

    summary_df["_state_order"] = (
        summary_df["true_state"]
        .astype(str)
        .str.lower()
        .map(state_order)
        .fillna(99)
    )

    summary_df["_position_order"] = (
        summary_df["position"]
        .astype(str)
        .str.lower()
        .map(position_order)
        .fillna(99)
    )

    summary_df = summary_df.sort_values(
        by=[
            "_state_order",
            "distance_m",
            "_position_order"
        ]
    )

    summary_df = summary_df.drop(
        columns=["_state_order", "_position_order"]
    )

    # Round values for easier reading
    percent_columns = [
        "detection_rate_percent",
        "detected_accuracy_percent",
        "overall_success_percent",
    ]

    confidence_columns = [
        "mean_confidence",
        "median_confidence",
        "min_confidence",
        "max_confidence",
        "std_confidence",
    ]

    summary_df[percent_columns] = (
        summary_df[percent_columns].round(2)
    )

    summary_df[confidence_columns] = (
        summary_df[confidence_columns].round(4)
    )

    # Save
    summary_df.to_csv(OUTPUT_FILE, index=False)

    print("\n========================================")
    print("Analysis complete")
    print("========================================")
    print(f"Tests analysed: {len(summary_df)}")
    print(f"Summary saved to:")
    print(OUTPUT_FILE)

    print("\nSummary:")
    print(summary_df.to_string(index=False))


if __name__ == "__main__":
    main()