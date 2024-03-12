import io

from simulation.data.connect import Connect
from googleapiclient.http import MediaIoBaseDownload
from pathlib import Path

EVOLUTION_NUMBER_ID = "1YHkewF40Na8xu137C-i4bVcuRoIARdQn"
EVOLUTION_BROWSER_ID = "1P7_pt6pgP7BkTOeUAZF915giN_2c8TGy"


class Downloader(Connect):
    def __init__(self):
        super().__init__()

    def download_evolution_number(self):
        self.download_file("Evolution Number", EVOLUTION_NUMBER_ID, Path("last_evolution.txt").resolve())

    def download_evolution_browser(self):
        self.download_file("Evolution Browser", EVOLUTION_BROWSER_ID, Path("evolution_browser.csv").resolve())

    def download_file(self, file_name: str, file_id: str, save_path: Path):
        # Download the file
        request = self.service.files().get_media(fileId=file_id)
        fh = io.FileIO(save_path, 'wb')
        downloader = MediaIoBaseDownload(fh, request)

        done = False
        while not done:
            status, done = downloader.next_chunk()

        print(f"File: {file_name} downloaded successfully to '{save_path}'.")


if __name__ == "__main__":
    downloader = Downloader()
    downloader.download_evolution_number()
    downloader.download_evolution_browser()

