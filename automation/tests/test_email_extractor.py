from automation.enrichment.email_extractor import extract_emails


html = """
<html>
<body>

<p>Sales: sales@company.com</p>

<p>Support: SUPPORT@company.com</p>

<a href="mailto:info@company.com">Contact</a>

<a href="mailto:jobs@company.com?subject=Resume">Jobs</a>

<p>example@example.com</p>

<p>sales@company.com</p>

</body>
</html>
"""

emails = extract_emails(html)

print(emails)