import re

EMAIL_PATTERN = re.compile(
    r"""
    [A-Za-z0-9._%+\-]+
    @
    [A-Za-z0-9.\-]+
    \.
    [A-Za-z]{2,}
    """,
    re.VERBOSE,
)

PHONE_PATTERN = re.compile(
    r"""
    (\+?\d{1,3}[\s.-]?)?
    (\(?\d{3}\)?[\s.-]?)?
    \d{3}[\s.-]?\d{4}
    """,
    re.VERBOSE,
)
