# BestDaam Catalog Automation

Cloud-ready catalog refresh for BestDaam.

The automation:

1. Restores existing price history from the live catalog.
2. Refreshes Flipkart category listings with Playwright.
3. Preserves verified Amazon matches and existing affiliate links.
4. Generates new EarnKaro links when a token is available.
5. Optionally syncs products and price history to Supabase.

Secrets are supplied through GitHub Actions and are never committed.
