"""
Test LinkedIn employee size gate (10-15 employees).
"""
from automation.pipeline_v2.apify_enricher import ApifyLinkedInEnricher


def test_size_gate_exact_count_in_range():
    # 12 is within [10, 15]
    count, text, passed = ApifyLinkedInEnricher._size({"employeeCount": 12})
    assert count == 12
    assert passed is True


def test_size_gate_exact_count_below_min():
    # 5 is below 10
    count, text, passed = ApifyLinkedInEnricher._size({"employeeCount": 5})
    assert count == 5
    assert passed is False


def test_size_gate_exact_count_above_max():
    # 25 is above 15
    count, text, passed = ApifyLinkedInEnricher._size({"employeeCount": 25})
    assert count == 25
    assert passed is False


def test_size_gate_range_overlapping():
    # '11-50 employees' overlaps with [10, 15]
    count, text, passed = ApifyLinkedInEnricher._size({"employeeRange": "11-50 employees"})
    assert passed is True

    # '10-20' overlaps
    count, text, passed = ApifyLinkedInEnricher._size({"employeeRange": "10-20"})
    assert passed is True


def test_size_gate_range_strictly_above():
    # '51-200' does not overlap [10, 15]
    count, text, passed = ApifyLinkedInEnricher._size({"employeeRange": "51-200 employees"})
    assert passed is False


def test_size_gate_range_strictly_below():
    # '1-9 employees' does not overlap [10, 15]
    count, text, passed = ApifyLinkedInEnricher._size({"employeeRange": "1-9 employees"})
    assert passed is False


def test_size_gate_plus_notation():
    # '100+' is above 15
    count, text, passed = ApifyLinkedInEnricher._size({"employeeRange": "100+ employees"})
    assert passed is False

