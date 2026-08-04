from custom_components.maico_kwl.profiles import (
    room_temp_source_from_value,
    room_temp_source_to_value,
)


def test_room_temp_source_mapping_round_trip() -> None:
    assert room_temp_source_from_value(0) == "Komfort-BDE"
    assert room_temp_source_from_value(1) == "Extern"
    assert room_temp_source_from_value(2) == "Intern"
    assert room_temp_source_from_value(3) == "Bus"

    assert room_temp_source_to_value("Komfort-BDE") == 0
    assert room_temp_source_to_value("Extern") == 1
    assert room_temp_source_to_value("Intern") == 2
    assert room_temp_source_to_value("Bus") == 3
