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
    "gethuman.com",
    "local.yahoo.com",
    "localsearch.com",
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
    "carriersource.io",
    "dotsearch.us",
    "fenderr.com",
    "findtruckservice.com",
    "freightconnect.com",
    "freightdatawatch.com",
    "freightvet.com",
    "lanefinder.com",
    "loadwrap.com",
    "logisticsvendorlocator.com",
    "movequotecheck.com",
    "mtstruckservice.com",
    "otrucking.com",
    "prohrhq.com",
    "quicktransportsolutions.com",
    "roserocket.com",
    "safer.fmcsa.dot.gov",
    "searchcarriers.com",
    "superpages.com",
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
    "move-and-care.com",
    "movebuddha.com",
    "moverreviews.com",
    "movers.com",
    "moving.com",
    "movingcompanyreviews.com",
    "movinglabor.com",
    "mymove.com",
    "topmovingreviews.com",
    "uship.com",

    # Government and regulatory portals
    "courtlistener.com",
    "fmcsa.dot.gov",
    "justia.com",
    "osha.gov",
    "puc.pa.gov",
    "sec.gov",

    # People-search, telephone lookup, and postal directories
    "zip-codes.com",
    "united-local.com",
    "allbluebook.com",
    "siccode.com",
    "wattagnet.com",
    "showmelocal.com",
    "usbizs.com",
    "myhomepro.org",
    "whereorg.com",
    "businessyab.com",
    "carriertruth.com",
    "fleetcollect.net",
    "dispatchff.com",
    "nationalpublicdata.com",
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

    # E-commerce retail marketplaces (not B2B freight or service company sites)
    "aliexpress.com",
    "alibaba.com",
    "temu.com",
    "shein.com",
    "ebay.com",
    "amazon.com",
    "walmart.com",
    "target.com",
    "etsy.com",
    "wish.com",
    "overstock.com",
    "wayfair.com",

    # Music, artists, and entertainment platforms
    "discogs.com",
    "allmusic.com",
    "last.fm",
    "bandcamp.com",
    "soundcloud.com",
    "reverbnation.com",
    "spotify.com",

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
    # Europe
    "ca", "uk", "co.uk", "de", "fr", "it", "es", "nl", "be", "ch", "at",
    "pl", "cz", "se", "no", "dk", "fi", "ru", "ua", "by", "pt", "gr",
    "ro", "bg", "hr", "rs", "sk", "si", "lt", "lv", "ee", "is", "lu",
    # East Asia
    "cn", "jp", "kr", "tw", "hk", "mo",
    # South & Southeast Asia
    "in", "pk", "bd", "vn", "th", "my", "sg", "ph", "id", "lk", "mm",
    "kh", "la", "np", "bt", "mv",
    # Central Asia
    "uz", "kz", "ge", "az", "am", "tm", "kg", "tj",
    # Oceania
    "au", "nz",
    # Africa
    "za", "ng", "eg", "ke", "et", "gh", "tz", "ug", "cm", "sn", "ci",
    "bw", "rw",
    # Latin America
    "br", "ar", "mx", "cl", "co", "pe", "bo", "uy", "py", "ec", "ve",
    "gt", "hn", "cr", "pa", "do", "cu", "gy", "sr",
    # Middle East
    "tr", "sa", "ae", "il", "ir", "iq", "jo",
    # Compound TLDs (explicit for common patterns)
    "com.bo", "com.ar", "com.br", "com.mx", "com.co", "com.pe",
    "com.ng", "com.eg", "com.pk", "com.bd", "com.vn", "com.my",
    "com.sg", "com.ph", "com.au", "com.tr", "com.sa",
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


# Domestic US or widely accepted tech/commercial top-level domains
DOMESTIC_OR_GLOBAL_TLDS: set[str] = {
    "com", "net", "org", "edu", "gov", "mil", "us", "biz", "info",
    "co", "io", "ai", "app", "dev", "me", "tv", "cc", "ly", "to",
    "tech", "pro", "online", "site", "store", "llc", "inc", "corp",
}


def is_foreign_cctld(url_or_domain: str, domestic_country: str = "US") -> bool:
    """
    Check if a domain ends with a foreign country-code TLD incompatible with domestic US companies.
    """
    domain = normalize_domain(url_or_domain)
    if not domain:
        return False

    parts = domain.split(".")
    if len(parts) >= 2:
        last_part = parts[-1]
        # Any 2-letter extension that is not US or a common global/tech TLD is a foreign ccTLD
        if len(last_part) == 2 and last_part not in DOMESTIC_OR_GLOBAL_TLDS:
            return True
        two_part = ".".join(parts[-2:])
        if two_part in FOREIGN_CCTLDS:
            return True
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
