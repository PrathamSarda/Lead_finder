from dataclasses import dataclass
from urllib.parse import urlparse


EXCLUDED_DOMAINS = {
    # Social networks
    "facebook.com",
    "instagram.com",
    "linkedin.com",
    "pinterest.com",
    "reddit.com",
    "threads.net",
    "tiktok.com",
    "twitter.com",
    "x.com",
    "youtube.com",

    # Business directories and company databases
    "bbb.org",
    "bizapedia.com",
    "bloomberg.com",
    "buzzfile.com",
    "chamberofcommerce.com",
    "clustrmaps.com",
    "cortera.com",
    "crunchbase.com",
    "datastical.com",
    "dnb.com",
    "foursquare.com",
    "findglocal.com",
    "gethuman.com",
    "local.yahoo.com",
    "localsearch.com",
    "manta.com",
    "mapquest.com",
    "opencorporates.com",
    "privco.com",
    "thebluebook.com",
    "thomasnet.com",
    "webstatsdomain.org",
    "worldorgs.com",
    "yellowpages.com",
    "yelp.com",
    "zoominfo.com",

    # FMCSA and carrier directories
    "arktms.com",
    "brokersnapshot.com",
    "carrier411.com",
    "carriersource.io",
    "fenderr.com",
    "findtruckservice.com",
    "freightconnect.com",
    "freightvet.com",
    "lanefinder.com",
    "loadwrap.com",
    "movers.com",
    "mtstruckservice.com",
    "prohrhq.com",
    "quicktransportsolutions.com",
    "safer.fmcsa.dot.gov",
    "searchcarriers.com",
    "thetruckersreport.com",
    "truckcarrierhub.com",
    "truckcompaniesin.com",
    "truckdriver.com",
    "truckdrivingjobs.com",
    "truckingdatabase.com",
    "usdotlookup.com",
    "uship.com",

    # People-search and unrelated information sites
    "mylife.com",
    "sports-reference.com",
    "wikipedia.org",

    # Job platforms
    "careerbuilder.com",
    "glassdoor.com",
    "indeed.com",
    "monster.com",
    "simplyhired.com",
    "snagajob.com",
    "ziprecruiter.com",
}


EXCLUDED_DOMAIN_FRAGMENTS = {
    "business-directory",
    "company-directory",
    "companyregistry",
    "company-registry",
    "directory",
    "find-local",
    "locations",
    "lookup",
    "people-search",
    "shipping-logistics",
    "trucking-warehousing",
}


EXCLUDED_PATH_SEGMENTS = {
    "business-directory",
    "companies",
    "company",
    "company-profile",
    "directory",
    "listing",
    "listings",
    "locations",
    "member",
    "members",
    "profile",
    "profiles",
    "search",
    "usdot",
}


@dataclass(frozen=True)
class CandidateFilterResult:
    accepted: bool
    reason: str | None = None


def normalize_hostname(url: str) -> str:
    """
    Extract and normalize a hostname from a URL.
    """

    parsed_url = urlparse(url)

    return (
        parsed_url.netloc
        .strip()
        .lower()
        .removeprefix("www.")
    )


def is_excluded_domain(hostname: str) -> bool:
    """
    Check known directory, social and aggregator domains.
    """

    return any(
        hostname == excluded_domain
        or hostname.endswith(f".{excluded_domain}")
        for excluded_domain in EXCLUDED_DOMAINS
    )


from automation.verification.directory_registry import (
    is_directory_domain as registry_is_directory,
    is_civic_or_gov_domain,
    is_foreign_cctld,
)


def evaluate_candidate_url(
    url: str,
) -> CandidateFilterResult:
    """
    Decide whether a search-result URL is plausible enough
    to enter the scoring and homepage-validation stages.
    """

    parsed_url = urlparse(url)

    if parsed_url.scheme not in {"http", "https"}:
        return CandidateFilterResult(
            accepted=False,
            reason="unsupported_scheme",
        )

    hostname = normalize_hostname(url)

    if not hostname:
        return CandidateFilterResult(
            accepted=False,
            reason="missing_hostname",
        )

    if is_excluded_domain(hostname):
        return CandidateFilterResult(
            accepted=False,
            reason="excluded_domain",
        )

    if any(
        fragment in hostname
        for fragment in EXCLUDED_DOMAIN_FRAGMENTS
    ):
        return CandidateFilterResult(
            accepted=False,
            reason="directory_domain_pattern",
        )

    path_segments = {
        segment.strip().lower()
        for segment in parsed_url.path.split("/")
        if segment.strip()
    }

    if path_segments.intersection(
        EXCLUDED_PATH_SEGMENTS
    ):
        return CandidateFilterResult(
            accepted=False,
            reason="directory_path_pattern",
        )

    if registry_is_directory(hostname):
        return CandidateFilterResult(
            accepted=False,
            reason="excluded_domain",
        )

    if is_civic_or_gov_domain(hostname):
        return CandidateFilterResult(
            accepted=False,
            reason="civic_domain",
        )

    if is_foreign_cctld(hostname):
        return CandidateFilterResult(
            accepted=False,
            reason="foreign_cctld",
        )

    return CandidateFilterResult(
        accepted=True,
    )