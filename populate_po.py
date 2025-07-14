import requests
from requests.auth import HTTPBasicAuth
import json
import time
import urllib.parse
import os
import csv

file_path = r"secrets\spire.json"

with open(file_path, "r") as f:
    spire = json.load(f)

root_url = spire["root"]
username = spire["username"]
password = spire["password"]

headers = {"accept": "application/json"}

auth = HTTPBasicAuth(username, password)

# Headers
part_no_header = "Part No"
qty_header = "Order Qty"
cost_header = "Unit Price"

# Important info for the user!
print(f"Name your column headers \"{part_no_header}\", \"{qty_header}\", \"{cost_header}\" to ensure an accurate payload (case insenstive, order does not matter)")
print(f"Note that this program OVERWRITES the existing purchase order items with the content of the csv file!\n")

# Prompts user for PO number and creates the get request url
def prompt_po_number():
    # Ex. enter "64405"
    no = input("Enter the order number: ")
    # PO numbers are always 10 digits, so pad the input with 0's
    po_number = no.zfill(10)
    po_number_json = {"number":po_number}
    json_po = json.dumps(po_number_json)
    url_safe_json = urllib.parse.quote_plus(json_po)
    url = f"{root_url}/purchasing/orders/?filter={url_safe_json}&limit=50"
    return {"po_number": no, "url": url}

# Prompts for a PO number until an existing one is found
po = []
while len(po) == 0:
    d = prompt_po_number()
    url = d["url"]
    po_no = d["po_number"]

    response = requests.get(url, headers=headers, auth=auth)

    if response.status_code != 200:
        print(f"Could not get PO {po_no}, Status code: {response.status_code}")
    else: 
        response_json = response.json()
        po = response_json["records"]

# Confirm if the first records result is the correct PO number 
check = input(f"Is PO number {po[0]["number"]} correct? (Enter 'Y' for yes): ") 
if check == 'Y' or check == 'y':
    po_id = po[0]["id"]
    put_url = f"{root_url}/purchasing/orders/{po_id}"
else: 
    raise SystemExit

path = input("Enter the path to the csv file: ")
while not os.path.exists(path): 
    path = input(f"Could not find {path}, enter the path: ")

# Function to create the payload from the csv file
def create_payload(csv_file, part_no_header=part_no_header, cost_header=cost_header, qty_header=qty_header):
    base_payload = {
        "items": []
    }
    with open(csv_file, encoding="utf8", mode ='r') as file:
        csv_file = csv.reader(file)

        headers = next(csv_file)
        uppercase_headers = [header.upper() for header in headers]
        part_no_column = uppercase_headers.index(part_no_header.upper())
        unit_price_column = uppercase_headers.index(cost_header.upper())
        order_qty_column = uppercase_headers.index(qty_header.upper())

        for line_no, lines in enumerate(csv_file):
            part_no = lines[part_no_column]
            unit_price = lines[unit_price_column]
            order_qty = lines[order_qty_column]
            # UOM autopopulates with stock UOM
            item = {
                "inventory": {
                    "whse": "00", # Default warehouse is 00
                    "partNo": part_no
                },
                "orderQty": order_qty
            }

            # Use system cost if the unit price is not included in csv file
            if unit_price != "":
                item["unitPrice"] = unit_price
            
            base_payload["items"].append(item)
    return base_payload

try: 
    payload = create_payload(path)
except Exception as e:
    print(e)
    print("Failed to update PO")
    raise SystemExit

response = requests.put(put_url, json=payload, headers=headers, auth=auth)

if response.status_code == 200:
    print(f"PO updated!")
else:
    print(response.text)
print(f"Failed to update PO \nStatus code {response.status_code}")
