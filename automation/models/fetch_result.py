from dataclasses import dataclass
from typing import Optional


@dataclass
class FetchResult:
    success: bool

    final_url: Optional[str] = None

    html: Optional[str] = None

    status_code: Optional[int] = None

    error: Optional[str] = None