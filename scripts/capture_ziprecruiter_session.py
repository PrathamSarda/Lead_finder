from automation.browser.session import SessionManager
from automation.sources.ziprecruiter.login import (
    ZIPRECRUITER_EMPLOYER_LOGIN_URL,
)


def main() -> None:
    manager = SessionManager(
        source_name="ziprecruiter",
        login_url=ZIPRECRUITER_EMPLOYER_LOGIN_URL,
        home_url=ZIPRECRUITER_EMPLOYER_LOGIN_URL,
    )

    success = manager.open_manual_login()

    if success:
        print("\nZipRecruiter browser profile saved successfully.")
    else:
        print("\nZipRecruiter session capture failed.")


if __name__ == "__main__":
    main()