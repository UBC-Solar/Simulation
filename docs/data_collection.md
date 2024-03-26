# Data Collection Scheme

In order to further the tuning of our hyperparameters for our optimization
process, it is imperative that we collect data on the evolutions that we run.

Additionally, it is critical that the context that the evolution was run with is preserved, 
and the settings and corresponding results appropriately recorded.

For more detail in the aspirations and requirements of this scheme, see _Proposal to Standardize Data Recording_.

## Description

1. When the hyperparameter optimization sequence is run, it will save the results of the evolution into an evolution folder into a `results_directory` (defaulted to `simulation/data/results`, but is a mutable parameter).
2. The evolution folder will be named numerically, beginning from 0.
3. The evolution folder will contain various files that aim to completely describe the context, settings, and results of the evolution.
4. Critically, the settings, context, and critical results (to hyperparameter tuning) will be captured in a `evolution_log.txt`.
5. When an evolution finishes, a counter which is used to name evolution folders, stored in `simulation/data`, will be incremented such that the name of each evolution folder remains unique.
6. Periodically, this local data can be offloaded to Google Drive. This offloading process is initiated by running the script `controller.py` in `simulation/data`.
7. First, the evolution number (the aforementioned counter) stored in Google Drive will be downloaded, and local evolution folders will be renamed to increment from that number.
8. Next, the logs for each local evolution will be collected to be stored in a central spreadsheet, `evolution_browser.csv`.
9. Then, the `evolution_browser.csv` from Google Drive will be downloaded, and the local data appended to it.
10. Finally, the updated and amended evolution number (counter) and `evolution_browser.csv` will be pushed to Google Drive.
11. Local evolution folders will be uploaded to Google Drive, and can subsequently be deleted (not automatic, at the moment).