from PyQt5.QtWidgets import (
    QMainWindow, QDesktopWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QMenu, QWidget, QTableWidget, QHeaderView, QTableWidgetItem
)
from src.datamanagement.database import DbManager as db
import re


class ApplicationGUI(QMainWindow):
    _HEADERS = 'config/fields.txt'

    def __init__(self):
        super().__init__()
        screen = QDesktopWidget().screenGeometry()
        width, height = screen.width(), screen.height()
        self.setGeometry(0, 0, width, height)
        self.setWindowTitle('App')

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        _hbox = QHBoxLayout()
        self.text_field = QLineEdit()
        self.text_button = QPushButton('>')
        self.text_button.setMaximumWidth(30)
        self.text_button.setMaximumHeight(30)
        self.text_button.clicked.connect(self.exec_query)
        _hbox.addWidget(self.text_field)
        _hbox.addWidget(self.text_button)
        _hbox.setContentsMargins(100, 0, 100, 10)
        _hbox.setSpacing(15)

        _vbox = QVBoxLayout()
        _vbox.addLayout(_hbox)
        self._headers = self._set_table_headers()
        self.query_select_fields = ','.join(list(self._headers.values()))
        self.table_view = QTableWidget()
        self.table_view.setColumnCount(len(self._headers))
        self.table_view.setHorizontalHeaderLabels(list(self._headers.keys()))
        header = self.table_view.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeToContents)
        self._load_data(None)
        _vbox.addWidget(self.table_view)

        central_widget.setLayout(_vbox)

        menu_bar = self.menuBar()
        file_item = QMenu('&File', self)
        help_item = QMenu('&Help', self)
        about_item = QMenu('&About', self)
        menu_bar.addMenu(file_item)
        menu_bar.addMenu(help_item)
        menu_bar.addMenu(about_item)

    def _set_table_headers(self):
        with open(self._HEADERS, 'r') as file:
            return {line.strip().split(':')[1]: line.strip().split(':')[0] for line in file}

    def _load_data(self, constraints):
        rows = db.custom_query(self.query_select_fields, constraints)
        print(len(rows))
        if rows is None:
            return
        self.table_view.setRowCount(len(rows))
        for row_idx, row_data in enumerate(rows):
            for col_idx, cell_data in enumerate(row_data):
                self.table_view.setItem(row_idx, col_idx, QTableWidgetItem(str(cell_data)))

    def exec_query(self):
        text = self.text_field.text()
        pattern = r'^[a-z_]+\=(\"[\sa-zA-Z_\-.0-9]+\"|[0-9.]+)(&&[a-z_]+\=(\"[\sa-zA-Z_\-.0-9]+\"|[0-9.]+))*$'
        match = re.match(pattern, text)
        if not match:
            return
        parsed = text.replace('&&', ' AND ')
        print(parsed)
        self._load_data(parsed)

