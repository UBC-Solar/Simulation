import io
import pathlib

from simulation.data.connect import Connect
from googleapiclient.http import MediaIoBaseDownload
from pathlib import Path


class Downloader(Connect):
    def __init__(self, service):
        super().__init__(service)

    def download_evolution_number(self):
        self.download_file("Evolution Number", self.evolution_number_id, self.last_evolution_path)

    def download_evolution_browser(self):
        self.download_file("Evolution Browser", self.evolution_browser_id, self.evolution_browser_path)

    def download_file(self, file_name: str, file_id: str, save_path: Path):
        # Download the file
        request = self.service.files().get_media(fileId=file_id)
        fh = io.FileIO(save_path, 'wb')
        download = MediaIoBaseDownload(fh, request)

        done = False
        while not done:
            status, done = download.next_chunk()

        print(f"File: {file_name} downloaded successfully to '{save_path}'.")
