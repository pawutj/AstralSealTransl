## 1. เพิ่ม Config.yaml

```yaml
xlsx:
    filePath: "/input/jp_script.xlsx"       # Input file path
    outputPath: "/output/translated.xlsx"   # Output file path
    nameColumn: who_talk                    # Column ชื่อตัวละคร
    srcColumn: talk                         # Column ต้นฉบับ
    targetColumn: talk_jp                   # Column แปล
    sheetName: "s4_1"                       # Sheet name (string, อนาคตรองรับ array)
    validateColumns: true                   # ตรวจสอบ columns ก่อนประมวลผล
```

---

## 2. สร้าง core/XLSXCore.py

### Method 1: readXlsx()

**Input**: ไม่รับ parameter (อ่านจาก config.yaml)

**Output**: String JSONLine format

**Logic**:
1. อ่าน config: `filePath`, `sheetName`, `nameColumn`, `srcColumn`
2. เปิด XLSX ด้วย `openpyxl` หรือ `pandas`
3. **Validate**:
   - ✅ File exists
   - ✅ Sheet exists
   - ✅ Columns exist (`nameColumn`, `srcColumn`)
   - ❌ ถ้า fail → `raise ValueError` พร้อม error message
4. Loop แต่ละ row (skip header):
   - `id`: Auto-increment จาก row number (เริ่ม 1)
   - `name`: ค่าจาก `nameColumn` → **ถ้าว่าง ใส่ `""`**
   - `src`: ค่าจาก `srcColumn` → **ถ้าว่าง ใส่ `""`**
5. แปลงเป็น JSONLine (แต่ละบรรทัด = 1 JSON object)
6. Return string

**Example Output**:
```json
{"id":1,"name":"Reika","src":"ごめんなさい、こんな夕方に呼び出して"}
{"id":2,"name":"","src":"その声は普段とは違い、柔らかく耳に響いた"}
{"id":3,"name":"Reika","src":"私、もう決めたの"}
{"id":4,"name":"Reika","src":"今日、どうしてもあなたに伝えたいことがある"}
{"id":5,"name":"","src":"その瞳からは強い情熱が伝わってきた"}
{"id":6,"name":"","src":"ついに来たのだ。僕の時が"}
{"id":7,"name":"Reika","src":"ユウマ…"}
{"id":8,"name":"Reika","src":"私…"}
{"id":9,"name":"Reika","src":"私………"}
{"id":10,"name":"","src":"僕の心臓はこれまでにないほど激しく鼓動していた"}
{"id":11,"name":"","src":"ああ、ついに僕の青春が花開こうとしている"}
{"id":12,"name":"","src":"さあ、僕に告白してくれ！"}
{"id":13,"name":"Reika","src":"いつになったらお金を返すのよ！！！"}
```

**Error Handling**:
- `FileNotFoundError` → "XLSX file not found: {filePath}"
- `ValueError` → "Sheet '{sheetName}' not found"
- `ValueError` → "Column '{nameColumn}' or '{srcColumn}' not found"

---

### Method 2: writeXlsx(jsonline_input: str)

**Input**: String JSONLine format
```json
{"id":1,"target":"ขอโทษนะที่เรียกมาตอนเย็นแบบนี้"}
{"id":2,"target":"เสียงนั้นแตกต่างจากปกติ ดังกังวานในหูอย่างนุ่มนวล"}
```

**Output**: ไฟล์ XLSX ที่ `outputPath`

**Logic**:
1. **Validate JSON schema**:
   - ✅ แต่ละบรรทัดต้องเป็น valid JSON
   - ✅ มี key `id` (int) และ `target` (string)
   - ❌ ถ้า invalid → `raise ValueError` พร้อม error message
2. Parse JSONLine → `Dict[id: target]`
3. อ่าน original XLSX จาก `filePath`
4. Copy ทั้งหมด → workbook ใหม่
5. Loop แต่ละ row:
   - Match `id` (row number)
   - เขียน `target` ลง column `targetColumn`
   - **ถ้า ID ไม่เจอใน input → skip + log warning**
6. บันทึกเป็นไฟล์ใหม่ที่ `outputPath`
7. Log: จำนวน rows ที่เขียนสำเร็จ

**Error Handling**:
- `JSONDecodeError` → "Invalid JSON at line {n}: {line}"
- `ValueError` → "Missing 'id' or 'target' at line {n}"
- `FileNotFoundError` → "Original XLSX not found: {filePath}"
- `Warning` → "ID {id} not found in original file, skipping"

---

## 3. Testing Checklist

- [ ] อ่าน XLSX ที่มี `nameColumn` ว่าง → `"name": ""`
- [ ] อ่าน XLSX ที่มี `srcColumn` ว่าง → `"src": ""`
- [ ] Error: ไฟล์ไม่มี → FileNotFoundError
- [ ] Error: sheet ไม่มี → ValueError
- [ ] Error: column ไม่มี → ValueError
- [ ] เขียน JSONLine valid → สำเร็จ
- [ ] เขียน JSONLine invalid JSON → JSONDecodeError
- [ ] เขียน JSONLine ขาด key → ValueError
- [ ] เขียน ID ไม่มีใน original → log warning + skip
- [ ] ตรวจสอบ output file ที่ `outputPath`

