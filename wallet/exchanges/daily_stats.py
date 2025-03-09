import os
import pandas as pd

# Define file paths
input_file = "filtered_payments.csv"  # Replace with your actual file path
output_file = "summed_by_date.csv"

# Delete the output file if it exists
if os.path.exists(output_file):
    os.remove(output_file)
    print(f"Existing file '{output_file}' has been deleted.")
else:
    print(f"No existing file named '{output_file}' found.")

# Read the CSV
df = pd.read_csv(input_file)

# Ensure correct column names (strip spaces if needed)
df.columns = df.columns.str.strip()

# Convert 'created_at' to datetime
df["created_at"] = pd.to_datetime(df["created_at"])

# Extract the date part (year-month-day)
df["date_only"] = df["created_at"].dt.date

# Convert 'amount' to numeric, coercing errors to NaN
df["amount"] = pd.to_numeric(df["amount"], errors="coerce")

# Drop rows with NaN values in 'amount'
df = df.dropna(subset=["amount"])

# Sum amounts for each date
df_grouped = df.groupby("date_only", as_index=False)["amount"].sum()

# Round 'amount' to zero decimal places
df_grouped["amount"] = df_grouped["amount"].round(0)

# Save to a new CSV file
df_grouped.to_csv(output_file, index=False)

print(f"Processed file saved as '{output_file}'")
