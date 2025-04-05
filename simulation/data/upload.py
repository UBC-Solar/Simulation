import io
import os.path
from pathlib import Path

from googleapiclient.http import MediaFileUpload, MediaIoBaseUpload
from simulation.data.connect import Connect


class Uploader(Connect):
    """

    Responsible for uploading data to Google Drive upon request

    """

    def __init__(self, service):
        super().__init__(service)

    def create_folder(self, folder_name: str) -> str:
        """

        Create a folder on Google Drive in the 'Evolution' root folder.

        :param folder_name: the name of the folder
        :return: ID of the created folder
        """

        # Specify the folder metadata
        folder_metadata = {
            "name": folder_name,
            "mimeType": "application/vnd.google-apps.folder",
            "parents": [self.evolution_root_id],
        }

        # Create the folder
        created_folder = (
            self.service.files().create(body=folder_metadata, fields="id").execute()
        )
        print(
            f"Folder '{created_folder}' created successfully with ID: {created_folder['id']}"
        )

        return created_folder["id"]

    def upload_file(self, name: str, file: Path, folder_id: str) -> None:
        """

        Upload a ``file`` on the disk to Google Drive, into the folder corresponding
        to ``folder_id``.

        :param name: name that the file will have on Google Drive
        :param file: path to the file to be uploaded
        :param folder_id: ID of the parent folder on Google Drive
        """

        # Specify the file metadata
        file_metadata = {"name": name, "parents": [folder_id]}

        # Create a MediaFileUpload object with the file to upload and the mimetype
        media = MediaFileUpload(
            file, mimetype="application/octet-stream", resumable=True
        )

        # Upload the file
        uploaded_file = (
            self.service.files()
            .create(body=file_metadata, media_body=media, fields="id")
            .execute()
        )
        print(
            f"File '{uploaded_file}' uploaded successfully with ID: {uploaded_file['id']}"
        )

    def update_file(self, file_id: str, file: Path) -> None:
        """

        Update an existing file, identified by ``file_id``, on Google Drive with the contents
        on the disk in the file at ``file``.

        :param file_id:
        :param file:
        """
        # Read the new bytes
        with open(file, "rb") as data:
            modified_content = data.read()

        # Create a MediaIoBaseUpload object with the modified content
        media = MediaIoBaseUpload(
            io.BytesIO(modified_content),
            mimetype="application/octet-stream",
            resumable=True,
        )

        # Upload the modified content back to the same file
        self.service.files().update(fileId=file_id, media_body=media).execute()
        print(f"File with ID '{file_id}' updated successfully.")

    def upload_evolution(self, evolution_folder: Path) -> None:
        """

        Upload an evolution folder, and all of its contents, to Google Drive.

        :param evolution_folder: path to the evolution folder to be uploaded.
        """
        evolution_number: int = int(str(evolution_folder).split(os.sep)[-1])
        folder_id = self.create_folder(str(evolution_number))

        files = [
            (str(file), Path(str(os.path.join(evolution_folder, file))))
            for file in os.listdir(evolution_folder)
            if os.path.isfile(os.path.join(evolution_folder, file))
        ]
        for name, path in files:
            self.upload_file(name, path.resolve(), folder_id)

    def upload_evolution_number(self) -> None:
        """

        Upload the current evolution number (update the existing file on Google Drive) to Google Drive.

        """
        self.update_file(self.evolution_number_id, self.last_evolution_path)

    def upload_evolution_browser(self):
        """

        Upload the current evolution browser (update the existing file on Google Drive) to Google Drive.

        """
        self.update_file(self.evolution_browser_id, self.evolution_browser_path)
