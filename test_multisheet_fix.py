"""
Test Multi-Sheet Row Mapping Bug Fix

This test verifies that the per-sheet row mapping fix correctly
handles multiple sheets with different row structures without
row offset corruption.

Bug Description:
    When processing multiple sheets sequentially, the row_mapping
    was being overwritten by subsequent sheets, causing translations
    to be written to incorrect rows.

Expected Behavior:
    Each sheet maintains its own row mapping, ensuring translations
    are always written to the correct Excel rows regardless of
    processing order or row structure differences.
"""

from pathlib import Path
import sys
from openpyxl import Workbook, load_workbook

sys.path.insert(0, str(Path(__file__).parent))

from core.CConfig import CConfig
from core.XLSXCore import XLSXCore


def create_test_multisheet_xlsx(file_path: Path) -> None:
    """
    Create test XLSX with 2 sheets having DIFFERENT row structures.

    This simulates the real-world scenario where sheets have different
    numbers of empty rows, which would expose the row mapping bug.
    """
    wb = Workbook()

    # ===================================
    # Sheet 1: "s4_1" (3 data rows, NO empty rows at start)
    # ===================================
    ws1 = wb.active
    ws1.title = "s4_1"

    ws1['A1'] = 'who_talk'
    ws1['B1'] = 'talk'

    # Data rows (Excel rows 2-4)
    ws1['A2'] = 'Reika'
    ws1['B2'] = 'こんにちは'  # Should translate to row 2

    ws1['A3'] = ''  # Narrator
    ws1['B3'] = '彼女は笑った'  # Should translate to row 3

    ws1['A4'] = 'Reika'
    ws1['B4'] = 'ありがとう'  # Should translate to row 4

    # ===================================
    # Sheet 2: "s4_2" (4 data rows, WITH empty rows)
    # ===================================
    ws2 = wb.create_sheet("s4_2")

    ws2['A1'] = 'who_talk'
    ws2['B1'] = 'talk'

    # Empty row (should be skipped)
    ws2['A2'] = ''
    ws2['B2'] = ''

    # Data rows (Excel rows 3-6, but JSONLine IDs 1-4)
    ws2['A3'] = 'Hana'
    ws2['B3'] = 'おはよう'  # JSONLine id=1 → Excel row 3

    ws2['A4'] = ''
    ws2['B4'] = ''  # Empty, skip

    ws2['A5'] = ''  # Narrator
    ws2['B5'] = '朝日が昇る'  # JSONLine id=2 → Excel row 5

    ws2['A6'] = 'Hana'
    ws2['B6'] = 'さようなら'  # JSONLine id=3 → Excel row 6

    ws2['A7'] = ''
    ws2['B7'] = '彼女は去った'  # JSONLine id=4 → Excel row 7

    file_path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(file_path)
    wb.close()


def test_multisheet_row_mapping_independence():
    """
    Core test: Verify each sheet uses its own row mapping.

    This test would FAIL with the old buggy code where row_mapping
    was shared across sheets.
    """
    print("\n" + "="*60)
    print("Test: Multi-sheet Row Mapping Independence")
    print("="*60)

    test_file = Path("input/test_multisheet.xlsx")
    output_file = Path("output/test_multisheet_fixed.xlsx")
    create_test_multisheet_xlsx(test_file)

    config = CConfig("config.yaml")
    config.xlsx.filePath = str(test_file)
    config.xlsx.outputPath = str(output_file)
    config.xlsx.sheetName = ["s4_1", "s4_2"]

    xlsx = XLSXCore(config)

    # ===================================
    # Phase 1: Read both sheets
    # ===================================
    print("\n📖 Reading sheets...")
    jsonline_s4_1 = xlsx.readXlsx("s4_1")
    jsonline_s4_2 = xlsx.readXlsx("s4_2")

    print(f"   ✓ s4_1: {len(jsonline_s4_1.split(chr(10)))} lines")
    print(f"   ✓ s4_2: {len(jsonline_s4_2.split(chr(10)))} lines")

    # Verify row mappings are stored separately
    assert "s4_1" in xlsx.row_mappings, "s4_1 mapping not found"
    assert "s4_2" in xlsx.row_mappings, "s4_2 mapping not found"

    print(f"\n🔍 Row Mappings:")
    print(f"   s4_1: {xlsx.row_mappings['s4_1']}")
    print(f"   s4_2: {xlsx.row_mappings['s4_2']}")

    # Verify expected mappings
    expected_s4_1 = {1: 2, 2: 3, 3: 4}
    expected_s4_2 = {1: 3, 2: 5, 3: 6, 4: 7}

    assert xlsx.row_mappings["s4_1"] == expected_s4_1, \
        f"s4_1 mapping incorrect: {xlsx.row_mappings['s4_1']} != {expected_s4_1}"
    assert xlsx.row_mappings["s4_2"] == expected_s4_2, \
        f"s4_2 mapping incorrect: {xlsx.row_mappings['s4_2']} != {expected_s4_2}"

    print("   ✅ Row mappings are correct and independent!")

    # ===================================
    # Phase 2: Write translations
    # ===================================
    print("\n💾 Writing translations...")

    translations = {
        "s4_1": '''{"id":1,"dst":"สวัสดี"}
{"id":2,"dst":"เธอหัวเราะ"}
{"id":3,"dst":"ขอบคุณ"}''',
        "s4_2": '''{"id":1,"dst":"อรุณสวัสดิ์"}
{"id":2,"dst":"พระอาทิตย์ขึ้น"}
{"id":3,"dst":"ลาก่อน"}
{"id":4,"dst":"เธอจากไป"}'''
    }

    xlsx.writeMultipleSheets(translations)

    # ===================================
    # Phase 3: Verify output
    # ===================================
    print("\n🔍 Verifying output...")

    wb = load_workbook(output_file)

    # Verify s4_1 (should use its own mapping)
    ws1 = wb["s4_1"]
    target_col = config.xlsx.targetColumn
    headers = [str(cell.value) for cell in ws1[1]]
    col_idx = headers.index(target_col) + 1

    s4_1_translations = {
        2: "สวัสดี",      # id=1 → row 2
        3: "เธอหัวเราะ",   # id=2 → row 3
        4: "ขอบคุณ"        # id=3 → row 4
    }

    for row_num, expected_text in s4_1_translations.items():
        actual = ws1.cell(row=row_num, column=col_idx).value
        assert actual == expected_text, \
            f"s4_1 row {row_num}: expected '{expected_text}', got '{actual}'"
        print(f"   ✅ s4_1 row {row_num}: '{actual}' (correct)")

    # Verify s4_2 (should use its own mapping, not s4_1's)
    ws2 = wb["s4_2"]

    s4_2_translations = {
        3: "อรุณสวัสดิ์",    # id=1 → row 3 (NOT row 2!)
        5: "พระอาทิตย์ขึ้น", # id=2 → row 5 (NOT row 3!)
        6: "ลาก่อน",        # id=3 → row 6 (NOT row 4!)
        7: "เธอจากไป"       # id=4 → row 7
    }

    for row_num, expected_text in s4_2_translations.items():
        actual = ws2.cell(row=row_num, column=col_idx).value
        assert actual == expected_text, \
            f"s4_2 row {row_num}: expected '{expected_text}', got '{actual}'"
        print(f"   ✅ s4_2 row {row_num}: '{actual}' (correct)")

    wb.close()

    print("\n" + "="*60)
    print("✅ MULTI-SHEET BUG FIX VERIFIED!")
    print("="*60)
    print("Each sheet correctly uses its own row mapping.")
    print("Translations are written to the correct rows regardless")
    print("of processing order or row structure differences.")
    print("="*60)


def test_backwards_compatibility_single_sheet():
    """
    Verify that single-sheet workflow still works (backward compatibility).
    """
    print("\n" + "="*60)
    print("Test: Backward Compatibility (Single Sheet)")
    print("="*60)

    test_file = Path("input/test_multisheet.xlsx")
    output_file = Path("output/test_single_sheet.xlsx")
    create_test_multisheet_xlsx(test_file)

    config = CConfig("config.yaml")
    config.xlsx.filePath = str(test_file)
    config.xlsx.outputPath = str(output_file)
    config.xlsx.sheetName = ["s4_1"]

    xlsx = XLSXCore(config)

    # Read
    jsonline = xlsx.readXlsx("s4_1")
    print(f"   ✓ Read {len(jsonline.split(chr(10)))} lines")

    # Write
    translations = '''{"id":1,"dst":"สวัสดี"}
{"id":2,"dst":"เธอหัวเราะ"}
{"id":3,"dst":"ขอบคุณ"}'''

    xlsx.writeXlsx(translations, sheet_name="s4_1")
    print(f"   ✓ Written to {output_file}")

    # Verify
    wb = load_workbook(output_file)
    ws = wb["s4_1"]
    headers = [str(cell.value) for cell in ws[1]]
    col_idx = headers.index(config.xlsx.targetColumn) + 1

    actual = ws.cell(row=2, column=col_idx).value
    assert actual == "สวัสดี", f"Expected 'สวัสดี', got '{actual}'"

    wb.close()

    print("   ✅ Single-sheet workflow works correctly!")
    print("="*60)


def run_all_tests():
    """Run all multi-sheet bug fix tests"""
    print("\n" + "="*60)
    print("MULTI-SHEET ROW MAPPING BUG FIX TESTS")
    print("="*60)

    tests = [
        test_multisheet_row_mapping_independence,
        test_backwards_compatibility_single_sheet,
    ]

    failed = []

    for test in tests:
        try:
            test()
        except AssertionError as e:
            print(f"\n❌ Test failed: {test.__name__}")
            print(f"   Error: {e}")
            failed.append(test.__name__)
        except Exception as e:
            print(f"\n❌ Test error: {test.__name__}")
            print(f"   Error: {e}")
            import traceback
            traceback.print_exc()
            failed.append(test.__name__)

    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"Total tests: {len(tests)}")
    print(f"Passed: {len(tests) - len(failed)}")
    print(f"Failed: {len(failed)}")

    if failed:
        print("\n❌ Failed tests:")
        for name in failed:
            print(f"  - {name}")
        sys.exit(1)
    else:
        print("\n✅ All tests passed!")
        print("\n🎉 Multi-sheet row mapping bug is FIXED!")
        print("="*60)


if __name__ == "__main__":
    run_all_tests()
