def test_import():
    """The package installs and imports cleanly from the src layout."""
    import battery_dispatch

    assert battery_dispatch.__version__
