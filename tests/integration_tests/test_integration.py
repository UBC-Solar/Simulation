from simulation.run_simulation import build_basic_model


def test_integration():
    # This test asserts that no error is raised.
    model = build_basic_model()
    model.run_model()
