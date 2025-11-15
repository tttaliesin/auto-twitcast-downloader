"""트위캐스트 자동 녹화 프로그램 - 메인 진입점"""

from src.gui import TwitCastingMonitorGUI


def main():
    """메인 진입점"""
    app = TwitCastingMonitorGUI()
    app.mainloop()


if __name__ == "__main__":
    main()
