from PyQt5.QtWidgets import (
    QMainWindow, QApplication, QDesktopWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QMenu, QWidget, QTableWidget, QHeaderView
)


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
        _hbox.addWidget(self.text_field)
        _hbox.addWidget(self.text_button)
        _hbox.setContentsMargins(100, 0, 100, 10)
        _hbox.setSpacing(15)

        _vbox = QVBoxLayout()
        _vbox.addLayout(_hbox)
        self._headers = self._set_table_headers()
        self.table_view = QTableWidget()
        self.table_view.setColumnCount(len(self._headers))
        self.table_view.setHorizontalHeaderLabels(list(self._headers.keys()))
        header = self.table_view.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeToContents)
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
