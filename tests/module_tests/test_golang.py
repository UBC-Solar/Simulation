import simulation as simulation


def test_acquired_libraries():
    library = simulation.Libraries()
    assert library.go_directory is not None
