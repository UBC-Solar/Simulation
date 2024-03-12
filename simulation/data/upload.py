import io
import os.path
from pathlib import Path

from googleapiclient.http import MediaFileUpload, MediaIoBaseUpload
from simulation.data.connect import Connect


EVOLUTION_ROOT_ID = "1L7mqA3UHsQD4FWVdkqDEcS6TPej6h9Pq"
EVOLUTION_NUMBER_ID = "1YHkewF40Na8xu137C-i4bVcuRoIARdQn"
EVOLUTION_BROWSER_ID = "1P7_pt6pgP7BkTOeUAZF915giN_2c8TGy"


class Uploader(Connect):
    def __init__(self):
        super().__init__()

    def create_folder(self, number: int) -> str:
        # Specify the folder metadata
        folder_metadata = {
            'name': str(number),
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [EVOLUTION_ROOT_ID]
        }

        # Create the folder
        created_folder = self.service.files().create(body=folder_metadata, fields='id').execute()
        print(f"Folder '{created_folder}' created successfully with ID: {created_folder['id']}")

        return created_folder['id']

    def upload_file(self, name: str, file: Path, folder_id: str):
        # Specify the file metadata
        file_metadata = {'name': name, 'parents': [folder_id]}

        # Create a MediaFileUpload object with the file to upload and the mimetype
        media = MediaFileUpload(file, mimetype='application/octet-stream', resumable=True)

        # Upload the file
        uploaded_file = self.service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        print(f"File '{uploaded_file}' uploaded successfully with ID: {uploaded_file['id']}")

    def update_file(self, file_id: str, file: Path):
        # Read the new bytes
        with open(file, 'rb') as data:
            modified_content = data.read()

        # Create a MediaIoBaseUpload object with the modified content
        media = MediaIoBaseUpload(io.BytesIO(modified_content), mimetype='application/octet-stream', resumable=True)

        # Upload the modified content back to the same file
        self.service.files().update(fileId=file_id, media_body=media).execute()
        print(f"File with ID '{file_id}' updated successfully.")

    def upload_evolution(self, evolution_folder: Path, number: int):
        folder_id = self.create_folder(number)

        files = [(str(file), Path(str(file))) for file in os.listdir(evolution_folder) if os.path.isfile(file)]
        for name, path in files:
            self.upload_file(name, path.resolve(), folder_id)


if __name__ == "__main__":
    # Bootstrap
    uploader = Uploader()
    uploader.upload_file("last_evolution.txt", Path("last_evolution.txt").resolve(), EVOLUTION_ROOT_ID)
    uploader.upload_file("evolution_browser.csv", Path("evolution_browser.csv").resolve(), EVOLUTION_ROOT_ID)
