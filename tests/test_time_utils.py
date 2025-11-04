from datetime import datetime

from iching.core.time_utils import validate_time_input


def test_validate_time_input_happy_path():
    value = validate_time_input("2024.11.05.1530")
    assert isinstance(value, datetime)
    assert value.year == 2024
    assert value.month == 11
    assert value.day == 5
    assert value.hour == 15
    assert value.minute == 30


def test_validate_time_input_rejects_bad_format(capsys):
    result = validate_time_input("2024-11-05 1530")
    assert result is None
    captured = capsys.readouterr().out
    assert "时间格式无效" in captured
