from dataclasses import dataclass, field


@dataclass
class EmailPriorityResult:
    """
    Ranked email addresses discovered for one company.
    """

    primary_email: str | None = None

    business_emails: list[str] = field(
        default_factory=list
    )

    personal_emails: list[str] = field(
        default_factory=list
    )

    rejected_emails: list[str] = field(
        default_factory=list
    )