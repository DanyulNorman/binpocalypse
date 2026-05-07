#!/usr/bin/env python3
"""
BinTracker - Inventory Management Server
Runs on theserverofdoom, port 8081
"""

import json
import sqlite3
import os
import re
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "inventory.db")
HTML_PATH = os.path.join(os.path.dirname(__file__), "inventory.html")


def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS bins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            number TEXT UNIQUE NOT NULL,
            label TEXT NOT NULL,
            location TEXT DEFAULT '',
            notes TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bin_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            qty INTEGER DEFAULT 1,
            description TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (bin_id) REFERENCES bins(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS checkouts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id INTEGER NOT NULL,
            note TEXT DEFAULT '',
            checked_out_at TEXT DEFAULT (datetime('now')),
            checked_in_at TEXT,
            FOREIGN KEY (item_id) REFERENCES items(id) ON DELETE CASCADE
        );
    """)
    conn.commit()
    conn.close()


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def next_bin_number():
    conn = get_db()
    row = conn.execute("SELECT number FROM bins ORDER BY CAST(number AS INTEGER) DESC LIMIT 1").fetchone()
    conn.close()
    if row:
        try:
            return str(int(row["number"]) + 1).zfill(3)
        except:
            return "001"
    return "001"


def next_bin_number_conn(conn):
    """Use existing connection — keeps numbers sequential during bulk import."""
    row = conn.execute("SELECT number FROM bins ORDER BY CAST(number AS INTEGER) DESC LIMIT 1").fetchone()
    if row:
        try:
            return str(int(row["number"]) + 1).zfill(3)
        except:
            return "001"
    return "001"


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {format % args}")

    def send_json(self, data, status=200):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(body))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def send_html(self):
        with open(HTML_PATH, "rb") as f:
            body = f.read()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def read_body(self):
        length = int(self.headers.get("Content-Length", 0))
        return json.loads(self.rfile.read(length)) if length else {}

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        qs = parse_qs(parsed.query)

        if path == "/":
            self.send_html()

        elif path == "/api/bins":
            conn = get_db()
            bins = [dict(r) for r in conn.execute("""
                SELECT b.*, COUNT(DISTINCT i.id) as item_count,
                    COUNT(DISTINCT CASE WHEN c.checked_in_at IS NULL AND c.id IS NOT NULL THEN c.id END) as checked_out_count
                FROM bins b 
                LEFT JOIN items i ON i.bin_id = b.id
                LEFT JOIN checkouts c ON c.item_id = i.id AND c.checked_in_at IS NULL
                GROUP BY b.id ORDER BY CAST(b.number AS INTEGER)
            """).fetchall()]
            for b in bins:
                previews = conn.execute(
                    "SELECT name, qty FROM items WHERE bin_id=? ORDER BY name LIMIT 3", (b['id'],)
                ).fetchall()
                b['item_preview'] = [f"{r['name']}{' ×'+str(r['qty']) if r['qty']>1 else ''}" for r in previews]
            conn.close()
            self.send_json(bins)

        elif path == "/api/next-number":
            self.send_json({"number": next_bin_number()})

        elif re.match(r"^/api/bins/(\d+)$", path):
            bin_id = re.match(r"^/api/bins/(\d+)$", path).group(1)
            conn = get_db()
            bin_row = conn.execute("SELECT * FROM bins WHERE id=?", (bin_id,)).fetchone()
            if not bin_row:
                self.send_json({"error": "Not found"}, 404)
                conn.close()
                return
            items = [dict(r) for r in conn.execute("""
                SELECT i.*, 
                    (SELECT checked_out_at FROM checkouts WHERE item_id=i.id AND checked_in_at IS NULL ORDER BY id DESC LIMIT 1) as checked_out_at,
                    (SELECT note FROM checkouts WHERE item_id=i.id AND checked_in_at IS NULL ORDER BY id DESC LIMIT 1) as checkout_note
                FROM items i WHERE i.bin_id=? ORDER BY i.name
            """, (bin_id,)).fetchall()]
            conn.close()
            self.send_json({"bin": dict(bin_row), "items": items})

        elif re.match(r"^/api/bins/number/([^/]+)$", path):
            number = re.match(r"^/api/bins/number/([^/]+)$", path).group(1)
            conn = get_db()
            bin_row = conn.execute("SELECT * FROM bins WHERE number=?", (number,)).fetchone()
            if not bin_row:
                self.send_json({"error": "Not found"}, 404)
                conn.close()
                return
            bin_id = bin_row["id"]
            items = [dict(r) for r in conn.execute("""
                SELECT i.*, 
                    (SELECT checked_out_at FROM checkouts WHERE item_id=i.id AND checked_in_at IS NULL ORDER BY id DESC LIMIT 1) as checked_out_at,
                    (SELECT note FROM checkouts WHERE item_id=i.id AND checked_in_at IS NULL ORDER BY id DESC LIMIT 1) as checkout_note
                FROM items i WHERE i.bin_id=? ORDER BY i.name
            """, (bin_id,)).fetchall()]
            conn.close()
            self.send_json({"bin": dict(bin_row), "items": items})

        elif path == "/api/search":
            q = qs.get("q", [""])[0].strip()
            if not q:
                self.send_json([])
                return
            conn = get_db()
            results = [dict(r) for r in conn.execute("""
                SELECT i.name, i.qty, i.description, b.number, b.label, b.location, b.id as bin_id
                FROM items i JOIN bins b ON b.id = i.bin_id
                WHERE i.name LIKE ? OR i.description LIKE ?
                ORDER BY b.number
            """, (f"%{q}%", f"%{q}%")).fetchall()]
            conn.close()
            self.send_json(results)

        else:
            self.send_json({"error": "Not found"}, 404)

    def do_POST(self):
        path = urlparse(self.path).path
        data = self.read_body()

        if path == "/api/bins":
            conn = get_db()
            number = data.get("number") or next_bin_number()
            conn.execute("INSERT INTO bins (number, label, location, notes) VALUES (?,?,?,?)",
                         (number, data["label"], data.get("location",""), data.get("notes","")))
            conn.commit()
            row = conn.execute("SELECT * FROM bins WHERE number=?", (number,)).fetchone()
            conn.close()
            self.send_json(dict(row), 201)

        elif re.match(r"^/api/bins/(\d+)/items$", path):
            bin_id = re.match(r"^/api/bins/(\d+)/items$", path).group(1)
            conn = get_db()
            conn.execute("INSERT INTO items (bin_id, name, qty, description) VALUES (?,?,?,?)",
                         (bin_id, data["name"], data.get("qty", 1), data.get("description", "")))
            conn.commit()
            conn.close()
            self.send_json({"ok": True}, 201)

        elif re.match(r"^/api/items/(\d+)/checkout$", path):
            item_id = re.match(r"^/api/items/(\d+)/checkout$", path).group(1)
            conn = get_db()
            conn.execute("INSERT INTO checkouts (item_id, note) VALUES (?,?)",
                         (item_id, data.get("note", "")))
            conn.commit()
            conn.close()
            self.send_json({"ok": True})

        elif re.match(r"^/api/items/(\d+)/checkin$", path):
            item_id = re.match(r"^/api/items/(\d+)/checkin$", path).group(1)
            conn = get_db()
            conn.execute("""UPDATE checkouts SET checked_in_at=datetime('now') 
                           WHERE item_id=? AND checked_in_at IS NULL""", (item_id,))
            conn.commit()
            conn.close()
            self.send_json({"ok": True})

        elif path == "/api/import":
            bins_data = data if isinstance(data, list) else data.get("bins", [])
            conn = get_db()
            summary = []
            for bin_def in bins_data:
                number = next_bin_number_conn(conn)
                conn.execute("INSERT INTO bins (number, label, location, notes) VALUES (?,?,?,?)",
                             (number, bin_def["label"], bin_def.get("location",""), bin_def.get("notes","")))
                conn.commit()
                bin_row = conn.execute("SELECT * FROM bins WHERE number=?", (number,)).fetchone()
                bin_id = bin_row["id"]
                items = bin_def.get("items", [])
                for item in items:
                    conn.execute("INSERT INTO items (bin_id, name, qty, description) VALUES (?,?,?,?)",
                                 (bin_id, item["name"], item.get("qty", 1), item.get("description", "")))
                conn.commit()
                summary.append({"number": number, "label": bin_def["label"], "items_added": len(items)})
            conn.close()
            self.send_json({"ok": True, "imported": summary}, 201)

        else:
            self.send_json({"error": "Not found"}, 404)

    def do_PUT(self):
        path = urlparse(self.path).path
        data = self.read_body()

        if re.match(r"^/api/bins/(\d+)$", path):
            bin_id = re.match(r"^/api/bins/(\d+)$", path).group(1)
            conn = get_db()
            conn.execute("UPDATE bins SET label=?, location=?, notes=? WHERE id=?",
                         (data["label"], data.get("location",""), data.get("notes",""), bin_id))
            conn.commit()
            conn.close()
            self.send_json({"ok": True})

        elif re.match(r"^/api/items/(\d+)$", path):
            item_id = re.match(r"^/api/items/(\d+)$", path).group(1)
            conn = get_db()
            conn.execute("UPDATE items SET name=?, qty=?, description=? WHERE id=?",
                         (data["name"], data.get("qty",1), data.get("description",""), item_id))
            conn.commit()
            conn.close()
            self.send_json({"ok": True})

        else:
            self.send_json({"error": "Not found"}, 404)

    def do_DELETE(self):
        path = urlparse(self.path).path

        if re.match(r"^/api/bins/(\d+)$", path):
            bin_id = re.match(r"^/api/bins/(\d+)$", path).group(1)
            conn = get_db()
            conn.execute("DELETE FROM bins WHERE id=?", (bin_id,))
            conn.commit()
            conn.close()
            self.send_json({"ok": True})

        elif re.match(r"^/api/items/(\d+)$", path):
            item_id = re.match(r"^/api/items/(\d+)$", path).group(1)
            conn = get_db()
            conn.execute("DELETE FROM items WHERE id=?", (item_id,))
            conn.commit()
            conn.close()
            self.send_json({"ok": True})

        else:
            self.send_json({"error": "Not found"}, 404)


if __name__ == "__main__":
    init_db()
    server = HTTPServer(("0.0.0.0", 8081), Handler)
    print("BinTracker running at http://0.0.0.0:8081")
    server.serve_forever()
