import os
from app import app
from pathlib import Path


def test_upload_archive():
    file_path = Path(__file__).resolve().parent / 'archive.zip'
    with app.test_client() as client, open(file_path, 'rb') as file:
        response = client.post('/upload', data={'archive': (file, 'archive.zip')}, content_type='multipart/form-data')
        assert response.status_code == 200
        data = response.get_json()
        assert "message" in data
        assert data["message"] == "File uploaded and extracted successfully"
        assert "request_id" in data
        assert Path(data["csv_file_path"]).exists()

def test_file_is_extracted():
    file_path = Path(__file__).resolve().parent / 'archive.zip'
    with app.test_client() as client, open(file_path, 'rb') as file:
        response = client.post('/upload', data={'archive': (file, 'archive.zip')}, content_type='multipart/form-data')
        data = response.get_json()
        extracted_path = Path("temp") / data["request_id"] / "archive"
        assert extracted_path.exists()
        assert extracted_path.is_dir()
        #  check if there is no zip file in extracted folder
        for root, dirs, files in os.walk(extracted_path):
            for file in files:
                assert not file.endswith('.zip')

# TODO Fix the testcase
def test_scan_results():

    file_path = Path(__file__).resolve().parent / 'archive.zip'
    with app.test_client() as client, open(file_path, 'rb') as file:
        response = client.post('/upload', data={'archive': (file, 'archive.zip')}, content_type='multipart/form-data')
        assert response.status_code == 200
        data = response.get_json()
        assert "scan_result" in data
        scan_result = data["scan_result"]
        assert isinstance(scan_result, dict)
        expected_tokens = ["<Tkn425JFIRKTkn>", "<Tkn435JFIRKTkn>", "<Tkn445JFIRKTkn>", "<Tkn455JFIRKTkn>"]
        for token in expected_tokens:
            assert token in scan_result
            assert scan_result[token] == 6

