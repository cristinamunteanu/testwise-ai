import pytest
import pandas as pd
import tempfile
import os

from app.parser import parse_file, parse_txt


def test_parse_csv_log():
    sample_csv = """timestamp,test_case,module,status,error,test_type
2025-07-14 02:35:05,test_adc_voltage,POWER,PASS,,
2025-07-14 02:35:10,test_can_bus,COMM,FAIL,TimeoutError,System
2025-07-14 02:35:15,test_temp_sensor,SENSOR,FAIL,NullReferenceException,Unit
2025-07-14 02:35:20,test_gpio_init,CORE,PASS,,Integration
"""
    with tempfile.NamedTemporaryFile(mode='w+', suffix='.csv', delete=False) as f:
        f.write(sample_csv)
        temp_path = f.name

    df = parse_file(temp_path)
    os.unlink(temp_path)

    expected_columns = {"timestamp", "test_case", "module", "status", "error", "test_type"}
    assert isinstance(df, pd.DataFrame)
    assert set(df.columns) == expected_columns
    assert df.shape[0] == 4
    assert df.loc[df["test_case"] == "test_can_bus", "error"].iloc[0] == "TimeoutError"
    assert df.loc[df["test_case"] == "test_gpio_init", "test_type"].iloc[0] == "Integration"


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
        f.write("[2025-07-14 02:35:05] [RESULT] test_str_mode [CORE] PASS [type=Unit]\n")
    df_str = parse_file(path)
    os.remove(path)
    assert df_str.shape[0] == 1
    assert df_str.iloc[0]["test_case"] == "test_str_mode"

    # This tests the file-like object branch
    from io import BytesIO
    file_like = BytesIO(b"[2025-07-14 02:35:05] [RESULT] test_io_mode [POWER] FAIL [type=System] - FaultInjection\n")
    file_like.name = "fake.log"
    df_io = parse_file(file_like)
    assert df_io.shape[0] == 1
    assert df_io.iloc[0]["status"] == "FAIL"


def test_parse_txt_log_format():
    log_data = """\
[2025-07-23 02:58:35] [INFO] Running test: test_case_000 [type=System]
[2025-07-23 02:58:35] [RESULT] test_case_000 [POWER] PASS
[2025-07-23 03:00:35] [RESULT] test_case_024 [SENSOR] PASS
"""
    from io import StringIO
    file_like = StringIO(log_data)

    df = parse_txt(file_like)

    expected_columns = {"timestamp", "test_case", "status", "module", "error", "test_type"}
    assert set(df.columns) == expected_columns
    assert df.shape[0] == 2, "Should parse 2 test cases"
    assert df.loc[df["test_case"] == "test_case_000", "status"].iloc[0] == "PASS"
    assert df.loc[df["test_case"] == "test_case_000", "module"].iloc[0] == "POWER"
    assert df.loc[df["test_case"] == "test_case_000", "test_type"].iloc[0] == "System"
    assert df.loc[df["test_case"] == "test_case_024", "test_type"].iloc[0] == ""


def test_parse_txt_text_format():
    # Sample text format data
    txt_data = """\
[2025-07-14 02:25:25] [RESULT] test_case_000 [SENSOR] FAIL [type=System] - MemoryAccessViolation in init()
[2025-07-14 02:25:30] [RESULT] test_case_001 [CORE] FAIL [type=Unit] - NullPointerException in 0x1AF4
[2025-07-14 02:25:35] [RESULT] test_case_002 [POWER] PASS [type=Integration]
"""
    from io import StringIO
    file_like = StringIO(txt_data)

    df = parse_txt(file_like)

    expected_columns = {"timestamp", "test_case", "status", "module", "error", "test_type"}
    assert set(df.columns) == expected_columns
    assert df.shape[0] == 3, "Should parse 3 test cases"
    assert df.loc[df["test_case"] == "test_case_000", "status"].iloc[0] == "FAIL"
    assert df.loc[df["test_case"] == "test_case_001", "module"].iloc[0] == "CORE"
    assert df.loc[df["test_case"] == "test_case_002", "error"].iloc[0] == ""


def test_txt_parser_handles_malformed_lines():
    # Malformed log format data (with one invalid line)
    malformed_log_data = """[2025-07-14 02:35:05] [INFO] Running test: test_case_116 [type=System]
[2025-07-14 02:35:05] [RESULT] test_case_116 [SENSOR] FAIL - MemoryAccessViolation in bus_handler()
invalid_line_without_result
[2025-07-14 02:35:15] [RESULT] test_case_118 [SENSOR] PASS
"""
    from io import StringIO
    file_like_log = StringIO(malformed_log_data)

    df_log = parse_txt(file_like_log)

    expected_columns = {"timestamp", "test_case", "status", "module", "error", "test_type"}
    assert set(df_log.columns) == expected_columns
    assert df_log.shape[0] == 2, "Should parse 2 valid lines from log format"
    assert "invalid_line_without_result" not in df_log["test_case"].values
    assert df_log.loc[df_log["test_case"] == "test_case_116", "test_type"].iloc[0] == "System"
    assert df_log.loc[df_log["test_case"] == "test_case_118", "test_type"].iloc[0] == ""


def test_parse_file_txt_branch():
    # Covers line 51: elif file_input.endswith(".txt") or file_input.endswith(".log"):
    txt_content = """[2025-07-14 02:35:05] [INFO] Running test: test_case_1 [type=System]
[2025-07-14 02:35:05] [RESULT] test_case_1 [CORE] PASS
"""
    import tempfile
    with tempfile.NamedTemporaryFile(mode="w+", suffix=".txt", delete=False) as f:
        f.write(txt_content)
        temp_path = f.name
    df = parse_file(temp_path)
    os.unlink(temp_path)
    assert df.shape[0] == 1
    assert df.iloc[0]["test_case"] == "test_case_1"



