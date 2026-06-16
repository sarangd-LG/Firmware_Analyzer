from urllib import request
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
import os
import zipfile
from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
from db import db
import re
import csv

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///firmware_analyzer.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5454, debug=True)

with app.app_context():
    db.create_all()

def extract_zip(file_path, extract_to="."):
    try:
        with zipfile.ZipFile(file_path, 'r') as zip_ref:
            zip_ref.extractall(extract_to)
            # after extracting the zip, the original zip file should be deleted to avoid confusion
            #  check files if, they are any nested zips, they should be extracted as well
            # make recursive call to this function with the path of nested zip files
            for file in zip_ref.namelist():
                if file.endswith('.zip'):
                    nested_zip_path = os.path.join(extract_to, file)
                    extract_zip(nested_zip_path, os.path.dirname(nested_zip_path))
                    print(f"Extracted nested zip file: {os.path.dirname(nested_zip_path)}")
                    os.remove(nested_zip_path)
    except zipfile.BadZipFile:
        print(f"Error: {file_path} is not a valid zip file.")
    except Exception as e:
        print(f"An error occurred while extracting {file_path}: {e}")

@app.post('/upload')
def upload_archive():
    file = request.files.get('archive')
    if not file:
        return jsonify({"error": "No file uploaded"}), 400

    filename = secure_filename(file.filename)
    if not filename:
        return jsonify({"error": "Invalid file name"}), 400

    os.makedirs("temp", exist_ok=True)
    temp_path = os.path.join("temp", filename)

    #  csv file folder to store results of the scan is created if it does not exist
    os.makedirs("results", exist_ok=True)

    # Save the uploaded file to a temporary location
    file.save(temp_path)

    # Extract the zip file
    extract_zip(temp_path, "temp")

    # path where the extracted files are stored is returned
    extracted_path = os.path.join("temp", os.path.splitext(filename)[0])

    # csv file to store results of the scan 
    csv_file_path = os.path.join("results", "scan_results.csv")

    scan_result = analyze_firmware(extracted_path, csv_file_path)

    return jsonify({"message": "File uploaded and extracted successfully", "scan_result": scan_result}), 200

def analyze_firmware(file_path, csv_file_path):
    result = []
    files_to_scan = []

    for root, dirs, files in os.walk(file_path):
        for file in files:
            current_file_path = os.path.join(root, file)
            relative_path = os.path.relpath(current_file_path, "temp")
            files_to_scan.append((current_file_path, relative_path))

    with ProcessPoolExecutor() as executor:
        futures = [
            executor.submit(scan_file, current_file_path, relative_path)
            for current_file_path, relative_path in files_to_scan
        ]

        for future in as_completed(futures):
            result.extend(future.result())
    sorted_result = sorted(result, key=lambda x: (len(x["file_path"]), x["count"], x["token"]))
    write_to_CSV(sorted_result, csv_file_path)

    token_totals = {}
    for row in sorted_result:
        token = row["token"]
        count = row["count"]
        if token in token_totals:
            token_totals[token] += count
        else:
            token_totals[token] = count
    return token_totals

def write_to_CSV(scan_result, csv_file_path):
    try:
        with open(csv_file_path, 'w', newline='', encoding='utf-8') as file:
            writer = csv.DictWriter(file, fieldnames=["file_path", "token", "count"])
            writer.writeheader()
            for row in scan_result:
                writer.writerow(row)
    except Exception as e:
        print(f"An error occurred while writing to CSV: {e}")

def scan_file(current_file_path, relative_path):
    rows = []
    token_pattern = re.compile(r"<Tkn\d{3}[A-Z]{5}Tkn>")
    with open(current_file_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
        tokens = token_pattern.findall(content)
        if tokens:
            map = {}
            for token in tokens:
                if token in map:
                    map[token] += 1
                else:
                    map[token] = 1
            for token, count in map.items():
                rows.append({
                    "file_path": relative_path,
                    "token": token,
                    "count": count
                })
    return rows
