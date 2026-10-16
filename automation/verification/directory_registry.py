"""
Centralized directory and aggregator registry.

Identifies directories, freight brokers, aggregators, job boards, social networks,
civic portals, and foreign ccTLD domains that should NEVER be accepted as official
US company websites.
"""
from __future__ import annotations

import re
from urllib.parse import urlparse


EXCLUDED_DOMAINS: set[str] = {
    # Social networks and content aggregators
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
    "vimeo.com",
    "wikipedia.org",

    # Business directories and corporate databases
    "allbiz.com",
    "apollo.io",
    "appsruntheworld.com",
    "bbb.org",
    "birdeye.com",
    "bizapedia.com",
    "bloomberg.com",
    "bubba.ai",
    "buzzfile.com",
    "chamberofcommerce.com",
    "clustrmaps.com",
    "clutch.co",
    "cortera.com",
    "crunchbase.com",
    "datastical.com",
    "dcontrol.com",
    "dnb.com",
    "dandb.com",
    "findglocal.com",
    "foursquare.com",
    "fyple.com",
    "glassdoor.com",
    "local.yahoo.com",
    "manta.com",
    "mapquest.com",
    "myplaniq.com",
    "newbizbot.ai",
    "opencorporates.com",
    "pitchbook.com",
    "privco.com",
    "rocketreach.co",
    "signalhire.com",
    "thebluebook.com",
    "thomasnet.com",
    "webstatsdomain.org",
    "whatsinproducts.com",
    "worldorgs.com",
    "yellowpages.com",
    "yelp.com",
    "zoominfo.com",

    # FMCSA, trucking, carrier and broker directories
    "arktms.com",
    "brokersnapshot.com",
    "carrier411.com",
    "dotsearch.us",
    "findtruckservice.com",
    "freightconnect.com",
    "freightdatawatch.com",
    "freightvet.com",
    "lanefinder.com",
    "loadwrap.com",
    "logisticsvendorlocator.com",
    "mtstruckservice.com",
    "quicktransportsolutions.com",
    "roserocket.com",
    "safer.fmcsa.dot.gov",
    "searchcarriers.com",
    "thetruckersreport.com",
    "truckcarrierhub.com",
    "truckcompaniesin.com",
    "truckdriver.com",
    "truckdrivingjobs.com",
    "truckingdatabase.com",
    "usdotlookup.com",

    # Moving company aggregators and broker portals
    "bestcrosscountrymovers.com",
    "crosscountrymovers.com",
    "greatguysmovers.com",
    "hireahelper.com",
    "movebuddha.com",
    "moverreviews.com",
    "moving.com",
    "movingcompanyreviews.com",
    "movinglabor.com",
    "mymove.com",
    "topmovingreviews.com",

    # Government and regulatory portals
    "courtlistener.com",
    "fmcsa.dot.gov",
    "justia.com",
    "osha.gov",
    "puc.pa.gov",
    "sec.gov",

    # People-search and telephone lookup
    "mylife.com",
    "sports-reference.com",
    "telephonedirectories.us",
    "whitepages.com",
    "anywho.com",

    # Job platforms
    "careerbuilder.com",
    "indeed.com",
    "monster.com",
    "simplyhired.com",
    "snagajob.com",
    "ziprecruiter.com",

    # Municipal and civic domains misattributed to companies
    "mckeesrocks.org",
    "mckeesrocks.com",
}

EXCLUDED_DOMAIN_FRAGMENTS: set[str] = {
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
    "truckingdatabase",
    "brokersnapshot",
    "crosscountrymovers",
    "usdotlookup",
    "searchcarriers",
}

EXCLUDED_PATH_SEGMENTS: set[str] = {
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
    "carrier",
    "dot",
}

# Foreign country-code top-level domains incompatible with domestic US operations
FOREIGN_CCTLDS: set[str] = {
    "ca", "uk", "co.uk", "de", "fr", "it", "es", "nl", "be", "ch", "at",
    "pl", "cz", "se", "no", "dk", "fi", "ru", "ua", "by", "cn",
    "jp", "kr", "in", "pk", "bd", "vn", "th", "my", "sg", "ph",
    "id", "au", "nz", "za", "ng", "eg", "ke", "br", "ar", "mx",
    "cl", "co", "pe", "tr", "sa", "ae", "il", "ir", "iq", "jo",
}


def normalize_domain(url_or_domain: str) -> str:
    """Extract and normalize a lowercase hostname from a URL or domain string."""
    if not url_or_domain:
        return ""
    target = url_or_domain.strip().lower()
    if "://" in target:
        try:
            parsed = urlparse(target)
            target = parsed.netloc or parsed.path
        except Exception:
            pass
    elif "/" in target:
        target = target.split("/", 1)[0]

    # Remove port and leading www
    target = target.split(":", 1)[0].strip()
    return target.removeprefix("www.")


def is_directory_domain(url_or_domain: str) -> bool:
    """
    Check if a domain matches known directories, aggregators, or carrier portals.
    """
    domain = normalize_domain(url_or_domain)
    if not domain:
        return False

    if any(domain == exc or domain.endswith(f".{exc}") for exc in EXCLUDED_DOMAINS):
        return True

    if any(frag in domain for frag in EXCLUDED_DOMAIN_FRAGMENTS):
        return True

    return False


CIVIC_DOMAINS: set[str] = {
    "mckeesrocks.org",
    "mckeesrocks.com",
}


def is_civic_or_gov_domain(url_or_domain: str) -> bool:
    """
    Check if a domain is a government, municipal, or public institution domain.
    """
    domain = normalize_domain(url_or_domain)
    if not domain:
        return False

    if domain in CIVIC_DOMAINS or any(domain.endswith(f".{c}") for c in CIVIC_DOMAINS):
        return True

    if domain.endswith(".gov") or domain.endswith(".mil"):
        return True

    # Common municipal patterns like boroughof..., townof..., cityof...
    municipal_prefixes = ("boroughof", "townof", "cityof", "countyof")
    main_label = domain.split(".")[0]
    if any(main_label.startswith(p) for p in municipal_prefixes):
        return True

    return False


def is_foreign_cctld(url_or_domain: str, domestic_country: str = "US") -> bool:
    """
    Check if a domain ends with a foreign country-code TLD incompatible with domestic US companies.
    """
    domain = normalize_domain(url_or_domain)
    if not domain:
        return False

    parts = domain.split(".")
    if len(parts) >= 2:
        # Check two-part TLD like .co.uk
        two_part = ".".join(parts[-2:])
        if two_part in FOREIGN_CCTLDS:
            return True
        last_part = parts[-1]
        if last_part in FOREIGN_CCTLDS:
            return True

    return False


def evaluate_domain_plausibility(url: str, domestic_country: str = "US") -> tuple[bool, str | None]:
    """
    Evaluate whether a URL belongs to a plausible company website.

    Returns:
        (is_plausible, rejection_reason)
    """
    if not url:
        return False, "missing_url"

    parsed = urlparse(url.strip())
    if parsed.scheme not in {"http", "https"}:
        return False, "unsupported_scheme"

    domain = normalize_domain(url)
    if not domain:
        return False, "missing_domain"

    if is_directory_domain(domain):
        return False, f"directory_domain:{domain}"

    if is_civic_or_gov_domain(domain):
        return False, f"civic_or_gov_domain:{domain}"

    if is_foreign_cctld(domain, domestic_country=domestic_country):
        return False, f"foreign_cctld:{domain}"

    path_segments = {
        seg.strip().lower()
        for seg in parsed.path.split("/")
        if seg.strip()
    }
    if path_segments.intersection(EXCLUDED_PATH_SEGMENTS):
        return False, "directory_path_pattern"

    return True, None
