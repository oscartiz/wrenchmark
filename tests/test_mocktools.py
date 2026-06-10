from wrenchmark import mocktools as m


def test_world_is_deterministic():
    assert m.get_weather("Paris") == m.get_weather("paris ")
    assert "17" in m.get_weather("Paris, France")
    assert "no weather data" in m.get_weather("Mars")


def test_chain_data_is_consistent():
    # Alice -> Physics -> budget; head of Engineering must be a real employee
    assert "Physics" in m.lookup_employee("alice")
    assert "120000" in m.lookup_department("physics")
    assert "Frank" in m.lookup_department("engineering")
    assert "frank@acme.io" in m.lookup_employee("frank")


def test_currency_and_calc():
    assert "110.00 USD" in m.convert_currency(100, "EUR", "USD")
    assert "137.50 USD" in m.convert_currency(2500, "mxn", "usd")
    assert m.calculator("173.40 / 6") == "28.9"
    assert "Error" in m.calculator("__import__('os')")


def test_registry_scopes_tools():
    schemas, dispatch = m.registry_for(["get_weather", "calculator"])
    assert len(schemas) == 2 and set(dispatch) == {"get_weather", "calculator"}
    try:
        m.registry_for(["nope"])
        raise AssertionError("should have raised")
    except KeyError:
        pass
