from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import HTMLResponse
import io
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
required_headers = {
        "PART NO", 
        "ORDER QTY"
        }

# Important info for the user!
message_1 = f"Name your column headers " + ", ".join(f"<strong>{header}</strong>" for header in required_headers) + " and <strong>UNIT PRICE</strong>"
message_2 = f"Note that this program OVERWRITES the existing purchase order items with the content of the csv file!\n"

# FUNCTIONS

# Interprets the input as a Spire PO number and creates the request url
def process_po_number(no):
    # PO numbers are always 10 digits, so pad the input with 0's
    po_number = no.zfill(10)
    po_number_json = {"number":po_number}
    json_po = json.dumps(po_number_json)
    url_safe_json = urllib.parse.quote_plus(json_po)
    url = f"{root_url}/purchasing/orders/?filter={url_safe_json}&limit=50"
    return {"po_number": no, "url": url}

# Find the entered PO 
def find_po(url):
    response = requests.get(url, headers=headers, auth=auth)
    if response.status_code != 200:
        print(f"Could not get PO {po_no}, Status code: {response.status_code}")
        return []
    else: 
        response_json = response.json()
        if not response_json["records"]:
            print("No results found. Double-check the PO exists and is active")
            return []
        else:
            po = response_json["records"][0]
            return po

# Function to create the payload from the csv file
def create_payload(csv_file: UploadFile, required_headers):
    base_payload = {
        "items": []
    }
    with io.TextIOWrapper(csv_file.file, encoding="utf-8", newline="") as file:
        csv_file = csv.reader(file)

        headers = next(csv_file)
        uppercase_headers = {header.upper(): i for i, header in enumerate(headers)}

        for header in required_headers:
            print(header)
            if header not in uppercase_headers:
                raise HTTPException(status_code=422, detail=f"Missing {header} column") 
        
        for line_no, lines in enumerate(csv_file):
            # UOM autopopulates with stock UOM
            item = {
                "inventory": {
                    "whse": "00", # Default warehouse is 00
                    "partNo": lines[uppercase_headers.get("PART NO")]
                },
                "orderQty": lines[uppercase_headers.get("ORDER QTY")]
            }

            # Use system cost if the unit price is not included in csv file
            if uppercase_headers.get("UNIT PRICE"):
                item["unitPrice"] = lines[uppercase_headers.get("UNIT PRICE")]
            
            base_payload["items"].append(item)
    return base_payload

app = FastAPI()

@app.get("/", response_class=HTMLResponse)
async def upload_form():
    return f"""
    <html>
        <body>
            <h2>PO Import</h2>
            <p>{message_1}<br>{message_2}</p>
            <form action="/upload/" method="post" enctype="multipart/form-data">
                PO Number: <input type="text" name="po_number"><br>
                Upload a file: <input type="file" name="file"><br>
                <input type="submit" value="Submit">
            </form>
        </body>
    </html>
    """

@app.post("/upload/")
async def upload_file(po_number: str = Form(), file: UploadFile = File()):
    # Form validation
    if po_number == "":
        raise HTTPException(status_code=422, detail="PO number is required")
    
    if not file.filename:
        raise HTTPException(status_code=422, detail="File is required")
    
    processed_po_no = process_po_number(po_number)
    po = find_po(processed_po_no["url"])

    if not po:
        raise HTTPException(status_code=404, detail="PO not found")
    
    po_id = po["id"]
    put_url = f"{root_url}/purchasing/orders/{po_id}"

    payload = create_payload(file, required_headers)
    response = requests.put(put_url, json=payload, headers=headers, auth=auth)

    if response.status_code == 200:
        return response.json()
    else:
        message = f"Failed to update PO: {response.text}"
        raise HTTPException(status_code=response.status_code, detail=message)
