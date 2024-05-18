"""
Controller manages the process of syncing and uploading evolution data.
"""

import os
import tomllib
import shutil
import pathlib
import string
import random
import googleapiclient.discovery
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from simulation.data.upload import Uploader
from simulation.data.download import Downloader
from simulation.data.assemble import Assembler
from simulation.data import data_directory
from collections import OrderedDict
from pathlib import Path


Client = googleapiclient.discovery.Resource


class Controller:
    def __init__(self, results_directory: str):
        # Get the data directory and config
        self.data_directory = data_directory
        with open(self.data_directory / "network.toml", 'rb') as config_file:
            config = tomllib.load(config_file)
            self.scopes = config['settings']['SCOPES']
            self.auth_file = os.path.join(data_directory, config['settings']['AUTH_FILE'])

        # Create clients with Google Drive
        service = Controller.get_service(self.authenticate())
        self.uploader: Uploader = Uploader(service)
        self.downloader: Downloader = Downloader(service)
        self.assembler: Assembler = Assembler(results_directory)

    def authenticate(self) -> Credentials:
        """
        Load authentication from the saved token file, the location of which is defined in ``network.toml``.

        :return: a Credentials object that can be used to create a Google Drive API client
        """
        if os.path.exists(self.auth_file):
            return Credentials.from_authorized_user_file(str(self.auth_file), self.scopes)
        else:
            raise FileNotFoundError("Cannot find Google Drive API token! Auth file not found: ", self.auth_file)

    @staticmethod
    def get_service(credentials: Credentials) -> Client:
        """
        From a ``credentials`` object, build a Google Drive API client.

        :param credentials: a Credentials object created from a token for the desired account
        :return: a Client object
        """
        return build("drive", "v3", credentials=credentials)

    def pull(self) -> None:
        """
        Pull the latest evolution browser and last evolution number from Google Drive.
        """
        self.downloader.download_evolution_browser()
        self.downloader.download_evolution_number()

    def push(self) -> None:
        """
        Push the updated evolution browser, last evolution number, and evolutions to Google Drive.
        """
        self.uploader.upload_evolution_number()
        self.uploader.upload_evolution_browser()
        self.assembler.reacquire_evolutions()
        for evolution_directory in self.assembler.evolutions:
            self.uploader.upload_evolution(Path(evolution_directory))

    def sync(self) -> None:
        """
        Invoke the process of pulling the latest data from Google Drive, merging with local data,
        and pushing the updated data and evolutions to Google Drive.
        """
        self.pull()

        evolution_number: int = Assembler.get_current_evolution()
        evolution_number = self.localize_evolutions(evolution_number)
        local_results = self.assembler.collect_local_results()

        local_results.to_csv(os.path.join(self.data_directory, "evolution_browser.csv"), mode='a', header=False)
        Assembler.set_evolution_counter(evolution_number)

        self.push()

    def localize_evolutions(self, evolution_number: int):
        """
        From an ``evolution_number``, sync local evolutions so that their names follow what is on Google Drive,
        sequentially.

        :param evolution_number: an integer representing the next evolution number that should be pushed to Google Drive
        :return:
        """
        # We need an ordered dictionary to maintain order when matching evolutions to a random key
        evolutions = OrderedDict((id_generator(), evolution_path) for evolution_path in self.assembler.evolutions)

        # Temporarily rename evolution folders to their random key (so that they don't override each other)
        # Otherwise, if the next evolution number was 6, and we had `5`, `6` locally, `5` would get overriden into `6`.
        for evolution_id, evolution_path in evolutions.items():
            new_path = pathlib.Path(evolution_path).resolve().parent / evolution_id
            shutil.move(Path(evolution_path).resolve(), Path(new_path).resolve())
            evolutions[evolution_id] = new_path

        # Rename evolution folders to their proper, localized names, from the temporary names.
        for evolution_id, evolution_path in evolutions.items():
            new_path = os.path.join(self.assembler.results_directory, str(evolution_number))
            shutil.move(Path(evolution_path).resolve(), Path(new_path).resolve())
            evolution_number += 1

        return evolution_number


def id_generator(size=6, chars=string.ascii_uppercase + string.digits):
    """
    Generate a random sequence of characters.

    :param size: number of characters
    :param chars: valid characters
    :return: a random sequence of characters of length ``size`` and containing characters from ``chars``.
    """
    return ''.join(random.choice(chars) for _ in range(size))


def reset(controller) -> None:
    """
    Push only the local evolution number and browser.
    Useful for resetting what is on Google Drive.

    :param controller: controller to perform this action
    """
    controller.uploader.upload_evolution_number()
    controller.uploader.upload_evolution_browser()


def bootstrap(controller: Controller):
    """
    Boostrap Google Drive to have the evolution browser and number file.
    REQUIRES SAVING THE NEWLY CREATED IDS INTO ``network.toml``!!

    :param controller: controller to perform this action
    """

    controller.uploader.upload_file("last_evolution.txt", Path("last_evolution.txt").resolve(), controller.uploader.evolution_number_id)
    controller.uploader.upload_file("evolution_browser.csv", Path("evolution_browser.csv").resolve(), controller.uploader.evolution_browser_id)
    print("WARNING! SAVE THE ABOVE ID'S INTO NETWORK.TOML!")

if __name__ == "__main__":
    path = ""
    while not os.path.exists(path):  # Prompt user to submit or resubmit path
        path = input("Enter/Paste path to simulation data results: ")

        if not os.path.exists(path):  # Check path validity
            print("Path invalid, please check path and resubmit")

    controller: Controller = Controller(path)
    controller.sync()