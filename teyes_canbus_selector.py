# teyes_canbus_selector_v4.py
# ------------------------------------------
# Run: python teyes_canbus_selector_v4.py
#
# Dependencies:
#   pip install PySide6
# ------------------------------------------

import sys
import importlib
import importlib.util

# ── Dependency check ─────────────────────────────────────────────────────────

REQUIRED = {
    "PySide6": "PySide6",
}

missing = []
for module, package in REQUIRED.items():
    if importlib.util.find_spec(module) is None:
        missing.append(package)

if missing:
    print("=" * 60)
    print("ERROR: Required dependencies are not installed!")
    print("=" * 60)
    print()
    print("Missing packages:", ", ".join(missing))
    print()
    print("Installation options:")
    print()
    print("  1) Standard pip install:")
    print(f"       pip install {' '.join(missing)}")
    print()
    print("  2) If you have multiple Python versions, specify explicitly:")
    print(f"       python3 -m pip install {' '.join(missing)}")
    print()
    print("  3) Install for current user only (no admin/sudo rights needed):")
    print(f"       pip install --user {' '.join(missing)}")
    print()
    print("  4) Inside a virtual environment (recommended):")
    print("       python -m venv venv")
    print("       # Windows:")
    print("       venv\\Scripts\\activate")
    print("       # Linux / macOS:")
    print("       source venv/bin/activate")
    print(f"       pip install {' '.join(missing)}")
    print()
    print("  5) Via conda (Anaconda / Miniconda):")
    print(f"       conda install -c conda-forge {' '.join(missing)}")
    print()
    print("Re-run the script after installation.")
    print("=" * 60)
    sys.exit(1)

# ── Main code ─────────────────────────────────────────────────────────────────

import os
import sqlite3

from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel,
    QVBoxLayout, QHBoxLayout, QComboBox,
    QTextEdit, QLineEdit, QPushButton,
    QMessageBox
)
from PySide6.QtCore import Qt

DB_FILE = "canbus.db"


def check_database() -> bool:
    """
    Checks whether the database file exists and has the correct structure.
    Shows a dialog with instructions if the file is missing or corrupted.
    Returns True if everything is fine, False if startup should be aborted.
    """
    # ── 1. Does the file exist? ───────────────────────────────────────────────
    if not os.path.isfile(DB_FILE):
        msg = QMessageBox()
        msg.setWindowTitle("Database not found")
        msg.setIcon(QMessageBox.Icon.Critical)
        msg.setText(f"File <b>{DB_FILE}</b> was not found.")
        msg.setInformativeText(
            "Place <b>canbus.db</b> in the same folder as the script.<br><br>"
            "How to get the database:<br>"
            "1. Open <a href='https://cc3.teyes.cn/apk3/#/'>cc3.teyes.cn/apk3</a><br>"
            "2. Download one of the files <b>* Update.apk … Canbus.apk</b><br>"
            "3. Rename the APK to <b>.zip</b> and extract it<br>"
            "4. Copy <b>assets/canbus.db</b> next to the script"
        )
        msg.setTextFormat(Qt.TextFormat.RichText)
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg.exec()
        return False

    # ── 2. Is the file a valid SQLite database? ───────────────────────────────
    try:
        conn = sqlite3.connect(DB_FILE)
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        conn.close()

        required_tables = {"canbus_company", "canbus_carset", "canbus_cartype", "canbus_canbox"}
        missing_tables  = required_tables - tables

        if missing_tables:
            msg = QMessageBox()
            msg.setWindowTitle("Invalid database structure")
            msg.setIcon(QMessageBox.Icon.Warning)
            msg.setText(f"File <b>{DB_FILE}</b> was found but has an unexpected structure.")
            msg.setInformativeText(
                "Missing tables:<br>"
                + "".join(f"&nbsp;&nbsp;• <b>{t}</b><br>" for t in sorted(missing_tables))
                + "<br>Make sure you extracted the correct file from the Teyes APK."
            )
            msg.setTextFormat(Qt.TextFormat.RichText)
            msg.setStandardButtons(QMessageBox.StandardButton.Ok)
            msg.exec()
            return False

    except sqlite3.DatabaseError as e:
        msg = QMessageBox()
        msg.setWindowTitle("Database file is corrupted")
        msg.setIcon(QMessageBox.Icon.Critical)
        msg.setText(f"Failed to open <b>{DB_FILE}</b>.")
        msg.setInformativeText(
            f"SQLite error: {e}<br><br>"
            "The file may be corrupted or is not a valid SQLite database.<br>"
            "Try extracting the file from the APK again."
        )
        msg.setTextFormat(Qt.TextFormat.RichText)
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg.exec()
        return False

    return True


# Language → field suffix mapping for canbus_canbox
LANG_SUFFIX = {
    "English": "_en",
    "Chinese": "_ch",
    "Taiwan":  "_tw",
    "Default": "",    # falls back to the `name` column
}


class CanbusApp(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("CANBUS Selector V4")
        self.resize(850, 640)

        self.conn = sqlite3.connect(DB_FILE)
        self.conn.row_factory = sqlite3.Row

        self.lang_box = QComboBox()
        self.lang_box.addItems(list(LANG_SUFFIX.keys()))

        self.brand_box = QComboBox()
        self.model_box = QComboBox()
        self.type_box  = QComboBox()
        self.trim_box  = QComboBox()

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search CANBUS code (number)")

        self.btn_find = QPushButton("Find")

        self.result = QTextEdit()
        self.result.setReadOnly(True)

        self._init_ui()
        self.load_brands()

    # ── UI ───────────────────────────────────────────────────────────────────

    def _init_ui(self):
        layout = QVBoxLayout()

        def row(title, widget):
            r = QHBoxLayout()
            lbl = QLabel(title)
            lbl.setFixedWidth(90)
            r.addWidget(lbl)
            r.addWidget(widget)
            layout.addLayout(r)

        row("Language", self.lang_box)
        row("Brand",    self.brand_box)
        row("Model",    self.model_box)
        row("Type",     self.type_box)
        row("Trim",     self.trim_box)

        sr = QHBoxLayout()
        sr.addWidget(self.search_box)
        sr.addWidget(self.btn_find)
        layout.addLayout(sr)

        layout.addWidget(self.result)
        self.setLayout(layout)

        # Signals
        self.lang_box.currentIndexChanged.connect(self._on_lang_change)
        self.brand_box.currentIndexChanged.connect(self.load_models)
        self.model_box.currentIndexChanged.connect(self.load_types)
        self.type_box.currentIndexChanged.connect(self.load_trims)
        self.trim_box.currentIndexChanged.connect(self.show_result)
        self.btn_find.clicked.connect(self.find_code)

    # ── Language change: reload all dropdowns ────────────────────────────────

    def _on_lang_change(self):
        self.load_brands()

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _lang(self) -> str:
        return self.lang_box.currentText()

    def _field(self, base: str) -> str:
        """
        Returns the column name for the current language.
        base is the field prefix, e.g. 'canbus_company_name'.
        For Default, returns 'name' (the base column without a suffix).
        """
        lang   = self._lang()
        suffix = LANG_SUFFIX.get(lang, "")
        return base + suffix if suffix else "name"

    @staticmethod
    def _coalesce(alias: str, field: str, fallback: str = "name") -> str:
        """Returns a SQL COALESCE expression that falls back to `fallback` for empty values."""
        return f"COALESCE(NULLIF({alias}.{field}, ''), {alias}.{fallback})"

    def _localized_canbox_field(self) -> str:
        """
        Returns the canbus_canbox column name that corresponds
        to the currently selected UI language.
        """
        lang = self._lang()
        mapping = {
            "English": "canbus_canbox_en",
            "Chinese": "canbus_canbox_ch",
            "Taiwan":  "canbus_canbox_tw",
            "Default": "name",
        }
        return mapping.get(lang, "name")

    def _format_result(self, row, found_by_search: bool = False) -> str:
        """Formats the result text according to the current language."""
        lang_field = self._localized_canbox_field()
        local_name = row[lang_field] if row[lang_field] else row["name"]
        apk_code   = row["id_value"] & 0xFFFF

        header = f"FOUND CODE: {row['id_value']}" if found_by_search else "RESULT"

        lines = [
            header,
            "",
            f"Local name   : {local_name}",
            f"Base name    : {row['name']}",
            f"English      : {row['canbus_canbox_en']}",
            f"Chinese      : {row['canbus_canbox_ch']}",
            "",
            f"CANBUS CODE  : {row['id_value']}",
            f"APK CODE     : {apk_code}",
            f"Visible(disp): {row['disp']}",
            "",
            "IDs:",
            f"  Company  = {row['company_id']}",
            f"  Carset   = {row['carset_id']}",
            f"  Type     = {row['cartype_id']}",
        ]
        return "\n".join(lines)

    # ── Dropdown loaders ─────────────────────────────────────────────────────

    def load_brands(self):
        self.brand_box.blockSignals(True)
        self.brand_box.clear()

        fld   = self._field("canbus_company_name")
        title = self._coalesce("c", fld)

        sql = f"""
        SELECT DISTINCT c.id, {title} AS title
        FROM canbus_company c
        JOIN canbus_canbox cb ON cb.company_id = c.id
        ORDER BY title
        """
        for r in self.conn.execute(sql).fetchall():
            self.brand_box.addItem(r["title"], r["id"])

        self.brand_box.blockSignals(False)
        self.load_models()

    def load_models(self):
        self.model_box.blockSignals(True)
        self.model_box.clear()

        brand_id = self.brand_box.currentData()
        if not brand_id:
            self.model_box.blockSignals(False)
            return

        fld   = self._field("canbus_carset_name")
        title = self._coalesce("cs", fld)

        sql = f"""
        SELECT DISTINCT cs.id, {title} AS title
        FROM canbus_carset cs
        JOIN canbus_canbox cb ON cb.carset_id = cs.id
        WHERE cb.company_id = ?
        ORDER BY title
        """
        for r in self.conn.execute(sql, (brand_id,)).fetchall():
            self.model_box.addItem(r["title"], r["id"])

        self.model_box.blockSignals(False)
        self.load_types()

    def load_types(self):
        self.type_box.blockSignals(True)
        self.type_box.clear()

        brand_id = self.brand_box.currentData()
        model_id = self.model_box.currentData()

        if not brand_id or not model_id:
            self.type_box.blockSignals(False)
            return

        fld   = self._field("canbus_cartype")
        title = self._coalesce("ct", fld)

        sql = f"""
        SELECT DISTINCT ct.id, {title} AS title
        FROM canbus_cartype ct
        JOIN canbus_canbox cb ON cb.cartype_id = ct.id
        WHERE cb.company_id = ?
          AND cb.carset_id = ?
        ORDER BY title
        """
        for r in self.conn.execute(sql, (brand_id, model_id)).fetchall():
            self.type_box.addItem(r["title"], r["id"])

        self.type_box.blockSignals(False)
        self.load_trims()

    def load_trims(self):
        self.trim_box.blockSignals(True)
        self.trim_box.clear()

        brand_id = self.brand_box.currentData()
        model_id = self.model_box.currentData()
        type_id  = self.type_box.currentData()

        if not brand_id or not model_id or not type_id:
            self.trim_box.blockSignals(False)
            return

        fld   = self._field("canbus_canbox")
        title = self._coalesce("cb", fld)

        sql = f"""
        SELECT cb.id, {title} AS title
        FROM canbus_canbox cb
        WHERE cb.company_id = ?
          AND cb.carset_id  = ?
          AND cb.cartype_id = ?
        ORDER BY title
        """
        for r in self.conn.execute(sql, (brand_id, model_id, type_id)).fetchall():
            self.trim_box.addItem(r["title"], r["id"])

        self.trim_box.blockSignals(False)
        self.show_result()

    # ── Result display ───────────────────────────────────────────────────────

    def show_result(self):
        trim_id = self.trim_box.currentData()
        if not trim_id:
            return

        row = self.conn.execute(
            "SELECT * FROM canbus_canbox WHERE id = ? LIMIT 1", (trim_id,)
        ).fetchone()

        if row:
            self.result.setText(self._format_result(row))

    # ── Search by code (language-aware) ─────────────────────────────────────

    def find_code(self):
        code = self.search_box.text().strip()

        if not code.isdigit():
            self.result.setText("Please enter a numeric CANBUS code.")
            return

        row = self.conn.execute(
            "SELECT * FROM canbus_canbox WHERE id_value = ? LIMIT 1", (code,)
        ).fetchone()

        if row:
            self.result.setText(self._format_result(row, found_by_search=True))
        else:
            self.result.setText(f"Code {code} was not found in the database.")


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app = QApplication(sys.argv)

    if not check_database():
        sys.exit(1)

    win = CanbusApp()
    win.show()
    sys.exit(app.exec())