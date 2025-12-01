"""
XLSX Processing Core for AstralSealTransl

Handles reading visual novel scripts from XLSX files and writing
translations back to XLSX format using JSONLine intermediate format.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass

from openpyxl import load_workbook
from openpyxl.worksheet.worksheet import Worksheet
from openpyxl.workbook.workbook import Workbook

from core.CConfig import CConfig, XLSXConfig


@dataclass
class RowData:
    """Single row data structure"""
    row_id: int
    name: str
    src: str


class XLSXCore:
    """
    Core XLSX processing engine.

    Converts XLSX visual novel scripts to JSONLine format for translation,
    and writes translated JSONLine back to XLSX files.

    Usage:
        config = CConfig("config.yaml")
        xlsx = XLSXCore(config)

        jsonline = xlsx.readXlsx()
        print(jsonline)

        translated = '{"id":1,"dst":"แปลภาษาไทย"}'
        xlsx.writeXlsx(translated)
    """

    def __init__(self, config: CConfig) -> None:
        """
        Initialize XLSX processor.

        Args:
            config: Configuration instance with xlsx settings
        """
        self.config = config
        self.xlsx_config = config.xlsx

    def readXlsx(self) -> str:
        """
        Read XLSX file and convert to JSONLine format.

        Returns:
            JSONLine string with format: {"id":1,"name":"...","src":"..."}

        Raises:
            FileNotFoundError: If XLSX file doesn't exist
            ValueError: If sheet or columns don't exist
        """
        file_path = Path(self.xlsx_config.filePath)

        self._validate_file_exists(file_path)

        workbook = load_workbook(file_path, read_only=True, data_only=True)
        sheet = self._get_sheet(workbook, self.xlsx_config.sheetName)

        if self.xlsx_config.validateColumns:
            self._validate_columns(sheet)

        rows_data = self._extract_rows(sheet)
        jsonline = self._format_as_jsonline(rows_data)

        workbook.close()
        return jsonline

    def writeXlsx(self, jsonline_input: str) -> None:
        """
        Write translated JSONLine to XLSX file.

        Args:
            jsonline_input: JSONLine string with format: {"id":1,"dst":"..."}

        Raises:
            FileNotFoundError: If source XLSX doesn't exist
            ValueError: If JSONLine format is invalid
        """
        translations = self._parse_jsonline(jsonline_input)

        source_path = Path(self.xlsx_config.filePath)
        self._validate_file_exists(source_path)

        workbook = load_workbook(source_path)
        sheet = self._get_sheet(workbook, self.xlsx_config.sheetName)

        column_index = self._get_column_index(sheet, self.xlsx_config.targetColumn)

        written_count = self._write_translations(sheet, column_index, translations)

        output_path = Path(self.xlsx_config.outputPath)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        workbook.save(output_path)
        workbook.close()

        print(f"✅ Written {written_count} translations to {output_path}")

    def _validate_file_exists(self, file_path: Path) -> None:
        """Validate that file exists"""
        if not file_path.exists():
            raise FileNotFoundError(f"XLSX file not found: {file_path}")

    def _get_sheet(self, workbook: Workbook, sheet_name: str) -> Worksheet:
        """Get worksheet by name with validation"""
        if sheet_name not in workbook.sheetnames:
            available = ", ".join(workbook.sheetnames)
            raise ValueError(
                f"Sheet '{sheet_name}' not found. "
                f"Available sheets: {available}"
            )
        return workbook[sheet_name]

    def _validate_columns(self, sheet: Worksheet) -> None:
        """Validate that required columns exist in sheet"""
        header_row = next(sheet.iter_rows(min_row=1, max_row=1, values_only=True))
        headers = [str(h) if h else "" for h in header_row]

        required = [
            self.xlsx_config.nameColumn,
            self.xlsx_config.srcColumn
        ]

        missing = [col for col in required if col not in headers]

        if missing:
            raise ValueError(
                f"Required columns not found: {', '.join(missing)}. "
                f"Available columns: {', '.join(headers)}"
            )

    def _get_column_index(self, sheet: Worksheet, column_name: str) -> int:
        """Get column index by name (1-based)"""
        header_row = next(sheet.iter_rows(min_row=1, max_row=1, values_only=True))
        headers = [str(h) if h else "" for h in header_row]

        if column_name not in headers:
            raise ValueError(
                f"Column '{column_name}' not found. "
                f"Available: {', '.join(headers)}"
            )

        return headers.index(column_name) + 1

    def _extract_rows(self, sheet: Worksheet) -> List[RowData]:
        """Extract data rows from worksheet"""
        header_row = next(sheet.iter_rows(min_row=1, max_row=1, values_only=True))
        headers = [str(h) if h else "" for h in header_row]

        name_index = headers.index(self.xlsx_config.nameColumn)
        src_index = headers.index(self.xlsx_config.srcColumn)

        rows_data = []
        row_id = 1

        for row in sheet.iter_rows(min_row=2, values_only=True):
            name_value = row[name_index] if row[name_index] else ""
            src_value = row[src_index] if row[src_index] else ""

            rows_data.append(RowData(
                row_id=row_id,
                name=str(name_value),
                src=str(src_value)
            ))

            row_id += 1

        return rows_data

    def _format_as_jsonline(self, rows_data: List[RowData]) -> str:
        """Convert rows to JSONLine format"""
        lines = []

        for row in rows_data:
            json_obj = {
                "id": row.row_id,
                "name": row.name,
                "src": row.src
            }
            lines.append(json.dumps(json_obj, ensure_ascii=False))

        return "\n".join(lines)

    def _parse_jsonline(self, jsonline_input: str) -> Dict[int, str]:
        """
        Parse JSONLine input to translation dictionary.

        Returns:
            Dict mapping row_id to translated text

        Raises:
            ValueError: If JSON format is invalid or missing required keys
        """
        translations = {}

        for line_num, line in enumerate(jsonline_input.strip().split('\n'), start=1):
            if not line.strip():
                continue

            try:
                data = json.loads(line)
            except json.JSONDecodeError as e:
                raise ValueError(
                    f"Invalid JSON at line {line_num}: {line}\n"
                    f"Error: {e}"
                )

            if 'id' not in data:
                raise ValueError(f"Missing 'id' at line {line_num}: {line}")
            if 'dst' not in data:
                raise ValueError(f"Missing 'dst' at line {line_num}: {line}")

            row_id = data['id']
            translation = data['dst']

            if not isinstance(row_id, int):
                raise ValueError(f"Invalid 'id' type at line {line_num}: expected int")

            translations[row_id] = str(translation)

        return translations

    def _write_translations(
        self,
        sheet: Worksheet,
        column_index: int,
        translations: Dict[int, str]
    ) -> int:
        """
        Write translations to worksheet.

        Returns:
            Number of rows written
        """
        written_count = 0

        for row_num in range(2, sheet.max_row + 1):
            row_id = row_num - 1

            if row_id in translations:
                sheet.cell(row=row_num, column=column_index).value = translations[row_id]
                written_count += 1
            else:
                print(f"⚠️  Warning: ID {row_id} not found in translations, skipping")

        return written_count
