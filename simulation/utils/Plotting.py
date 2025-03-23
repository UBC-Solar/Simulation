from bokeh.layouts import gridplot
from bokeh.models import HoverTool
from bokeh.plotting import figure, show, output_file
import os
import pathlib


class GraphPage:
    """

    A graph page contains a singular or series of graphs that will be plotted on one page.

    """

    def __init__(self, arrays_to_plot, plot_titles, page_name):
        self.arrays_to_plot = arrays_to_plot
        self.plot_titles = plot_titles
        self.page_name = page_name


class Plotting:
    """

    This class exists to organize the plotting of graphs.

    """

    def __init__(self):
        self.graph_queue = []

    def plot_graph_pages(self, timestamps, plot_portion):
        """

        Plot all graph pages in the queue.

        :param np.ndarray timestamps: Array of timestamps which serves as the "x-axis" of graphs.
        :param tuple[float] plot_portion: A tuple containing percentages that denote the beginning and end of the
        portion of the race that we'd like to plot. For example, if you wanted to plot the second half of the race,
        input (0.5, 1.0).

        """

        assert 0.0 <= plot_portion[0] < plot_portion[1] <= 1.0, (
            "plotting_portion is out of bounds!"
        )

        # Graph all graphs that have been queued
        for graph in self.graph_queue:
            plot_graph(
                timestamps=timestamps,
                arrays_to_plot=graph.arrays_to_plot,
                array_labels=graph.plot_titles,
                graph_title=graph.page_name,
                plot_portion=plot_portion,
            )

        # Remove every graph from the queue after they've been graphed.
        self.graph_queue.clear()

    def add_graph_page_to_queue(self, new_graph):
        """

        Add a new graph page to the plotting queue.

        :param GraphPage new_graph: Graph page object to be added in the queue of graphs to be plotted.

        """

        self.graph_queue.append(new_graph)


def plot_graph(
    timestamps,
    arrays_to_plot,
    array_labels,
    graph_title,
    save=True,
    plot_portion: tuple[float] = (0.0, 1.0),
):
    """

    This is a utility function to plot out any set of NumPy arrays you pass into it using the Bokeh library.
    The precondition of this function is that the length of arrays_to_plot and array_labels are equal.

    This is because there be a 1:1 mapping of each entry of arrays_to_plot to array_labels such that:
        arrays_to_plot[n] has label array_labels[n]

    Result:
        Produces a 3 x ceil(len(arrays_to_plot) / 3) plot
        If save is enabled, save html file

    Another precondition of this function is that each of the arrays within arrays_to_plot also have the
    same length. This is each of them will share the same time axis.

    :param np.ndarray timestamps: An array of timestamps for the race
    :param list arrays_to_plot: An array of NumPy arrays to plot
    :param list array_labels: An array of strings for the individual plot titles
    :param str graph_title: A string that serves as the plot's main title
    :param bool save: Boolean flag to control whether to save an .html file
    :param plot_portion: tuple containing beginning and end of arrays that we want to plot as percentages which is
    useful if we only want to plot for example the second half of the race in which case we would input (0.5, 1.0).

    """

    if plot_portion != (0.0, 1.0):
        for index, array in enumerate(arrays_to_plot):
            beginning_index = int(len(array) * plot_portion[0])
            end_index = int(len(array) * plot_portion[1])
            arrays_to_plot[index] = array[beginning_index:end_index]

        beginning_index = int(len(timestamps) * plot_portion[0])
        end_index = int(len(timestamps) * plot_portion[1])
        timestamps = timestamps[beginning_index:end_index]

    compress_constant = max(int(timestamps.shape[0] / 5000), 1)

    for index, array in enumerate(arrays_to_plot):
        arrays_to_plot[index] = array[::compress_constant]

    figures = list()

    hover_tool = HoverTool()
    hover_tool.formatters = {"x": "datetime"}
    hover_tool.tooltips = [("time", "$x"), ("data", "$y")]

    for index, data_array in enumerate(arrays_to_plot):
        # create figures and put them in list
        figures.append(
            figure(
                title=array_labels[index],
                x_axis_label="Time (hr)",
                y_axis_label=array_labels[index],
                x_axis_type="datetime",
            )
        )

        # add line renderers to each figure
        colours = (
            "#EC1557",
            "#F05223",
            "#F6A91B",
            "#A5CD39",
            "#20B254",
            "#00AAAE",
            "#4998D3",
            "#892889",
            "#fa1b9a",
            "#F05223",
            "#EC1557",
            "#F05223",
            "#F6A91B",
            "#A5CD39",
            "#20B254",
            "#00AAAE",
            "#4998D3",
            "#892889",
            "#fa1b9a",
            "#F05223",
            "#EC1557",
            "#F05223",
            "#F6A91B",
            "#A5CD39",
            "#20B254",
            "#00AAAE",
            "#4998D3",
            "#892889",
            "#fa1b9a",
            "#F05223",
            "#EC1557",
            "#F05223",
            "#F6A91B",
            "#A5CD39",
            "#EC1557",
            "#F05223",
        )
        figures[index].line(
            timestamps[::compress_constant] * 1000,
            data_array,
            line_color=colours[index],
            line_width=2,
        )

        figures[index].add_tools(hover_tool)

    grid = gridplot(figures, ncols=3, height=400, width=450)

    if save:
        filename = graph_title + ".html"
        filepath = pathlib.Path(os.path.abspath(__file__)).parent.parent.parent / "html"
        os.makedirs(filepath / "html", exist_ok=True)
        output_file(filename=str(filepath / filename), title=graph_title)

    show(grid)

    return
