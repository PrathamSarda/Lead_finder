"""
Target Discovery via Serper.dev Google Maps API (/maps).
Discovers local small businesses with high accuracy, extracting company name,
website domain, address, rating, and phone.
Rotates through diverse trade niches and US cities to ensure an endless stream of fresh companies.
Includes expanded fallback samples so testing never runs dry.
"""
from __future__ import annotations

import os
import random
import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any
from urllib.parse import urlparse

import requests


@dataclass(slots=True)
class DiscoveredBusiness:
    title: str
    domain: str | None
    website: str | None
    phone: str | None = None
    address: str | None = None
    rating: float | None = None
    reviews: int | None = None
    category: str | None = None
    cid: str | None = None


def extract_domain(url: str | None) -> str | None:
    if not url:
        return None
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    try:
        netloc = urlparse(url).netloc.lower()
        return netloc.removeprefix("www.") if netloc else None
    except Exception:
        return None


# Built-in rotation lists for diverse SMB discovery across regions & industries
REGION_CONFIGS: dict[str, dict[str, Any]] = {
    "US": {
        "name": "United States",
        "gl": "us",
        "hl": "en",
        "indeed_domain": "indeed.com",
        "queries": [
            "commercial HVAC contractors in Dallas, TX",
            "electrical contractors in Austin, TX",
            "commercial roofing companies in Houston, TX",
            "plumbing contractors in San Antonio, TX",
            "landscape design contractors in Phoenix, AZ",
            "general contractors in Denver, CO",
            "commercial cleaning companies in Atlanta, GA",
            "digital marketing agencies in Miami, FL",
            "auto repair and collision centers in Charlotte, NC",
            "freight logistics companies in Columbus, OH",
            "custom home builders in Nashville, TN",
            "solar installation companies in Tampa, FL",
        ],
    },
    "UK": {
        "name": "United Kingdom",
        "gl": "gb",
        "hl": "en",
        "indeed_domain": "indeed.co.uk",
        "queries": [
            "commercial HVAC companies in London, UK",
            "electrical contractors in Manchester, UK",
            "commercial roofing companies in Birmingham, UK",
            "plumbing contractors in Leeds, UK",
            "digital marketing agencies in Bristol, UK",
            "building contractors in Glasgow, UK",
            "commercial cleaning companies in Edinburgh, UK",
            "logistics companies in Liverpool, UK",
        ],
    },
    "AU": {
        "name": "Australia",
        "gl": "au",
        "hl": "en",
        "indeed_domain": "au.indeed.com",
        "queries": [
            "commercial HVAC contractors in Sydney, NSW",
            "electrical contractors in Melbourne, VIC",
            "commercial roofing companies in Brisbane, QLD",
            "plumbing contractors in Perth, WA",
            "digital marketing agencies in Adelaide, SA",
            "commercial builders in Gold Coast, QLD",
            "facilities maintenance companies in Canberra, ACT",
        ],
    },
    "CA": {
        "name": "Canada",
        "gl": "ca",
        "hl": "en",
        "indeed_domain": "ca.indeed.com",
        "queries": [
            "commercial HVAC contractors in Toronto, ON",
            "electrical contractors in Vancouver, BC",
            "commercial roofing companies in Montreal, QC",
            "plumbing contractors in Calgary, AB",
            "digital marketing agencies in Ottawa, ON",
            "general contractors in Edmonton, AB",
        ],
    },
}

DEFAULT_DISCOVERY_QUERIES = REGION_CONFIGS["US"]["queries"]


class SerperMapsDiscovery:
    """Discovers SMB businesses in specific locations via Serper Google Maps API."""

    ENDPOINT = "https://google.serper.dev/maps"

    def __init__(self, api_key: str | None = None):
        self.api_key = (api_key or os.getenv("SERPER_API_KEY", "")).strip()

    def discover(self, query: str | None = None, limit: int = 20, region: str = "US") -> list[DiscoveredBusiness]:
        """
        Search Google Maps via Serper.
        If query is empty or default, rotates to an active target query for the target region.
        """
        reg = region.upper() if region else "US"
        if "," in reg:
            regions = [r.strip() for r in reg.split(",") if r.strip()]
            combined: list[DiscoveredBusiness] = []
            per_limit = max(1, limit // len(regions))
            for sub_reg in regions:
                sub_res = self.discover(query=query, limit=per_limit, region=sub_reg)
                combined.extend(sub_res)
            return combined[:limit]

        config = REGION_CONFIGS.get(reg, REGION_CONFIGS["US"])
        queries_pool = config.get("queries", DEFAULT_DISCOVERY_QUERIES)

        active_query = query.strip() if query and query.strip() else random.choice(queries_pool)

        if not self.api_key:
            return self._mock_fallback(active_query, limit)

        headers = {
            "X-API-KEY": self.api_key,
            "Content-Type": "application/json",
        }
        payload = {
            "q": active_query,
            "num": limit,
            "gl": config.get("gl", "us"),
            "hl": config.get("hl", "en"),
        }

        try:
            response = requests.post(self.ENDPOINT, headers=headers, json=payload, timeout=15)
            response.raise_for_status()
            data = response.json()
            places = data.get("places", [])
            return self._parse_places(places, limit)
        except Exception as exc:
            print(f"[Serper] Error querying '{active_query}': {exc}. Using fallback pool.")
            return self._mock_fallback(active_query, limit)

    def lookup_company(self, company_name: str, location: str | None = None, region: str = "US") -> DiscoveredBusiness | None:
        """Use Google Maps to enrich a company without substituting demo data."""
        if not self.api_key:
            raise RuntimeError("SERPER_API_KEY is required for Google Maps enrichment.")
        query = ", ".join(part for part in (company_name, location) if part)
        reg = (region.split(",")[0].strip().upper()) if region else "US"
        config = REGION_CONFIGS.get(reg, REGION_CONFIGS["US"])

        response = requests.post(
            self.ENDPOINT,
            headers={"X-API-KEY": self.api_key, "Content-Type": "application/json"},
            json={
                "q": query,
                "num": 5,
                "gl": config.get("gl", "us"),
                "hl": config.get("hl", "en"),
            },
            timeout=15,
        )
        response.raise_for_status()
        places = self._parse_places(response.json().get("places", []), 5)
        normalize = lambda value: re.sub(r"[^a-z0-9]", "", value.lower())
        target = normalize(company_name)
        ranked = sorted(places, key=lambda place: SequenceMatcher(None, target, normalize(place.title)).ratio(), reverse=True)
        if not ranked:
            return None
        best = ranked[0]
        score = SequenceMatcher(None, target, normalize(best.title)).ratio()
        return best if score >= 0.55 else None

    def _parse_places(self, places: list[dict[str, Any]], limit: int) -> list[DiscoveredBusiness]:
        results: list[DiscoveredBusiness] = []
        for p in places[:limit]:
            title = p.get("title") or p.get("name")
            if not title:
                continue

            website = p.get("website")
            domain = extract_domain(website)

            # Skip generic platforms if returned as website
            if domain and any(d in domain for d in ("facebook.com", "instagram.com", "yelp.com", "yellowpages.com")):
                website = None
                domain = None

            results.append(
                DiscoveredBusiness(
                    title=title.strip(),
                    domain=domain,
                    website=website,
                    phone=p.get("phoneNumber") or p.get("phone"),
                    address=p.get("address"),
                    rating=float(p.get("rating", 0.0)) if p.get("rating") else None,
                    reviews=int(p.get("reviewsCount") or p.get("reviews", 0)) if (p.get("reviewsCount") or p.get("reviews")) else None,
                    category=p.get("category") or p.get("type") or (p.get("types")[0] if p.get("types") else None),
                    cid=p.get("cid"),
                )
            )
        return results

    def _mock_fallback(self, query: str, limit: int) -> list[DiscoveredBusiness]:
        """Realistic sample businesses pool for testing pipeline workflows when no key is set."""
        print(f"[Serper Maps] (Demo Mode) Sourcing candidates for: '{query}'")
        samples = [
            DiscoveredBusiness(
                title="Apex Plumbing Solutions",
                domain="apexplumbingaustin.com",
                website="https://apexplumbingaustin.com",
                phone="+1 (512) 555-0143",
                address="1024 Congress Ave, Austin, TX 78701",
                rating=4.8,
                reviews=42,
                category="Plumbing contractor",
            ),
            DiscoveredBusiness(
                title="Hill Country Electric Services",
                domain="hillcountryelectric.com",
                website="https://hillcountryelectric.com",
                phone="+1 (512) 555-0155",
                address="2201 S 1st St, Austin, TX 78704",
                rating=4.7,
                reviews=38,
                category="Electrical contractor",
            ),
            DiscoveredBusiness(
                title="Cedar Park HVAC Pros",
                domain="cedarparkhvac.com",
                website="https://cedarparkhvac.com",
                phone="+1 (512) 555-0162",
                address="1400 Whitestone Blvd, Cedar Park, TX 78613",
                rating=4.9,
                reviews=55,
                category="HVAC contractor",
            ),
            DiscoveredBusiness(
                title="Travis Roofing & Construction",
                domain="travisroofingtx.com",
                website="https://travisroofingtx.com",
                phone="+1 (512) 555-0181",
                address="810 Barton Springs Rd, Austin, TX 78704",
                rating=4.6,
                reviews=29,
                category="Roofing contractor",
            ),
            DiscoveredBusiness(
                title="Blue Ridge Financial Advisors",
                domain="blueridgefa.com",
                website="https://blueridgefa.com",
                phone="+1 (512) 555-0189",
                address="500 W 2nd St, Austin, TX 78701",
                rating=4.9,
                reviews=19,
                category="Financial consultant",
            ),
            DiscoveredBusiness(
                title="Lone Star Digital Marketing",
                domain="lonestarmarketing.co",
                website="https://lonestarmarketing.co",
                phone="+1 (512) 555-0199",
                address="1200 S Lamar Blvd, Austin, TX 78704",
                rating=4.7,
                reviews=31,
                category="Marketing agency",
            ),
            DiscoveredBusiness(
                title="Oak Springs Auto Repair",
                domain="oakspringsautorepair.com",
                website="https://oakspringsautorepair.com",
                phone="+1 (512) 555-0210",
                address="3102 E 12th St, Austin, TX 78702",
                rating=4.8,
                reviews=64,
                category="Auto repair shop",
            ),
            DiscoveredBusiness(
                title="Capitol City Landscaping",
                domain="capitolcitylandscaping.com",
                website="https://capitolcitylandscaping.com",
                phone="+1 (512) 555-0233",
                address="4900 Burnet Rd, Austin, TX 78756",
                rating=4.5,
                reviews=22,
                category="Landscape design",
            ),
            DiscoveredBusiness(
                title="Austin Commercial Logistics",
                domain="austinlogisticstx.com",
                website="https://austinlogisticstx.com",
                phone="+1 (512) 555-0177",
                address="4301 E Riverside Dr, Austin, TX 78741",
                rating=4.5,
                reviews=15,
                category="Logistics service",
            ),
            DiscoveredBusiness(
                title="Red River Freight Logistics",
                domain="redriverfreight.com",
                website="https://redriverfreight.com",
                phone="+1 (512) 555-0288",
                address="7000 Metropolis Dr, Austin, TX 78744",
                rating=4.3,
                reviews=12,
                category="Freight forwarding",
            ),
            DiscoveredBusiness(
                title="Summit Peak Construction",
                domain="summitpeakbuilders.com",
                website="https://summitpeakbuilders.com",
                phone="+1 (303) 555-0144",
                address="1700 Lincoln St, Denver, CO 80203",
                rating=4.8,
                reviews=45,
                category="General contractor",
            ),
            DiscoveredBusiness(
                title="Pioneer Valley Electric",
                domain="pioneervalleyelectric.com",
                website="https://pioneervalleyelectric.com",
                phone="+1 (602) 555-0172",
                address="2400 E Camelback Rd, Phoenix, AZ 85016",
                rating=4.9,
                reviews=51,
                category="Electrical contractor",
            ),
            DiscoveredBusiness(
                title="Biscayne Bay Facility Services",
                domain="biscaynebayfs.com",
                website="https://biscaynebayfs.com",
                phone="+1 (305) 555-0193",
                address="801 Brickell Ave, Miami, FL 33131",
                rating=4.7,
                reviews=34,
                category="Commercial cleaning",
            ),
            DiscoveredBusiness(
                title="Vanguard Security Solutions",
                domain="vanguardsecuritytx.com",
                website="https://vanguardsecuritytx.com",
                phone="+1 (214) 555-0168",
                address="2100 Ross Ave, Dallas, TX 75201",
                rating=4.8,
                reviews=39,
                category="Security system installation",
            ),
            DiscoveredBusiness(
                title="Pinnacle Precision Tooling",
                domain="pinnacleprecisionmfg.com",
                website="https://pinnacleprecisionmfg.com",
                phone="+1 (704) 555-0128",
                address="100 N Tryon St, Charlotte, NC 28202",
                rating=4.6,
                reviews=27,
                category="Machine shop",
            ),
            DiscoveredBusiness(
                title="ClearChoice Glass & Glazing",
                domain="clearchoiceglazing.com",
                website="https://clearchoiceglazing.com",
                phone="+1 (404) 555-0182",
                address="3344 Peachtree Rd, Atlanta, GA 30326",
                rating=4.9,
                reviews=60,
                category="Glass repair and replacement",
            ),
            DiscoveredBusiness(
                title="Crossroads Transport Logistics",
                domain="crossroadstransport.co",
                website="https://crossroadstransport.co",
                phone="+1 (317) 555-0151",
                address="1 Monument Cir, Indianapolis, IN 46204",
                rating=4.5,
                reviews=18,
                category="Freight logistics",
            ),
            DiscoveredBusiness(
                title="Ironwood Custom Cabinetry",
                domain="ironwoodcabinetry.com",
                website="https://ironwoodcabinetry.com",
                phone="+1 (615) 555-0136",
                address="400 Broadway, Nashville, TN 37203",
                rating=4.9,
                reviews=41,
                category="Cabinet maker",
            ),
            DiscoveredBusiness(
                title="Desert Sun Solar Contractors",
                domain="desertsunsolaraz.com",
                website="https://desertsunsolaraz.com",
                phone="+1 (480) 555-0119",
                address="7014 E Camelback Rd, Scottsdale, AZ 85251",
                rating=4.7,
                reviews=37,
                category="Solar energy system service",
            ),
            DiscoveredBusiness(
                title="Precision Hydraulics & Hose",
                domain="precisionhydraulics.net",
                website="https://precisionhydraulics.net",
                phone="+1 (713) 555-0185",
                address="1000 Louisiana St, Houston, TX 77002",
                rating=4.8,
                reviews=23,
                category="Hydraulic repair service",
            ),
            DiscoveredBusiness(
                title="Frontier Masonry & Restoration",
                domain="frontiermasonryco.com",
                website="https://frontiermasonryco.com",
                phone="+1 (801) 555-0164",
                address="222 S Main St, Salt Lake City, UT 84101",
                rating=4.8,
                reviews=31,
                category="Masonry contractor",
            ),
            DiscoveredBusiness(
                title="Magnolia Commercial Painting",
                domain="magnoliapaintingfl.com",
                website="https://magnoliapaintingfl.com",
                phone="+1 (813) 555-0147",
                address="100 N Tampa St, Tampa, FL 33602",
                rating=4.6,
                reviews=28,
                category="Painting contractor",
            ),
        ]
        # Shuffle pool slightly for variety in fallback mode
        shuffled = list(samples)
        random.shuffle(shuffled)
        return shuffled[:limit]
