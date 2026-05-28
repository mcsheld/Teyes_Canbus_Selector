# teyes_canbus_selector_v3.py
# ------------------------------------------
# pip install PySide6
# ------------------------------------------

import sys
import sqlite3

from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel,
    QVBoxLayout, QHBoxLayout, QComboBox,
    QTextEdit, QLineEdit, QPushButton
)

DB_FILE = "canbus.db"


class CanbusApp(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("CANBUS Selector V3")
        self.resize(850, 620)

        self.conn = sqlite3.connect(DB_FILE)
        self.conn.row_factory = sqlite3.Row

        self.lang_box = QComboBox()
        self.lang_box.addItems(["English", "Chinese", "Taiwan", "Default"])

        self.brand_box = QComboBox()
        self.model_box = QComboBox()
        self.type_box = QComboBox()
        self.trim_box = QComboBox()

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search CANBUS code")

        self.btn_find = QPushButton("Find")

        self.result = QTextEdit()
        self.result.setReadOnly(True)

        self.init_ui()
        self.load_brands()

    # ---------------- UI ----------------

    def init_ui(self):
        layout = QVBoxLayout()

        def row(title, widget):
            r = QHBoxLayout()
            r.addWidget(QLabel(title))
            r.addWidget(widget)
            layout.addLayout(r)

        row("Language", self.lang_box)
        row("Brand", self.brand_box)
        row("Model", self.model_box)
        row("Type", self.type_box)
        row("Trim", self.trim_box)

        sr = QHBoxLayout()
        sr.addWidget(self.search_box)
        sr.addWidget(self.btn_find)
        layout.addLayout(sr)

        layout.addWidget(self.result)

        self.setLayout(layout)

        # events
        self.lang_box.currentIndexChanged.connect(self.reload_all)
        self.brand_box.currentIndexChanged.connect(self.load_models)
        self.model_box.currentIndexChanged.connect(self.load_types)
        self.type_box.currentIndexChanged.connect(self.load_trims)
        self.trim_box.currentIndexChanged.connect(self.show_result)

        self.btn_find.clicked.connect(self.find_code)

    # ---------------- Helpers ----------------

    def field(self, base):
        lang = self.lang_box.currentText()

        if lang == "English":
            return base + "_en"
        elif lang == "Chinese":
            return base + "_ch"
        elif lang == "Taiwan":
            return base + "_tw"
        else:
            return "name"

    def title_expr(self, alias, field, fallback="name"):
        return f"COALESCE(NULLIF({alias}.{field}, ''), {alias}.{fallback})"

    # ---------------- Loaders ----------------

    def reload_all(self):
        self.load_brands()

    def load_brands(self):
        self.brand_box.clear()

        fld = self.field("canbus_company_name")
        title = self.title_expr("c", fld)

        sql = f"""
        SELECT DISTINCT c.id, {title} AS title
        FROM canbus_company c
        JOIN canbus_canbox cb ON cb.company_id = c.id
        ORDER BY title
        """

        rows = self.conn.execute(sql).fetchall()

        for r in rows:
            self.brand_box.addItem(r["title"], r["id"])

        self.load_models()

    def load_models(self):
        self.model_box.clear()

        brand_id = self.brand_box.currentData()
        if not brand_id:
            return

        fld = self.field("canbus_carset_name")
        title = self.title_expr("cs", fld)

        sql = f"""
        SELECT DISTINCT cs.id, {title} AS title
        FROM canbus_carset cs
        JOIN canbus_canbox cb ON cb.carset_id = cs.id
        WHERE cb.company_id = ?
        ORDER BY title
        """

        rows = self.conn.execute(sql, (brand_id,)).fetchall()

        for r in rows:
            self.model_box.addItem(r["title"], r["id"])

        self.load_types()

    def load_types(self):
        self.type_box.clear()

        brand_id = self.brand_box.currentData()
        model_id = self.model_box.currentData()

        if not brand_id or not model_id:
            return

        fld = self.field("canbus_cartype")
        title = self.title_expr("ct", fld)

        sql = f"""
        SELECT DISTINCT ct.id, {title} AS title
        FROM canbus_cartype ct
        JOIN canbus_canbox cb ON cb.cartype_id = ct.id
        WHERE cb.company_id = ?
          AND cb.carset_id = ?
        ORDER BY title
        """

        rows = self.conn.execute(sql, (brand_id, model_id)).fetchall()

        for r in rows:
            self.type_box.addItem(r["title"], r["id"])

        self.load_trims()

    def load_trims(self):
        self.trim_box.clear()

        brand_id = self.brand_box.currentData()
        model_id = self.model_box.currentData()
        type_id = self.type_box.currentData()

        if not brand_id or not model_id or not type_id:
            return

        fld = self.field("canbus_canbox")
        title = self.title_expr("cb", fld)

        sql = f"""
        SELECT cb.id, {title} AS title
        FROM canbus_canbox cb
        WHERE cb.company_id = ?
          AND cb.carset_id = ?
          AND cb.cartype_id = ?
        ORDER BY title
        """

        rows = self.conn.execute(
            sql, (brand_id, model_id, type_id)
        ).fetchall()

        for r in rows:
            self.trim_box.addItem(r["title"], r["id"])

        self.show_result()

    # ---------------- Result ----------------

    def show_result(self):
        trim_id = self.trim_box.currentData()

        if not trim_id:
            return

        sql = """
        SELECT *
        FROM canbus_canbox
        WHERE id = ?
        LIMIT 1
        """

        row = self.conn.execute(sql, (trim_id,)).fetchone()

        if row:
            self.result.setText(
                f"""
CANBUS CODE : {row['id_value']}
In APK CODE : {row['id_value'] & 0xFFFF}

Display Name: {row['name']}
EN Code     : {row['canbus_canbox_en']}
Chinese     : {row['canbus_canbox_ch']}
Visible     : {row['disp']}

IDs:
Company = {row['company_id']}
Carset  = {row['carset_id']}
Type    = {row['cartype_id']}
"""
            )

    # ---------------- Search ----------------

    def find_code(self):
        code = self.search_box.text().strip()

        if not code.isdigit():
            return

        sql = """
        SELECT *
        FROM canbus_canbox
        WHERE id_value = ?
        LIMIT 1
        """

        row = self.conn.execute(sql, (code,)).fetchone()

        if row:
            self.result.setText(
                f"""
FOUND CODE: {code}

Name    : {row['name']}
EN Code : {row['canbus_canbox_en']}
Chinese : {row['canbus_canbox_ch']}
"""
            )
        else:
            self.result.setText("Nothing found.")

# ------------------------------------------

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = CanbusApp()
    win.show()
    sys.exit(app.exec())