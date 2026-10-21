"""Demo mode: a CSV file that mimics the small part of the gspread Worksheet API we use.
Enable with  use_mock = true  in secrets.toml (or the env var USE_MOCK=1)."""
import csv
import json
import os
import struct
import threading
import zlib
from pathlib import Path

from gspread.utils import a1_to_rowcol

import config as C
import storage

MOCK_CSV = Path(os.getenv("MOCK_CSV", "data/clients_mock.csv"))


def _with_check_digit(first8: str) -> str:
    """Build a valid 9-digit Israeli ID from 8 digits (so the demo IDs pass validation)."""
    total = sum((lambda n: n - 9 if n > 9 else n)(int(ch) * (1 + i % 2))
                for i, ch in enumerate(first8))
    return first8 + str((10 - total % 10) % 10)


def _demo_png(rgb: tuple, w: int = 240, h: int = 150) -> bytes:
    """A tiny valid PNG (solid colour) so the admin preview has something to show."""
    raw = b"".join(b"\x00" + bytes(rgb) * w for _ in range(h))

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


def _demo_rows() -> list[dict]:
    """Four sample clients covering every status (red / yellow / green)."""
    def received(cid, docs, approved):
        out = []
        for i, doc in enumerate(docs):
            path = storage.save_file(cid, doc, "demo.png", _demo_png((90 + 40 * i, 140, 190 - 30 * i)))
            out.append({"doc": doc, "files": [path], "time": "2026-10-15 09:30",
                        "approved": approved})
        return json.dumps(out)

    ids = [_with_check_digit(x) for x in ("31245678", "20458713", "30819264", "27650491")]
    return [
        {C.COL_ID: ids[0], C.COL_NAME: "דנה לוי", C.COL_PHONE: "050-1234567",
         C.COL_BTYPE: C.BUSINESS_TYPES[0], C.COL_STAGE: C.STAGES[0], C.COL_STATUS: C.WAITING,
         C.COL_MISSING: "צילום תעודת זהות, צילום שיק מבוטל", C.COL_RECEIVED: "[]"},
        {C.COL_ID: ids[1], C.COL_NAME: "יוסי כהן", C.COL_PHONE: "052-7654321",
         C.COL_BTYPE: C.BUSINESS_TYPES[1], C.COL_STAGE: C.STAGES[1], C.COL_STATUS: C.REVIEW,
         C.COL_MISSING: "", C.COL_RECEIVED: received(ids[1], ["טופס 106", "טופס 867", "קבלות"], False)},
        {C.COL_ID: ids[2], C.COL_NAME: "נועה מזרחי", C.COL_PHONE: "054-1112233",
         C.COL_BTYPE: C.BUSINESS_TYPES[0], C.COL_STAGE: C.STAGES[2], C.COL_STATUS: C.WAITING,
         C.COL_MISSING: "טופס 867, דפי חשבון בנק, קבלות",
         C.COL_RECEIVED: received(ids[2], ["צילום תעודת זהות"], True)},
        {C.COL_ID: ids[3], C.COL_NAME: "אבי פרץ", C.COL_PHONE: "053-9988776",
         C.COL_BTYPE: C.BUSINESS_TYPES[1], C.COL_STAGE: C.STAGES[1], C.COL_STATUS: C.DONE,
         C.COL_MISSING: "", C.COL_RECEIVED: received(ids[3], ["טופס 106", "טופס 867", "קבלות"], True)},
    ]


class MockWorksheet:
    """CSV-backed stand-in for gspread.Worksheet (row_values, get_all_values, update,
    batch_update, append_row). Thread-safe; every call re-reads the file."""

    def __init__(self, path: Path = MOCK_CSV):
        self.path = Path(path)
        self._lock = threading.RLock()
        if not self.path.exists():
            self.path.parent.mkdir(parents=True, exist_ok=True)
            rows = [C.COLUMNS] + [[r.get(c, "") for c in C.COLUMNS] for r in _demo_rows()]
            self._write(rows)

    # -- file helpers
    def _read(self) -> list[list[str]]:
        with open(self.path, newline="", encoding="utf-8-sig") as f:
            return [row for row in csv.reader(f)]

    def _write(self, rows: list[list[str]]) -> None:
        tmp = self.path.with_suffix(".tmp")
        with open(tmp, "w", newline="", encoding="utf-8-sig") as f:   # BOM → opens fine in Excel
            csv.writer(f).writerows(rows)
        os.replace(tmp, self.path)                                    # atomic swap

    @staticmethod
    def _put(rows, a1: str, values) -> None:
        r0, c0 = a1_to_rowcol(a1.split(":")[0])
        for i, vals in enumerate(values):
            while len(rows) < r0 + i:
                rows.append([])
            row = rows[r0 + i - 1]
            row.extend([""] * (c0 + len(vals) - 1 - len(row)))
            for j, v in enumerate(vals):
                row[c0 + j - 1] = "" if v is None else str(v)

    # -- gspread-compatible API
    def row_values(self, n: int) -> list[str]:
        with self._lock:
            rows = self._read()
            return rows[n - 1] if n <= len(rows) else []

    def get_all_values(self) -> list[list[str]]:
        with self._lock:
            return self._read()

    def update(self, range_name: str, values, value_input_option=None) -> None:
        with self._lock:
            rows = self._read()
            self._put(rows, range_name, values)
            self._write(rows)

    def batch_update(self, data, value_input_option=None) -> None:
        with self._lock:                       # one read + one write = atomic
            rows = self._read()
            for item in data:
                self._put(rows, item["range"], item["values"])
            self._write(rows)

    def append_row(self, values, value_input_option=None) -> None:
        with self._lock:
            rows = self._read()
            rows.append([str(v) for v in values])
            self._write(rows)
