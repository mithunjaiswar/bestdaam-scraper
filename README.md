# BestDaam Catalog Automation

Cloud-ready catalog refresh for BestDaam.

The automation:

1. Restores existing price history from the live catalog.
2. Refreshes Flipkart category listings with Playwright.
3. Refreshes existing Amazon matches through the official Creators API when the
   account is eligible. A 403 eligibility response safely preserves old data.
4. Preserves existing affiliate links and generates new EarnKaro links for
   product entries and curated limited-time offers when a token is available.
5. Optionally syncs products and price history to Supabase.

Secrets are supplied through GitHub Actions and are never committed.
