from automation.browser.session import SessionManager
from automation.sources.monster.login import MONSTER_HOME_URL


def main() -> None:
    manager = SessionManager(
        source_name="monster",
        login_url=MONSTER_HOME_URL,
        home_url=MONSTER_HOME_URL,
    )

    success = manager.open_manual_login()

    if success:
        print("\nMonster browser profile saved successfully.")
    else:
        print("\nMonster session capture failed.")


if __name__ == "__main__":
    main()