import pandas as pd
import tempfile
import os

from app.parser import parse_file

def test_parse_txt_log():
    sample_txt = """\
test_adc_voltage: PASS
test_can_bus: FAIL - TimeoutError
test_temp_sensor: FAIL - NullReferenceException
test_gpio_init: PASS
"""
    with tempfile.NamedTemporaryFile(mode='w+', suffix='.txt', delete=False) as f:
        f.write(sample_txt)
        temp_path = f.name

    df = parse_file(temp_path)
    os.unlink(temp_path)  # Clean up

    assert isinstance(df, pd.DataFrame)
    assert set(df.columns) == {"test_case", "status", "error"}
    assert df.shape[0] == 4
    assert df[df["status"] == "FAIL"].shape[0] == 2
    assert "TimeoutError" in df["error"].values


def test_parse_csv_log():
    sample_csv = """test_case,status,error
test_adc_voltage,PASS,
test_can_bus,FAIL,TimeoutError
test_temp_sensor,FAIL,NullReferenceException
test_gpio_init,PASS,
"""
    with tempfile.NamedTemporaryFile(mode='w+', suffix='.csv', delete=False) as f:
        f.write(sample_csv)
        temp_path = f.name

    df = parse_file(temp_path)
    os.unlink(temp_path)

    assert isinstance(df, pd.DataFrame)
    assert set(df.columns) == {"test_case", "status", "error"}
    assert df.shape[0] == 4
    assert df.loc[df["test_case"] == "test_can_bus", "error"].iloc[0] == "TimeoutError"


def test_txt_parser_handles_malformed_lines():
    malformed_txt = """\
test_ok: PASS
bad_line_here_no_colon
test_fail: FAIL - UnknownException
"""
    with tempfile.NamedTemporaryFile(mode='w+', suffix='.txt', delete=False) as f:
        f.write(malformed_txt)
        temp_path = f.name

    df = parse_file(temp_path)
    os.unlink(temp_path)

    assert df.shape[0] == 2  # Only valid lines should be parsed
    assert "bad_line_here_no_colon" not in df["test_case"].values


def test_csv_parser_missing_column_raises():
    broken_csv = """case_name,status
test_a,PASS
test_b,FAIL
"""
    with tempfile.NamedTemporaryFile(mode='w+', suffix='.csv', delete=False) as f:
        f.write(broken_csv)
        temp_path = f.name

    try:
        parse_file(temp_path)
        assert False, "Should raise ValueError for missing columns"
    except ValueError as e:
        assert "Missing expected columns" in str(e)

    os.unlink(temp_path)


def test_parse_file_unsupported_type():
    # Test for unsupported file type
    try:
        parse_file("unsupported_file_type.xyz")
        assert False, "Should raise ValueError for unsupported file type"
    except ValueError as e:
        assert "Unsupported file type" in str(e)


def test_parse_csv_missing_columns():
    # Test for missing columns in CSV
    broken_csv = """case_name,status
test_a,PASS
test_b,FAIL
"""
    with tempfile.NamedTemporaryFile(mode='w+', suffix='.csv', delete=False) as f:
        f.write(broken_csv)
        temp_path = f.name

    try:
        parse_file(temp_path)
        assert False, "Should raise ValueError for missing columns"
    except ValueError as e:
        assert "Missing expected columns" in str(e)

    os.unlink(temp_path)




def test_parse_file_explicit_branches():
    # This tests the `str` branch
    path = "temp_str_path.txt"
    with open(path, "w") as f:
        f.write("test_str_mode: PASS\n")
    df_str = parse_file(path)
    os.remove(path)
    assert df_str.shape[0] == 1
    assert df_str.iloc[0]["test_case"] == "test_str_mode"

    # This tests the file-like object branch
    from io import BytesIO
    file_like = BytesIO(b"test_io_mode: FAIL - FaultInjection\n")
    file_like.name = "fake.log"
    df_io = parse_file(file_like)
    assert df_io.shape[0] == 1
    assert df_io.iloc[0]["status"] == "FAIL"



