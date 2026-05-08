# We Work Remotely (WWR) Scraper

## Source URL
`https://weworkremotely.com/remote-jobs/search?term=developer`

## robots.txt Status
- Checked: 2026-05-09
- `/remote-jobs/` section: allowed
- No explicit API — HTML scraping required

## Scrape Policy
- Method: httpx + BeautifulSoup4 (static HTML)
- Endpoint: `GET https://weworkremotely.com/remote-jobs/search?term=developer`
- Delay: `scrape_delay_min`–`scrape_delay_max` seconds (from Settings)
- User-Agent: `scrape_user_agent` (from Settings)
- Retries: exponential backoff with jitter, max 3 attempts

## HTML Structure
Jobs are in `<section class="jobs"> > article.feature` elements.
Each article contains: h2 (title), span.company (company), span.region (location),
and an href link to the detail page.

## Notes
Detail page fetch needed for full description — consider caching per ScrapeRun.
