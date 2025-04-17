import sys
import sqlite3
from datetime import datetime
import requests
from functools import partial
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QDateEdit, QTableWidget, QTableWidgetItem,
    QSpinBox, QMessageBox, QCheckBox, QHeaderView, QComboBox, QSizePolicy
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QFont

# ---------- DATABASE ----------
conn = sqlite3.connect("tasks.db")
c = conn.cursor()
c.execute('''
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        due_date TEXT,
        completed BOOLEAN,
        priority INTEGER
    )
''')
c.execute('''
    CREATE TABLE IF NOT EXISTS reminders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        date TEXT,
        type TEXT
    )
''')
conn.commit()

def fetch_reminders():
    url = 'https://date.nager.at/api/v3/PublicHolidays/2025/PL'
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            for event in data:
                name = event['localName']
                date = event['date']
                type_ = event['types'][0] if event['types'] else 'Holiday'
                c.execute("SELECT * FROM reminders WHERE name = ? AND date = ?", (name, date))
                if not c.fetchone():
                    c.execute("INSERT INTO reminders (name, date, type) VALUES (?, ?, ?)", (name, date, type_))
            conn.commit()
    except Exception as e:
        print("Error", e)

fetch_reminders()

# ---------- MAIN WINDOW ----------
class TaskTracker(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Task Tracker")
        self.setStyleSheet(""" 
        QWidget {
            background-color: #FFF5EE; 
            color: #000000; 
        }
        QLineEdit, QDateEdit, QSpinBox, QComboBox, QTableWidget {
            border: 0.5px solid #f3ecdb;
            font-size: 14px;
            border-radius: 4px;
        }
        QHeaderView::section { 
            background-color: #FAF0E6;
            font-weight: bold;
            border: 0.5px solid #ccc;
            padding: 4px;
        }
        QPushButton {
            background-color: #FAF0E6;    
            font-weight: bold;    
        }
        QCheckBox {
            padding-left: 7px;
        }
        QCheckBox::indicator {
            width: 20px;
            height: 20px;
            border: 0.5px solid #ccc;
            border-radius: 4px;
        }  
        QCheckBox::indicator:checked {
            background-color: #f3ecdb;
            border: 0.5px solid #ccc;
        } 
        """)#CF9D9D
        self.setGeometry(250, 30, 600, 500)

        layout = QVBoxLayout()

        title = QLabel("❀ Planer zadań ❀")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFont(QFont("Arial", 20))
        layout.addWidget(title)

        # Układ pionowy dla dodawania zadania
        input_layout = QVBoxLayout()

        # Nowe zadania
        new_title = QLabel("Dodaj nowe zadanie")
        new_title.setFont(QFont("Arial", 15))
        input_layout.addWidget(new_title)

        # Nazwa zadania
        title_label = QLabel("Nazwa zadania:")
        title_label.setStyleSheet("font-size: 14px;")
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("Wpisz nazwę zadania")
        self.title_input.setStyleSheet("padding: 4px; background-color: #FAF0E6;")
        input_layout.addWidget(title_label)
        input_layout.addWidget(self.title_input)

        # Data wykonania
        date_label = QLabel("Wybierz datę wykonania:")
        date_label.setStyleSheet("font-size: 14px;")
        self.date_input = QDateEdit()
        self.date_input.setDate(QDate.currentDate())
        self.date_input.setCalendarPopup(True)
        self.date_input.setStyleSheet("padding: 4px; background-color: #FAF0E6;")
        input_layout.addWidget(date_label)
        input_layout.addWidget(self.date_input)

        # Priorytet
        priority_label = QLabel("Jak ważne jest to zadanie? (1 - bardzo ważne):")
        priority_label.setStyleSheet("font-size: 14px;")
        self.priority_input = QSpinBox()
        self.priority_input.setRange(1, 5)
        self.priority_input.setStyleSheet("padding: 4px; background-color: #FAF0E6;")
        input_layout.addWidget(priority_label)
        input_layout.addWidget(self.priority_input)

        # Przycisk dodaj
        add_btn = QPushButton("Dodaj")
        add_btn.setStyleSheet("padding: 6px; margin-bottom: 10px;")
        add_btn.clicked.connect(self.add_task)
        input_layout.addWidget(add_btn)

        layout.addLayout(input_layout)

        # ----------------- Twoje zadania
        tasks = QLabel("Twoje zadania")
        tasks.setFont(QFont("Arial", 15))
        layout.addWidget(tasks)

        # wyszukiwanie, sortowanie
        search_sort_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Wyszukaj")
        self.search_input.setStyleSheet("border-radius: 4px;")
        self.search_input.textChanged.connect(self.load_tasks)

        self.sort_combo = QComboBox()
        self.sort = {
            "Brak sortowania": None,
            "Data wykonania": "due_date",
            "Priorytet": "priority",
            "Nazwa zadania": "title"
        }
        self.sort_combo.addItems(self.sort.keys())
        self.sort_combo.setMinimumWidth(180)
        self.sort_combo.currentTextChanged.connect(self.load_tasks)

        search_label = QLabel("Wyszukaj:")
        search_label.setStyleSheet("font-size: 14px;")
        search_sort_layout.addWidget(search_label)
        search_sort_layout.addWidget(self.search_input)

        sort_label = QLabel("Sortuj:")
        sort_label.setStyleSheet("font-size: 14px; margin-left: 10px;")
        search_sort_layout.addWidget(sort_label)
        search_sort_layout.addWidget(self.sort_combo)
        layout.addLayout(search_sort_layout)

        # paginacja setup
        self.current_page = 0
        self.items_per_page = 5

        # ----------- Task Table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.verticalHeader().setVisible(False)
        self.table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        row_height = 30  # wysokość jednego wiersza
        visible_rows = self.items_per_page  # 5
        header_height = self.table.horizontalHeader().height()
        self.table.setFixedHeight(row_height * visible_rows + header_height + 12)
        self.table.verticalHeader().setDefaultSectionSize(row_height)

        layout.addWidget(self.table)

        # -------- Zmiana stron
        pagination_layout = QHBoxLayout()
        self.prev_btn = QPushButton("⯇")
        self.prev_btn.clicked.connect(self.prev_page)

        self.next_btn = QPushButton("⯈")
        self.next_btn.clicked.connect(self.next_page)
        pagination_layout.addWidget(self.prev_btn)
        pagination_layout.addWidget(self.next_btn)
        layout.addLayout(pagination_layout)

        # ---------- Nadchodzące święta
        self.reminder_label = QLabel("Nadchodzące Święta")
        self.reminder_label.setFont(QFont("Arial", 15))
        self.reminder_label.setStyleSheet("margin-top: 10px;")
        layout.addWidget(self.reminder_label)

        self.reminder_list = QLabel()
        self.reminder_list.setStyleSheet("color: black; font-size: 15px; line-height: 1.6; padding: 8px; background-color: #FAF0E6; border-radius: 8px; border: 0.5px solid #f3ecdb;")
        layout.addWidget(self.reminder_list)

        self.setLayout(layout)
        self.editing_task_id = None
        self.load_tasks()
        self.table.itemChanged.connect(self.item_change)
        self.load_reminders()

    def add_task(self):
        title = self.title_input.text()
        due_date = self.date_input.date().toString("yyyy-MM-dd")
        priority = int(self.priority_input.value())
        completed = False

        if not title:
            QMessageBox.warning(self, "Uwaga!", "Dodaj nazwę zadania")
            return

        c.execute("INSERT INTO tasks (title, due_date, completed, priority) VALUES (?, ?, ?, ?)",
                  (title, due_date, completed, priority))

        # print("DODANIE:", title, due_date, priority, completed)

        conn.commit()
        self.clear_inputs()
        self.load_tasks()

    def clear_inputs(self):
        self.title_input.clear()
        self.date_input.setDate(QDate.currentDate())
        self.priority_input.setValue(1)
        # self.completed_input.setChecked(False)

    def load_tasks(self):
        self.table.blockSignals(True)
        self.table.setRowCount(0)
        search = self.search_input.text()
        sort_by = self.sort_combo.currentText()
        offset = self.current_page * self.items_per_page

        base_query = "SELECT * FROM tasks WHERE title LIKE ?"
        sort_column = self.sort.get(sort_by)
        if sort_column:
            base_query += f" ORDER BY {sort_column}"
        base_query += " LIMIT ? OFFSET ?"

        rows = c.execute(base_query, (f"%{search}%", self.items_per_page, offset)).fetchall()

        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["✓", "Zadanie", "Zrobić do", "Priorytet", "Usuń"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        for row_idx, task in enumerate(rows):
            self.table.insertRow(row_idx)

            task_id = task[0]
            title = task[1]
            due_date = task[2]
            completed = task[3]
            priority = task[4]

            completed_checkbox = QCheckBox()
            completed_checkbox.setChecked(bool(completed))
            completed_checkbox.stateChanged.connect(partial(self.update_task_completed, task_id))

            self.table.setCellWidget(row_idx, 0, completed_checkbox)
            self.table.setItem(row_idx, 1, QTableWidgetItem(title))

            # self.table.setItem(row_idx, 2, QTableWidgetItem(str(due_date)))
            date_item = QTableWidgetItem(str(due_date))
            date_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row_idx, 2, date_item)

            # self.table.setItem(row_idx, 3, QTableWidgetItem(str(priority)))
            priority_item = QTableWidgetItem(str(priority))
            priority_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row_idx, 3, priority_item)

            delete_btn = QPushButton("☓")
            delete_btn.clicked.connect(lambda _, id=task_id: self.delete_task(id))
            self.table.setCellWidget(row_idx, 4, delete_btn)
        self.table.blockSignals(False)

    def delete_task(self, task_id):
        c.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        conn.commit()
        self.load_tasks()

    def update_task_completed(self, task_id, state):
        completed = 1 if state == Qt.CheckState.Checked.value else 0
        c.execute("UPDATE tasks SET completed = ? WHERE id = ?", (completed, task_id))
        conn.commit()

    def prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.load_tasks()

    def next_page(self):
        total = c.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
        if (self.current_page + 1) * self.items_per_page < total:
            self.current_page += 1
            self.load_tasks()

    def item_change(self, item):
        row = item.row()
        column = item.column()
        checkbox_widget = self.table.cellWidget(row, 0)

        if checkbox_widget:
            task_id = None
            for i, row_data in enumerate(c.execute("SELECT id FROM tasks").fetchall()):
                widget = self.table.cellWidget(i, 0)
                if widget == checkbox_widget:
                    task_id = row_data[0]
                    break
            if task_id is None:
                return
        else:
            return
        new_value = item.text()
        if column == 1:  # Tytuł
            c.execute("UPDATE tasks SET title = ? WHERE id = ?", (new_value, task_id))
        elif column == 2:  # Data
            c.execute("UPDATE tasks SET due_date = ? WHERE id = ?", (new_value, task_id))
        elif column == 3:  # Priorytet
            try:
                new_priority = int(new_value)
                if 1 <= new_priority <= 5:
                    c.execute("UPDATE tasks SET priority = ? WHERE id = ?", (new_priority, task_id))
                    conn.commit()
                else:
                    # gdy za wyskoa wartosc to zaladuje od nowa i wyskoczy okno
                    QMessageBox.warning(self, "Błąd", "Priorytet ma być liczbą od 1 do 5")
                    self.load_tasks()
            except ValueError:
                self.load_tasks()

        conn.commit()

    def load_reminders(self):
        today = datetime.today().strftime("%Y-%m-%d")
        reminders = c.execute("SELECT name, date FROM reminders "
                              "WHERE date >= ? ORDER BY date LIMIT 5",
                              (today,)).fetchall()

        text = ""
        for r in reminders:
            text += f"""
                <div style='display: flex; justify-content: space-between; align-items: center; 
                            margin-bottom: 5px;'>
                    <span style='width: 100px; font-weight: bold;'>{r[1]}</span>
                    <span style='flex: 1; text-align: center; '>{r[0]}</span>
                </div>
            """

        self.reminder_list.setText(text)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TaskTracker()
    window.show()
    sys.exit(app.exec())
