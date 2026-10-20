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
    LEGAL_SUFFIXES as _DS_LEGAL_SUFFIXES,
    _tokenize as _ds_tokenize,
    calculate_domain_similarity,
    extract_domain_name,
)
from automation.resolvers.validator import (
    _looks_like_personal_name,
)
from automation.verification.directory_registry import (
    evaluate_domain_plausibility,
    is_directory_domain,
    normalize_domain,
)
from automation.verification.models import LeadTier, VerificationStatus, VerifiedLead


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
            if parsed.country_code == 1:
                national = phonenumbers.format_number(parsed, PhoneNumberFormat.NATIONAL)
                return f"+1 {national}"
            else:
                return phonenumbers.format_number(parsed, PhoneNumberFormat.INTERNATIONAL)
    except Exception:
        pass

    # Ensure it's not a pure numeric string that triggers scientific notation
    if cleaned.isdigit() and len(cleaned) == 10:
        return f"+1 ({cleaned[:3]}) {cleaned[3:6]}-{cleaned[6:]}"

    return cleaned


def check_geographic_conflict(state_code: str | None, phone: str | None) -> tuple[bool, str | None]:
    """
    Check if a US phone number belongs to a different state or country than expected.
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

        # Check for foreign country phone number on domestic US carrier
        if parsed.country_code != 1:
            country_name = geocoder.description_for_number(parsed, "en") or f"country code +{parsed.country_code}"
            return True, f"International phone number located in {country_name}, differing from expected US state {expected_state_name} ({state_code})"

        geo_desc = geocoder.description_for_number(parsed, "en")
        if not geo_desc:
            return False, None

        lower_desc = geo_desc.lower()

        # Check if expected state is mentioned in the geocoder description
        if (
            expected_state_name.lower() in lower_desc
            or f", {state_code.lower()}" in lower_desc
            or lower_desc.endswith(f" {state_code.lower()}")
        ):
            return False, None

        # If geocoder returned another US state name or state code, flag conflict
        for code, full_name in US_STATE_NAMES.items():
            if code != state_code:
                if (
                    full_name.lower() in lower_desc
                    or f", {code.lower()}" in lower_desc
                    or lower_desc.endswith(f" {code.lower()}")
                ):
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
        clean_local = re.sub(r"[^a-z0-9]", "", local_part)
        # Accept if local part contains at least one substantive company token (3+ chars)
        if any(token in clean_local for token in company_tokens if len(token) >= 3):
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

        candidate_results = getattr(evidence, "candidate_results", None) or []

        if evidence is None or not evidence.website:
            formatted_p = format_phone_as_text(evidence.phone) if evidence and evidence.phone else None
            p_source = evidence.phone_source_url if evidence else None
            e_val = evidence.email if evidence else None
            e_source = evidence.email_source_url if evidence else None

            if formatted_p or e_val:
                geo_conflict, geo_conflict_desc = check_geographic_conflict(company.state, formatted_p) if formatted_p else (False, None)
                p_status = VerificationStatus.NEEDS_REVIEW.value if formatted_p else VerificationStatus.UNRESOLVED.value
                e_status = VerificationStatus.NEEDS_REVIEW.value if e_val else VerificationStatus.UNRESOLVED.value
                return VerifiedLead(
                    company_name=company.name,
                    location=location_str,
                    status=VerificationStatus.NEEDS_REVIEW.value,
                    status_reason=f"No custom website; direct contact found via directory ({geo_conflict_desc or 'unverified domain'}).",
                    lead_tier=LeadTier.DIRECTORY_CONTACT.value,
                    website=None,
                    website_status=VerificationStatus.UNRESOLVED.value,
                    website_source=None,
                    email=e_val,
                    email_status=e_status,
                    email_source=e_source,
                    phone=formatted_p,
                    phone_status=p_status,
                    phone_source=p_source,
                    confidence=0.50,
                    sources=evidence.sources if evidence else ["fmcsa"],
                    candidate_results=candidate_results,
                    elapsed_seconds=duration,
                )

            return VerifiedLead(
                company_name=company.name,
                location=location_str,
                status=VerificationStatus.UNRESOLVED.value,
                status_reason="No official company website found in search results.",
                confidence=0.0,
                sources=evidence.sources if evidence else ["fmcsa"],
                candidate_results=candidate_results,
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
                candidate_results=candidate_results,
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

        # False positive check for multi-token companies matching single unrelated brand (e.g. Marc Cain for Cain AM Bickley)
        unrelated_short_match = False
        if len(company_tokens) >= 2 and len(matched_tokens) == 1 and token_coverage < 0.50:
            evidence_text = f"{candidate_url} {evidence.title or ''} {evidence.snippet or ''}".lower()
            unmatched_tokens = [tok for tok in company_tokens if tok not in matched_tokens]
            if not any(tok in evidence_text for tok in unmatched_tokens):
                # Truly unrelated (e.g., 'cain' matched 'marc-cain' with no 'bickley' in evidence)
                unrelated_short_match = True

        # Check if matched tokens are exclusively generic category terms
        GENERIC_CATEGORY_TERMS = {
            "delivery", "transfer", "transport", "transportation", "trucking",
            "freight", "logistics", "shipping", "storage", "moving",
            "supplies", "products", "materials", "sales", "contracting",
            "construction", "commercial", "industrial", "management",
            "services", "service", "solutions", "enterprises", "group", "international",
        }
        distinctive_company_tokens = [tok for tok in company_tokens if tok not in GENERIC_CATEGORY_TERMS]
        generic_only_domain_match = False
        if distinctive_company_tokens and not any(tok in domain_name for tok in distinctive_company_tokens):
            # Check if domain starts with the company's initials (e.g. 'aic' for 'American Industrial Contracting')
            company_initials = "".join(t[0] for t in company_tokens if len(t) >= 2)
            has_initialism_match = len(company_initials) >= 2 and domain_name.startswith(company_initials)
            if not has_initialism_match:
                # Domain matched only generic category terms without the company's distinctive brand token
                generic_only_domain_match = True

        # Geographic consistency check (phone area code vs company state)
        geo_conflict, geo_conflict_desc = check_geographic_conflict(company.state, evidence.phone)

        # Cross-state domain check: reject domains that embed a different US state code or full state name
        # e.g. 'adamsincvt.com' has 'vt' preceded by non-vowel or full state name 'floridamoving'
        domain_state_conflict = False
        domain_state_conflict_desc = None
        if company.state and domain_name:
            company_state = company.state.strip().upper()
            domain_lower = domain_name.lower()
            for code, full_name in US_STATE_NAMES.items():
                if code == company_state:
                    continue
                state_code_lower = code.lower()
                full_name_lower = full_name.lower().replace(" ", "")

                # Check if the full state name appears in the domain (e.g. 'floridamoving' or 'texasrigging')
                if full_name_lower in domain_lower and len(full_name_lower) >= 4:
                    domain_state_conflict = True
                    domain_state_conflict_desc = (
                        f"Domain '{domain_name}' contains state name '{full_name}', "
                        f"but company is registered in {US_STATE_NAMES.get(company_state, company_state)} ({company_state})"
                    )
                    break

                # For 2-letter state codes, avoid false positives from English word endings like
                # 'chloride' (-de), 'transport' (-or), 'metal' (-al), 'trucking' (-in), 'services' (-es).
                # Require that the 2-letter code is preceded by a number, hyphen, or common suffix (inc/corp/co/llc)
                # or is an explicit suffix like 'adamsincvt' or 'company-vt'
                state_code_pattern = rf"(?:[0-9_-]|inc|corp|co|llc|group|trucking|freight|movers|moving|transport){state_code_lower}$"
                if re.search(state_code_pattern, domain_lower):
                    domain_state_conflict = True
                    domain_state_conflict_desc = (
                        f"Domain '{domain_name}' contains state code '{code}' ({full_name}), "
                        f"but company is registered in {US_STATE_NAMES.get(company_state, company_state)} ({company_state})"
                    )
                    break

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

        # Determine field-level statuses
        website_status = VerificationStatus.UNRESOLVED.value
        email_status = VerificationStatus.UNRESOLVED.value
        phone_status = VerificationStatus.UNRESOLVED.value

        evidence_sources = set(evidence.sources or [])
        is_pattern_guess_email = "pattern_guess" in evidence_sources

        # Determine phone verification
        if formatted_phone and not geo_conflict:
            phone_status = VerificationStatus.VERIFIED.value
        elif formatted_phone:
            phone_status = VerificationStatus.NEEDS_REVIEW.value

        # RULE 2: pattern_guess alone can never result in email_status = VERIFIED
        if valid_email:
            if is_pattern_guess_email:
                email_status = VerificationStatus.NEEDS_REVIEW.value
            else:
                email_status = VerificationStatus.VERIFIED.value

        # Independent sources include search providers, crawlers, and directory engines
        has_independent_source = bool(
            evidence_sources.intersection({
                "ddgs", "zenserp", "serper", "thomasnet",
                "resolver", "crawler", "generic", "google", "bing"
            })
        )
        # Primary contact evidence: verified phone with no geo-conflict or verified owned email
        has_primary_contact_evidence = (
            phone_status == VerificationStatus.VERIFIED.value
            or (email_status == VerificationStatus.VERIFIED.value and not is_pattern_guess_email)
        )
        # Domain guessing ALONE (no search provider and no primary contact evidence on the page)
        is_domain_guess_only = (
            ("domain_guess" in evidence_sources)
            and not has_independent_source
            and not has_primary_contact_evidence
        )

        # Personal name check: personal name companies require location corroboration
        # or verified contact details to be marked VERIFIED. Without them, mark NEEDS_REVIEW.
        is_personal_company = _looks_like_personal_name(company.name)

        # RULE 1 & 3: domain_guess alone can never result in website_status = VERIFIED.
        # A website must match target company identity and location, not merely share a word.
        if unrelated_short_match or generic_only_domain_match:
            status = VerificationStatus.NEEDS_REVIEW.value
            website_status = VerificationStatus.NEEDS_REVIEW.value
            if generic_only_domain_match:
                status_reason = f"Candidate domain {candidate_url} matches only generic/industry terms without the company's distinctive brand name; requires manual review."
            else:
                status_reason = f"Candidate domain {candidate_url} matches only a generic fragment; requires manual review."
            final_website = candidate_url
        elif substantive_conflict or geo_conflict or domain_state_conflict:
            status = VerificationStatus.NEEDS_REVIEW.value
            website_status = VerificationStatus.NEEDS_REVIEW.value
            reasons = []
            if substantive_conflict:
                reasons.append("Company name keyword discrepancy (e.g. contracting vs construction)")
            if geo_conflict and geo_conflict_desc:
                reasons.append(geo_conflict_desc)
            if domain_state_conflict and domain_state_conflict_desc:
                reasons.append(domain_state_conflict_desc)
            status_reason = "; ".join(reasons)
            final_website = candidate_url
        elif is_domain_guess_only:
            # Domain guessing alone requires manual review
            status = VerificationStatus.NEEDS_REVIEW.value
            website_status = VerificationStatus.NEEDS_REVIEW.value
            status_reason = f"Candidate domain {candidate_url} derived from domain guessing alone; requires independent verification."
            final_website = candidate_url
        elif is_personal_company and not has_primary_contact_evidence:
            # Personal-name company without verified phone or direct email: treat as lead for review, not proof
            status = VerificationStatus.NEEDS_REVIEW.value
            website_status = VerificationStatus.NEEDS_REVIEW.value
            status_reason = f"Personal name candidate {candidate_url} requires direct contact corroboration to verify identity."
            final_website = candidate_url
        elif (similarity >= 0.65 or token_coverage >= 0.60) and (len(matched_tokens) >= 1 if company_tokens else True):
            # Verified via independent search / resolver with high matching confidence
            status = VerificationStatus.VERIFIED.value
            website_status = VerificationStatus.VERIFIED.value
            status_reason = "Official company domain verified with matching identity and contact details."
            final_website = candidate_url
        elif (similarity >= 0.50 or token_coverage >= 0.50) and (
            email_status == VerificationStatus.VERIFIED.value
            or phone_status == VerificationStatus.VERIFIED.value
        ):
            # Moderate similarity accepted only when supported by verified contact data
            status = VerificationStatus.VERIFIED.value
            website_status = VerificationStatus.VERIFIED.value
            status_reason = f"Candidate domain {candidate_url} confirmed via verified contact channels."
            final_website = candidate_url
        else:
            status = VerificationStatus.NEEDS_REVIEW.value
            website_status = VerificationStatus.NEEDS_REVIEW.value
            status_reason = f"Candidate domain {candidate_url} has moderate similarity ({similarity:.2f}); flagged for review."
            final_website = candidate_url

        # RULE 5: Calculate lead_tier from VALIDATED fields, not merely non-empty fields
        if website_status == VerificationStatus.VERIFIED.value and (
            email_status == VerificationStatus.VERIFIED.value
            or phone_status == VerificationStatus.VERIFIED.value
        ):
            lead_tier = LeadTier.FULL_LEAD.value
        elif website_status == VerificationStatus.VERIFIED.value:
            lead_tier = LeadTier.WEBSITE_ONLY.value
        else:
            lead_tier = LeadTier.UNRESOLVED.value

        return VerifiedLead(
            company_name=company.name,
            location=location_str,
            status=status,
            status_reason=status_reason,
            lead_tier=lead_tier,
            website=final_website,
            website_status=website_status,
            website_source=evidence.website_source_url or candidate_url if final_website else None,
            email=valid_email,
            email_status=email_status,
            email_source=email_source if valid_email else None,
            phone=formatted_phone,
            phone_status=phone_status,
            phone_source=phone_source if formatted_phone else None,
            confidence=evidence.confidence if status == VerificationStatus.VERIFIED.value else min(evidence.confidence, 0.65),
            sources=evidence.sources or [],
            candidate_results=candidate_results,
            elapsed_seconds=duration,
        )
