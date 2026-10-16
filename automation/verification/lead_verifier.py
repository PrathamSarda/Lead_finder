"""
Lead Verification Layer.

Validates extracted company evidence prior to final qualification:
- Distinguishes official company websites from directories, aggregators, and civic portals.
- Enforces email ownership and discards directory or generic third-party support emails.
- Validates geographic consistency (area codes vs US state).
- Formats phone numbers as strings to prevent spreadsheet scientific notation.
- Assigns three-state outcome: VERIFIED, NEEDS_REVIEW, UNRESOLVED with provenance.
"""
from __future__ import annotations

import re
from urllib.parse import urlparse

import phonenumbers
from phonenumbers import PhoneNumberFormat, geocoder

from automation.intelligence.models import CompanyEvidence, CompanyInput
from automation.resolvers.domain_similarity import (
    calculate_domain_similarity,
    extract_domain_name,
)
from automation.verification.directory_registry import (
    evaluate_domain_plausibility,
    is_directory_domain,
    normalize_domain,
)
from automation.verification.models import VerificationStatus, VerifiedLead


LEGAL_SUFFIXES = {
    "inc",
    "incorporated",
    "llc",
    "l.l.c",
    "ltd",
    "limited",
    "corp",
    "corporation",
    "company",
    "co",
    "plc",
    "lp",
    "llp",
    "group",
    "holdings",
}

FREE_EMAIL_DOMAINS = {
    "aol.com",
    "att.net",
    "bellsouth.net",
    "comcast.net",
    "gmail.com",
    "googlemail.com",
    "hotmail.com",
    "icloud.com",
    "live.com",
    "mail.com",
    "msn.com",
    "outlook.com",
    "proton.me",
    "protonmail.com",
    "sbcglobal.net",
    "verizon.net",
    "yahoo.com",
    "ymail.com",
}

US_STATE_NAMES = {
    "AL": "Alabama",
    "AK": "Alaska",
    "AZ": "Arizona",
    "AR": "Arkansas",
    "CA": "California",
    "CO": "Colorado",
    "CT": "Connecticut",
    "DE": "Delaware",
    "FL": "Florida",
    "GA": "Georgia",
    "HI": "Hawaii",
    "ID": "Idaho",
    "IL": "Illinois",
    "IN": "Indiana",
    "IA": "Iowa",
    "KS": "Kansas",
    "KY": "Kentucky",
    "LA": "Louisiana",
    "ME": "Maine",
    "MD": "Maryland",
    "MA": "Massachusetts",
    "MI": "Michigan",
    "MN": "Minnesota",
    "MS": "Mississippi",
    "MO": "Missouri",
    "MT": "Montana",
    "NE": "Nebraska",
    "NV": "Nevada",
    "NH": "New Hampshire",
    "NJ": "New Jersey",
    "NM": "New Mexico",
    "NY": "New York",
    "NC": "North Carolina",
    "ND": "North Dakota",
    "OH": "Ohio",
    "OK": "Oklahoma",
    "OR": "Oregon",
    "PA": "Pennsylvania",
    "RI": "Rhode Island",
    "SC": "South Carolina",
    "SD": "South Dakota",
    "TN": "Tennessee",
    "TX": "Texas",
    "UT": "Utah",
    "VT": "Vermont",
    "VA": "Virginia",
    "WA": "Washington",
    "WV": "West Virginia",
    "WI": "Wisconsin",
    "WY": "Wyoming",
}


def clean_company_tokens(name: str) -> list[str]:
    """Return substantive lowercase alphanumeric tokens for a company name."""
    raw_tokens = re.findall(r"[a-z0-9]+", name.lower())
    return [token for token in raw_tokens if token not in LEGAL_SUFFIXES and len(token) > 1]


def format_phone_as_text(phone: str | None) -> str | None:
    """
    Format a phone number into a formatted string (e.g. +1 478-214-4236)
    that spreadsheet tools will NEVER render as scientific notation float.
    """
    if not phone or not phone.strip():
        return None

    cleaned = phone.strip()
    try:
        parsed = phonenumbers.parse(cleaned, "US")
        if phonenumbers.is_valid_number(parsed):
            # Formats as e.g. "(478) 214-4236" or "+1 478-214-4236"
            national = phonenumbers.format_number(parsed, PhoneNumberFormat.NATIONAL)
            return f"+1 {national}"
    except Exception:
        pass

    # Ensure it's not a pure numeric string that triggers scientific notation
    if cleaned.isdigit() and len(cleaned) == 10:
        return f"+1 ({cleaned[:3]}) {cleaned[3:6]}-{cleaned[6:]}"

    return cleaned


def check_geographic_conflict(state_code: str | None, phone: str | None) -> tuple[bool, str | None]:
    """
    Check if a US phone number belongs to a different state than expected.
    Returns (has_conflict, description).
    """
    if not state_code or not phone:
        return False, None

    state_code = state_code.strip().upper()
    expected_state_name = US_STATE_NAMES.get(state_code)
    if not expected_state_name:
        return False, None

    try:
        parsed = phonenumbers.parse(phone.strip(), "US")
        if not phonenumbers.is_valid_number(parsed):
            return False, None
        geo_desc = geocoder.description_for_number(parsed, "en")
        if not geo_desc:
            return False, None

        # Check if expected state is mentioned in the geocoder description
        if expected_state_name.lower() in geo_desc.lower() or f", {state_code}".lower() in geo_desc.lower():
            return False, None

        # If geocoder returned another US state name, flag conflict
        for code, full_name in US_STATE_NAMES.items():
            if code != state_code and full_name.lower() in geo_desc.lower():
                return True, f"Phone area code located in {geo_desc}, differing from expected state {expected_state_name} ({state_code})"

    except Exception:
        pass

    return False, None


def validate_email_ownership(
    email: str | None,
    website: str | None,
    company_name: str,
) -> tuple[str | None, str | None]:
    """
    Validate that an extracted email belongs to the company, not a directory or aggregator.
    Returns (accepted_email, drop_reason).
    """
    if not email or not email.strip():
        return None, None

    email = email.strip().lower()
    if "@" not in email:
        return None, "invalid_email_format"

    local_part, domain = email.rsplit("@", 1)

    # 0. Reject placeholder, dummy, or website registrar emails
    placeholder_prefixes = {
        "filler", "example", "test", "testing", "dummy", "sample",
        "noreply", "no-reply", "donotreply", "webmaster", "privacy",
        "abuse", "postmaster", "hostmaster", "registrar",
    }
    if local_part in placeholder_prefixes or any(local_part.startswith(p) for p in ("filler", "dummy", "test")):
        return None, f"placeholder_email:{local_part}"

    if domain in {"godaddy.com", "wix.com", "squarespace.com", "wordpress.com", "namecheap.com", "cloudflare.com"}:
        return None, f"website_builder_domain:{domain}"

    # 1. Reject emails on directory domains
    if is_directory_domain(domain):
        return None, f"email_domain_is_directory:{domain}"

    # 2. Match against company website domain
    if website:
        web_domain = normalize_domain(website)
        if domain == web_domain or domain.endswith(f".{web_domain}") or web_domain.endswith(f".{domain}"):
            return email, None

    # 3. Handle free-mail / ISP domains
    if domain in FREE_EMAIL_DOMAINS:
        company_tokens = clean_company_tokens(company_name)
        # Check if local part contains at least one substantive company token
        clean_local = re.sub(r"[^a-z0-9]", "", local_part)
        if any(token in clean_local for token in company_tokens if len(token) >= 4):
            return email, None
        return None, "freemail_unverified_local_part"

    # 4. Third-party domain emails that do not match the company's verified domain
    return None, f"third_party_domain_mismatch:{domain}"


class LeadVerifier:
    """
    Applies qualification rules to candidate company evidence.
    """

    def verify(
        self,
        company: CompanyInput,
        evidence: CompanyEvidence | None,
        duration: float = 0.0,
    ) -> VerifiedLead:
        location_str = ", ".join(p for p in (company.city, company.state) if p and p.strip()) or "US"

        if evidence is None or not evidence.website:
            return VerifiedLead(
                company_name=company.name,
                location=location_str,
                status=VerificationStatus.UNRESOLVED.value,
                status_reason="No official company website found in search results.",
                confidence=0.0,
                sources=evidence.sources if evidence else ["fmcsa"],
                elapsed_seconds=duration,
            )

        candidate_url = evidence.website.strip()
        plausible, rejection_reason = evaluate_domain_plausibility(candidate_url)

        if not plausible:
            return VerifiedLead(
                company_name=company.name,
                location=location_str,
                status=VerificationStatus.UNRESOLVED.value,
                status_reason=f"Rejected candidate domain: {rejection_reason}",
                confidence=0.0,
                sources=evidence.sources or [],
                elapsed_seconds=duration,
            )

        # Domain token and similarity analysis
        company_tokens = clean_company_tokens(company.name)
        domain_name = extract_domain_name(candidate_url)
        similarity = calculate_domain_similarity(company.name, candidate_url)

        # Check token coverage (how many substantive company words appear in domain)
        matched_tokens = [tok for tok in company_tokens if tok in domain_name]
        token_coverage = (len(matched_tokens) / len(company_tokens)) if company_tokens else 0.0

        # Substantive keyword discrepancy check (e.g. contracting vs construction)
        substantive_conflict = False
        if "contracting" in company_tokens and "construction" in domain_name and "contracting" not in domain_name:
            substantive_conflict = True

        # False positive check for multi-token companies matching single unrelated brand (e.g. Marc Cain)
        unrelated_short_match = False
        if len(company_tokens) >= 2 and len(matched_tokens) == 1 and token_coverage < 0.50:
            # e.g., Cain Am Bickley -> marc-cain (only 'cain' matched, 'bickley' absent, 'marc' added)
            unrelated_short_match = True

        # Geographic consistency check
        geo_conflict, geo_conflict_desc = check_geographic_conflict(company.state, evidence.phone)

        # Email validation
        valid_email, email_note = validate_email_ownership(
            evidence.email,
            candidate_url,
            company.name,
        )
        email_source = evidence.email_source_url if valid_email else None

        # Phone formatting
        formatted_phone = format_phone_as_text(evidence.phone)
        phone_source = evidence.phone_source_url if formatted_phone else None

        # Determine final status
        if unrelated_short_match:
            status = VerificationStatus.UNRESOLVED.value
            status_reason = f"Candidate domain {candidate_url} matches only a generic fragment without company identity."
            final_website = None
            valid_email = None
            formatted_phone = None
        elif substantive_conflict or geo_conflict:
            status = VerificationStatus.NEEDS_REVIEW.value
            reasons = []
            if substantive_conflict:
                reasons.append("Company name keyword discrepancy (e.g. contracting vs construction)")
            if geo_conflict and geo_conflict_desc:
                reasons.append(geo_conflict_desc)
            status_reason = "; ".join(reasons)
            final_website = candidate_url
        elif similarity >= 0.75 or token_coverage >= 0.65 or evidence.confidence >= 0.85:
            status = VerificationStatus.VERIFIED.value
            status_reason = "Official company domain verified with matching identity and contact details."
            final_website = candidate_url
        elif similarity >= 0.45 or token_coverage >= 0.35:
            status = VerificationStatus.NEEDS_REVIEW.value
            status_reason = f"Candidate domain {candidate_url} has moderate similarity ({similarity:.2f}); manual review recommended."
            final_website = candidate_url
        else:
            status = VerificationStatus.UNRESOLVED.value
            status_reason = f"Candidate domain {candidate_url} does not have sufficient evidence to establish ownership."
            final_website = None
            valid_email = None
            formatted_phone = None

        return VerifiedLead(
            company_name=company.name,
            location=location_str,
            status=status,
            status_reason=status_reason,
            website=final_website,
            website_source=evidence.website_source_url or candidate_url if final_website else None,
            email=valid_email,
            email_source=email_source,
            phone=formatted_phone,
            phone_source=phone_source,
            confidence=evidence.confidence if status == VerificationStatus.VERIFIED.value else min(evidence.confidence, 0.60),
            sources=evidence.sources or [],
            elapsed_seconds=duration,
        )
