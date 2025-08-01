from ft_891_hunter.hunter import MainWindow, get_app


def main():
    app = get_app()
    window = MainWindow()
    window.show()
    app.exec()
