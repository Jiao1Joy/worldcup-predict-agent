def test_package_exposes_version() -> None:
    import worldcup_agent

    assert worldcup_agent.__version__ == "0.1.0"
