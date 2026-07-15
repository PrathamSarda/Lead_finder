from automation.resolvers.scorer import (
    score_search_result,
)


def test_official_matching_domain_scores_highly():
    score = score_search_result(
        company_name="Cherokee Culvert Company Inc",
        location="Macon, GA",
        title="Cherokee Culvert Company",
        url="https://cherokeeculvert.com/",
        description=(
            "Cherokee Culvert manufactures drainage "
            "products in Georgia."
        ),
    )

    assert score >= 35


def test_directory_domain_is_rejected():
    score = score_search_result(
        company_name="Cain AM Bickley LLC",
        location="Marshallville, GA",
        title="Cain AM Bickley LLC",
        url=(
            "https://www.datastical.com/"
            "transportation/company/111/"
        ),
        description="Transportation company profile",
    )

    assert score == -1_000


def test_yahoo_local_is_rejected():
    score = score_search_result(
        company_name="CWT Farms International Inc",
        location="Gainesville, GA",
        title="CWT Farms International",
        url=(
            "https://local.yahoo.com/"
            "info-cwt-farms/"
        ),
        description="Local business listing",
    )

    assert score == -1_000


def test_unrelated_domain_scores_below_official_domain():
    official_score = score_search_result(
        company_name="Biolab Inc",
        location="Lawrenceville, GA",
        title="BioLab",
        url="https://www.biolabinc.com/",
        description="BioLab official corporate website",
    )

    unrelated_score = score_search_result(
        company_name="Biolab Inc",
        location="Lawrenceville, GA",
        title="Chemical Industry News",
        url="https://industrynews.example.com/article",
        description="Article mentioning BioLab",
    )

    assert official_score > unrelated_score


def test_company_profile_path_receives_penalty():
    homepage_score = score_search_result(
        company_name="Example Logistics LLC",
        location="Dallas, TX",
        title="Example Logistics",
        url="https://examplelogistics.com/",
        description="Transportation and logistics services",
    )

    profile_score = score_search_result(
        company_name="Example Logistics LLC",
        location="Dallas, TX",
        title="Example Logistics",
        url=(
            "https://unknown-directory.test/"
            "company/example-logistics"
        ),
        description="Business company profile",
    )

    assert homepage_score > profile_score