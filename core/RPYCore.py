"""
RPY Processing Core for AstralSealTransl

Handles reading Ren'Py translate block files (.rpy) and writing
translations back to RPY format using JSONLine intermediate format.

Input RPY format (Ren'Py translate blocks):
    # game/s1_1.rpy:17
    translate eng s1_1_e0250921:

        # voice "daiji/s1_1/daiji_1_1_001.mp3"
        # daiji sad "original text" with dissolve
        voice "daiji/s1_1/daiji_1_1_001.mp3"
        daiji sad "original text" with dissolve

After writeRpy(), translated lines are replaced with translated text:
        voice "daiji/s1_1/daiji_1_1_001.mp3"
        daiji sad "translated text" with dissolve
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class TranslatableLine:
    """Represents a translatable dialogue/narration line in an RPY translate block."""
    json_id: int         # Sequential JSONLine ID (1, 2, 3, ...)
    file_line_idx: int   # Index in the raw file lines list
    name: str            # Character name (first word before the opening quote)
    src: str             # Source text (content inside quotes)
    pre_quote: str       # Everything up to and including the opening "
    post_quote: str      # From the closing " onwards (includes closing " and suffix like newline)


class RPYCore:
    """
    Core RPY processing engine.

    Converts Ren'Py translate block files to JSONLine format for translation,
    and writes translated JSONLine back to RPY files.

    Usage:
        rpy = RPYCore("input/s1_1.rpy", "output/s1_1.rpy")

        jsonline = rpy.readRpy()
        print(jsonline)
        # {"id":1,"name":"navigator_cutscene","src":"ชีวิตวัยรุ่น..."}

        translated = '{"id":1,"dst":"Youth life..."}'
        rpy.writeRpy(translated)
    """

    def __init__(self, input_path: str, output_path: str) -> None:
        """
        Initialize RPY processor.

        Args:
            input_path: Path to input .rpy file
            output_path: Path for translated output .rpy file
        """
        self.input_path = Path(input_path)
        self.output_path = Path(output_path)
        self._file_lines: List[str] = []
        self._id_to_tl: Dict[int, TranslatableLine] = {}

    def readRpy(self) -> str:
        """
        Read RPY file and convert translatable lines to JSONLine format.

        Parses all translate blocks, skips voice lines and comments,
        and extracts character name + source text from dialogue/narration lines.

        Returns:
            JSONLine string: {"id":1,"name":"character","src":"text"}

        Raises:
            FileNotFoundError: If RPY file doesn't exist
        """
        if not self.input_path.exists():
            raise FileNotFoundError(f"RPY file not found: {self.input_path}")

        with open(self.input_path, 'r', encoding='utf-8') as f:
            self._file_lines = f.readlines()

        self._id_to_tl = {}
        self._parse_blocks()

        return self._format_as_jsonline()

    def writeRpy(self, jsonline_input: str) -> None:
        """
        Write translated JSONLine back to RPY file.

        Replaces only the quoted text in each translatable line while
        preserving the full file structure (comments, block headers,
        voice lines, transitions, etc.).

        Args:
            jsonline_input: JSONLine string with translations
                {"id":1,"dst":"translated text"}

        Raises:
            ValueError: If readRpy() was not called first, or JSONLine is invalid
        """
        if not self._file_lines:
            raise ValueError("No RPY data loaded. Call readRpy() first.")

        translations = self._parse_jsonline(jsonline_input)

        # Work on a copy of the file lines
        lines = list(self._file_lines)

        written_count = 0
        for json_id, dst in translations.items():
            if json_id not in self._id_to_tl:
                print(f"⚠️  Warning: JSONLine ID {json_id} not found in mapping, skipping")
                continue

            tl = self._id_to_tl[json_id]
            lines[tl.file_line_idx] = tl.pre_quote + dst + tl.post_quote
            written_count += 1

        self.output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(self.output_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)

        print(f"✅ Written {written_count} translations to {self.output_path}")

    # ------------------------------------------------------------------ #
    # Internal helpers                                                     #
    # ------------------------------------------------------------------ #

    def _parse_blocks(self) -> None:
        """
        Iterate file lines, find translate blocks, extract translatable lines.

        A translate block looks like:
            translate eng BLOCK_ID:
            [blank]
                # commented original line(s)
                translated line(s)
            [blank or non-indented line]
        """
        json_id = 1
        i = 0

        while i < len(self._file_lines):
            raw = self._file_lines[i]
            stripped = raw.rstrip('\n')

            # Detect block header: "translate LANG BLOCK_ID:"
            if re.match(r'^translate\s+\w+\s+\w+\s*:', stripped):
                i += 1
                # Collect indented content lines
                while i < len(self._file_lines):
                    raw_content = self._file_lines[i]
                    content = raw_content.rstrip('\n')
                    inner = content.strip()

                    # Skip blank lines (appear after header and between content)
                    if not inner:
                        i += 1
                        continue

                    # End of block: non-indented non-blank line
                    if not content.startswith('    '):
                        break

                    # Skip comment lines (these are the originals)
                    if inner.startswith('#'):
                        i += 1
                        continue

                    # Skip voice lines
                    if re.match(r'^voice\s+"', inner):
                        i += 1
                        continue

                    # Translatable line with quoted text
                    if '"' in inner:
                        result = self._extract_parts(raw_content)
                        if result:
                            name, src, pre_quote, post_quote = result
                            tl = TranslatableLine(
                                json_id=json_id,
                                file_line_idx=i,
                                name=name,
                                src=src,
                                pre_quote=pre_quote,
                                post_quote=post_quote,
                            )
                            self._id_to_tl[json_id] = tl
                            json_id += 1

                    i += 1
            else:
                i += 1

    def _extract_parts(self, raw_line: str) -> Optional[Tuple[str, str, str, str]]:
        """
        Split a dialogue/narration line into its component parts.

        Args:
            raw_line: Raw file line, e.g. '    daiji sad "text" with dissolve\\n'

        Returns:
            Tuple (name, src, pre_quote, post_quote) where:
                name      = character name (first word before opening quote)
                src       = text content between quotes
                pre_quote = everything up to and including opening "
                post_quote= from closing " onwards (includes \\n if present)
            Returns None if no valid quoted string found.
        """
        first_q = raw_line.find('"')
        if first_q == -1:
            return None

        last_q = raw_line.rfind('"')
        if last_q == first_q:
            return None  # Only one quote character found

        pre_quote = raw_line[:first_q + 1]    # includes opening "
        src = raw_line[first_q + 1:last_q]    # text without quotes
        post_quote = raw_line[last_q:]         # includes closing " and trailing content

        # Character name = first word in the segment before the opening "
        pre_stripped = pre_quote.rstrip('"').strip()
        parts = pre_stripped.split()
        name = parts[0] if parts else ""

        return name, src, pre_quote, post_quote

    def _format_as_jsonline(self) -> str:
        """Convert stored TranslatableLine entries to JSONLine string."""
        lines = []
        for tl in sorted(self._id_to_tl.values(), key=lambda t: t.json_id):
            obj = {"id": tl.json_id, "name": tl.name, "src": tl.src}
            lines.append(json.dumps(obj, ensure_ascii=False))
        return "\n".join(lines)

    def _parse_jsonline(self, jsonline_input: str) -> Dict[int, str]:
        """
        Parse JSONLine translation string to {id: dst} dict.

        Args:
            jsonline_input: JSONLine string with {"id":N,"dst":"text"} per line

        Returns:
            Dict mapping json_id -> translated text

        Raises:
            ValueError: On malformed JSON or missing required fields
        """
        translations: Dict[int, str] = {}

        for line_num, line in enumerate(jsonline_input.strip().split('\n'), start=1):
            if not line.strip():
                continue

            try:
                data = json.loads(line)
            except json.JSONDecodeError as e:
                raise ValueError(
                    f"Invalid JSON at line {line_num}: {line}\nError: {e}"
                )

            if 'id' not in data:
                raise ValueError(f"Missing 'id' field at line {line_num}: {line}")
            if 'dst' not in data:
                raise ValueError(f"Missing 'dst' field at line {line_num}: {line}")

            translations[int(data['id'])] = str(data['dst'])

        return translations
