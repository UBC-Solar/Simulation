from PyQt5.QtGui import QIcon
import matplotlib
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar


from PyQt5.QtCore import QSize

class CustomNavigationToolbar(NavigationToolbar):
    """Custom toolbar with tooltips for each button."""

    def __init__(self, canvas, parent=None):
        """
        :param PlotCanvas canvas: the canvas on which we will include our toolbar.
        """
        super().__init__(canvas, parent)

        # Load a save icon (matching Matplotlib's style)
        save_icon = QIcon(matplotlib.get_data_path() + "/images/filesave.png")

        # Add a "Save Data" button to the toolbar for saving data as a csv
        self.save_data_action = self.addAction(save_icon, "Save Data")
        self.save_data_action.setToolTip("Save the plotted data as a CSV file.")
        self.save_data_action.triggered.connect(self.canvas.save_data_to_csv)
        self.addAction(self.save_data_action)




        #stuff added:


        self.setIconSize(QSize(24, 24))
        self.setFixedHeight(25)


        # Define tooltips for each standard tool in the toolbar
        tooltips = {
            "Home": "Reset view.",
            "Back": "Go back to the previous view.",
            "Forward": "Move forward in the view history.",
            "Pan": "Click and drag to move the plot.",
            "Zoom": "Select a region to zoom in.",
            "Save": "Save the current plot as an image file.",
        }

        # Loop through toolbar buttons and set tooltips
        for action in self.actions():
            text = action.text()
            if text in tooltips:
                action.setToolTip(tooltips[text])
