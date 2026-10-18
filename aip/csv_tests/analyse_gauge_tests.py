from pathlib import Path

import numpy as np
import pandas as pd


# ==============================================================
# CONFIG
# ==============================================================

DATA_FOLDER = Path(__file__).resolve().parent

OUTPUT_SUMMARY = DATA_FOLDER / "gauge_summary.csv"
OUTPUT_RAW = DATA_FOLDER / "gauge_all_raw.csv"

# System accuracy requirement
ACCURACY_REQUIREMENT_BAR = 0.2


# ==============================================================
# PROCESS ONE CSV
# ==============================================================

def summarise_test(csv_path):
    df = pd.read_csv(csv_path)

    # ----------------------------------------------------------
    # Clean success column
    # ----------------------------------------------------------

    if df["success"].dtype != bool:
        df["success"] = (
            df["success"]
            .astype(str)
            .str.strip()
            .str.lower()
            .isin(["true", "1", "yes"])
        )

    # A valid successful reading requires:
    #   1. success == True
    #   2. measured_value is not missing
    valid_mask = df["success"] & df["measured_value"].notna()

    valid = df.loc[valid_mask].copy()


    # ----------------------------------------------------------
    # Test parameters
    # ----------------------------------------------------------

    distance = df["distance_m"].iloc[0]
    true_value = df["true_value"].iloc[0]
    position = df["position"].iloc[0]
    gauge_type = df["gauge_type"].iloc[0]


    # ----------------------------------------------------------
    # Basic reliability statistics
    # ----------------------------------------------------------

    total_frames = len(df)

    successful_reads = int(valid_mask.sum())

    failed_reads = total_frames - successful_reads

    if total_frames > 0:
        success_pct = 100 * successful_reads / total_frames
    else:
        success_pct = np.nan


    # ----------------------------------------------------------
    # Accuracy statistics
    # ----------------------------------------------------------

    if successful_reads > 0:

        signed_error = (
            valid["measured_value"]
            - valid["true_value"]
        )

        abs_error = signed_error.abs()

        # Main accuracy statistics
        mean_measured = valid["measured_value"].mean()

        bias = signed_error.mean()

        mae = abs_error.mean()

        max_abs_error = abs_error.max()

        rmse = np.sqrt(
            np.mean(signed_error ** 2)
        )

        p95_abs_error = abs_error.quantile(0.95)

        # Stability / repeatability
        std_measurement = valid["measured_value"].std()


        # ------------------------------------------------------
        # ±0.2 bar accuracy requirement
        # ------------------------------------------------------

        within_spec_mask = (
            abs_error <= ACCURACY_REQUIREMENT_BAR
        )

        within_spec_count = int(within_spec_mask.sum())

        within_spec_pct = (
            100
            * within_spec_count
            / successful_reads
        )

        # Percentage of ALL frames which both:
        #   - produced a reading
        #   - were within ±0.2 bar
        overall_spec_pass_pct = (
            100
            * within_spec_count
            / total_frames
        )

        # True only if every successful reading
        # satisfied the ±0.2 bar requirement
        all_reads_within_spec = bool(
            within_spec_mask.all()
        )


        # ------------------------------------------------------
        # Confidence statistics
        # ------------------------------------------------------

        mean_gauge_conf = (
            valid["gauge_confidence"].mean()
        )

        mean_centre_conf = (
            valid["centre_confidence"].mean()
        )

        mean_needle_conf = (
            valid["needle_confidence"].mean()
        )

    else:

        mean_measured = np.nan
        bias = np.nan
        mae = np.nan
        max_abs_error = np.nan
        rmse = np.nan
        p95_abs_error = np.nan
        std_measurement = np.nan

        within_spec_count = 0
        within_spec_pct = np.nan
        overall_spec_pass_pct = 0.0
        all_reads_within_spec = False

        mean_gauge_conf = np.nan
        mean_centre_conf = np.nan
        mean_needle_conf = np.nan


    # ----------------------------------------------------------
    # SUMMARY ROW
    # ----------------------------------------------------------

    summary = {

        # File
        "source_file": csv_path.name,

        # Test conditions
        "distance_m": distance,
        "true_value_bar": true_value,
        "position": position,
        "gauge_type": gauge_type,

        # Detection / reading reliability
        "total_frames": total_frames,
        "successful_reads": successful_reads,
        "failed_reads": failed_reads,
        "success_pct": success_pct,

        # Accuracy
        "mean_measured_bar": mean_measured,
        "bias_bar": bias,
        "mae_bar": mae,
        "max_abs_error_bar": max_abs_error,
        "rmse_bar": rmse,
        "p95_abs_error_bar": p95_abs_error,

        # Stability
        "std_measurement_bar": std_measurement,

        # ±0.2 bar requirement
        "within_0.2bar_count": within_spec_count,
        "within_0.2bar_pct": within_spec_pct,
        "overall_spec_pass_pct": overall_spec_pass_pct,
        "all_reads_within_0.2bar": all_reads_within_spec,

        # Detection confidence
        "mean_gauge_conf": mean_gauge_conf,
        "mean_centre_conf": mean_centre_conf,
        "mean_needle_conf": mean_needle_conf,
    }


    # ----------------------------------------------------------
    # ADD ERROR INFORMATION TO RAW DATA
    # ----------------------------------------------------------

    df["source_file"] = csv_path.name

    df["signed_error_bar"] = (
        df["measured_value"]
        - df["true_value"]
    )

    df["abs_error_bar"] = (
        df["signed_error_bar"].abs()
    )

    # Reading meets accuracy requirement only if:
    #   - detection/read was successful
    #   - absolute error <= 0.2 bar
    df["within_0.2bar"] = (
        valid_mask
        & (
            df["abs_error_bar"]
            <= ACCURACY_REQUIREMENT_BAR
        )
    )


    return summary, df


# ==============================================================
# FIND ALL GAUGE TEST CSV FILES
# ==============================================================

csv_files = sorted(
    DATA_FOLDER.glob("gauge_test_*.csv")
)

if not csv_files:
    print("No gauge test CSV files found.")
    raise SystemExit


# ==============================================================
# PROCESS ALL TESTS
# ==============================================================

summaries = []
raw_data = []

for csv_file in csv_files:

    print(
        f"Processing: {csv_file.name}"
    )

    try:

        summary, raw = summarise_test(
            csv_file
        )

        summaries.append(summary)

        raw_data.append(raw)

    except Exception as error:

        print(
            f"ERROR processing "
            f"{csv_file.name}: {error}"
        )


# ==============================================================
# CREATE SUMMARY TABLE
# ==============================================================

summary_df = pd.DataFrame(summaries)


# Sort into a useful order for analysis
summary_df = summary_df.sort_values(
    by=[
        "gauge_type",
        "distance_m",
        "true_value_bar",
        "position",
    ]
)


# Round values to make CSV easier to read
round_columns = [

    "success_pct",

    "mean_measured_bar",
    "bias_bar",
    "mae_bar",
    "max_abs_error_bar",
    "rmse_bar",
    "p95_abs_error_bar",
    "std_measurement_bar",

    "within_0.2bar_pct",
    "overall_spec_pass_pct",

    "mean_gauge_conf",
    "mean_centre_conf",
    "mean_needle_conf",
]

for column in round_columns:

    if column in summary_df.columns:

        summary_df[column] = (
            summary_df[column].round(4)
        )


# Save summary
summary_df.to_csv(
    OUTPUT_SUMMARY,
    index=False
)


# ==============================================================
# CREATE COMBINED RAW DATA FILE
# ==============================================================

if raw_data:

    combined_raw = pd.concat(
        raw_data,
        ignore_index=True
    )

    combined_raw.to_csv(
        OUTPUT_RAW,
        index=False
    )


# ==============================================================
# PRINT RESULTS
# ==============================================================

print()
print(
    f"Processed {len(summary_df)} "
    f"test files."
)

print(
    f"Summary saved to: "
    f"{OUTPUT_SUMMARY}"
)

print(
    f"Combined raw data saved to: "
    f"{OUTPUT_RAW}"
)

print()
print(
    "Accuracy requirement: "
    f"±{ACCURACY_REQUIREMENT_BAR} bar"
)

print()

# Display a useful condensed summary
display_columns = [
    "distance_m",
    "true_value_bar",
    "position",
    "gauge_type",
    "success_pct",
    "mae_bar",
    "max_abs_error_bar",
    "within_0.2bar_pct",
    "overall_spec_pass_pct",
]

print(
    summary_df[
        display_columns
    ].to_string(index=False)
)