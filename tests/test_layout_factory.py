from tests.fixtures.layout_factory import build_waveguide_fixture


def test_waveguide_fixture_has_expected_top_cell_and_layers(tmp_path):
    fixture = build_waveguide_fixture(tmp_path)

    assert fixture.top_cell == "TOP"
    assert fixture.path.exists()
    assert fixture.expected_layers
