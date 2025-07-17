import pytest
import pandas as pd
import tempfile
import os

from app.parser import parse_file, parse_txt


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


def test_parse_txt_log_format():
    # Sample log format data
    log_data = """\
[2025-07-14 02:35:05] ▶ Result: test_case_116 | FAIL | Module: SENSOR | Error: MemoryAccessViolation in bus_handler()
[2025-07-14 02:35:10] ▶ Result: test_case_117 | FAIL | Module: UI | Error: NullPointerException in init()
[2025-07-14 02:35:15] ▶ Result: test_case_118 | PASS | Module: SENSOR
"""
    from io import StringIO
    file_like = StringIO(log_data)

    df = parse_txt(file_like)

    # Assertions
    assert set(df.columns) == {"test_case", "status", "module", "error"}, "Columns should match expected set"
    assert df.shape[0] == 3, "Should parse 3 test cases"
    assert df.loc[df["test_case"] == "test_case_116", "status"].iloc[0] == "FAIL"
    assert df.loc[df["test_case"] == "test_case_117", "module"].iloc[0] == "UI"
    assert df.loc[df["test_case"] == "test_case_118", "error"].iloc[0] == ""


def test_parse_txt_text_format():
    # Sample text format data
    txt_data = """\
[2025-07-14 02:25:25] [RESULT] test_case_000 [SENSOR] FAIL - MemoryAccessViolation in init()
[2025-07-14 02:25:30] [RESULT] test_case_001 [CORE] FAIL - NullPointerException in 0x1AF4
[2025-07-14 02:25:35] [RESULT] test_case_002 [POWER] PASS
"""
    from io import StringIO
    file_like = StringIO(txt_data)

    df = parse_txt(file_like)

    # Assertions
    assert df.shape[0] == 3, "Should parse 3 test cases"
    assert df.loc[df["test_case"] == "test_case_000", "status"].iloc[0] == "FAIL"
    assert df.loc[df["test_case"] == "test_case_001", "module"].iloc[0] == "CORE"
    assert df.loc[df["test_case"] == "test_case_002", "error"].iloc[0] == ""


def test_txt_parser_handles_malformed_lines():
    # Malformed log format data
    malformed_log_data = """[2025-07-14 02:35:05] ▶ Result: test_case_116 | FAIL | Module: SENSOR | Error: MemoryAccessViolation in bus_handler()
invalid_line_without_result
[2025-07-14 02:35:15] ▶ Result: test_case_118 | PASS | Module: SENSOR
"""
    from io import StringIO
    file_like_log = StringIO(malformed_log_data)

    # Print the content of the StringIO object for debugging
    print("Log Data:", file_like_log.getvalue())

    # Reset the pointer to the beginning of the StringIO object
    file_like_log.seek(0)

    df_log = parse_txt(file_like_log)

    # Assertions for log format
    assert df_log.shape[0] == 2, "Should parse 2 valid lines from log format"
    assert "invalid_line_without_result" not in df_log["test_case"].values

    # Malformed text format data
    malformed_txt_data = """[2025-07-14 02:25:25] [RESULT] test_case_000 [SENSOR] FAIL - MemoryAccessViolation in init()
bad_line_missing_result_tag
[2025-07-14 02:25:35] [RESULT] test_case_002 [POWER] PASS
"""
    file_like_txt = StringIO(malformed_txt_data)

    # Print the content of the StringIO object for debugging
    print("Text Data:", file_like_txt.getvalue())

    # Reset the pointer to the beginning of the StringIO object
    file_like_txt.seek(0)

    df_txt = parse_txt(file_like_txt)

    # Assertions for text format
    assert df_txt.shape[0] == 2, "Should parse 2 valid lines from text format"
    assert "bad_line_missing_result_tag" not in df_txt["test_case"].values



