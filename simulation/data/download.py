import io
import pathlib

from simulation.data.connect import Connect
from googleapiclient.http import MediaIoBaseDownload
from pathlib import Path


class Downloader(Connect):
    """
    Responsible for downloading data from Google Drive upon request

    """

    def __init__(self, service):
        super().__init__(service)

    def download_evolution_number(self) -> None:
        """
        Download the latest evolution number on Google Drive
        """
        self.download_file(
            "Evolution Number", self.evolution_number_id, self.last_evolution_path
        )

    def download_evolution_browser(self) -> None:
        """
        Download the latest evolution browser on Google Drive
        """
        self.download_file(
            "Evolution Browser", self.evolution_browser_id, self.evolution_browser_path
        )

    def download_file(self, file_name: str, file_id: str, save_path: Path) -> None:
        """
        Given a ``file_id`` corresponding to ``file_name`` on Google Drive,
        download the file and save it to ``save_path``.

        :param file_name: name of file that will be downloaded
        :param file_id: ID of file that will be downloaded
        :param save_path: path to location for file to be saved
        """

        # Download the file
        request = self.service.files().get_media(fileId=file_id)
        fh = io.FileIO(save_path, "wb")
        download = MediaIoBaseDownload(fh, request)

        done = False
        while not done:
            status, done = download.next_chunk()

        print(f"File: {file_name} downloaded successfully to '{save_path}'.")
