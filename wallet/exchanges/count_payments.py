import requests
import csv
import json

output_file = "filtered_payments.csv"
raw_output_file = "raw_payments.json"

# Horizon Server Details
horizon_server = "https://api.mainnet.minepi.com"

# Ask user for wallet address
account_id = input("Enter your Pi Network wallet address: ").strip()

# Function to fetch all payments for an account
def fetch_all_payments(account):
    url = f"{horizon_server}/accounts/{account}/payments"
    params = {"order": "desc", "limit": 200}  # Adjust limit if necessary
    payments = []
    
    page=1
    while url:
        print(f"Page> {page}")
        response = requests.get(url, params=params)
        if response.status_code == 200:
            data = response.json()
            records = data.get("_embedded", {}).get("records", [])
            payments.extend(records)
            
            # Check if there's a next page
            url = data.get("_links", {}).get("next", {}).get("href")
            params = {}  # Reset params since URL already contains them
        else:
            print(f"Error fetching payments for {account}: {response.status_code}")
            break
        page+=1 

    return payments

# Fetch all payments for the main account
payments = fetch_all_payments(account_id)

# Save the raw payments as a JSON file
with open(raw_output_file, "w", encoding="utf-8") as f:
    json.dump(payments, f, ensure_ascii=False, indent=4)

# Filter and write to CSV
filtered_payments = [
    (p["created_at"], p["from"], p["amount"])
    for p in payments
    if p.get("type") == "payment" and p.get("to_muxed", "").startswith("M")
]

# Write to CSV
with open(output_file, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["created_at", "from", "amount"])  # Header row
    writer.writerows(filtered_payments)

print(f"Filtered payments saved to {output_file}")
print(f"Raw payments saved to {raw_output_file}")
