import sys

from PyQt6.QtWidgets import QApplication

from dampfross.ui.main_window import MainWindow


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("DampfrossDigital")
    app.setApplicationVersion("0.1.0")
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
