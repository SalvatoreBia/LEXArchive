from PyQt5.QtWidgets import QApplication
import src.bot.tgbot as bot
import sys
import src.gui.main_window as wnd

if __name__ == '__main__':
    # bot.run()
    app = QApplication(sys.argv)
    window = wnd.ApplicationGUI()
    window.show()
    sys.exit(app.exec_())
