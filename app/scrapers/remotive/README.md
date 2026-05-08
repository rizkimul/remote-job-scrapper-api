# Remotive Scraper

## API Endpoint
`https://remotive.com/api/remote-jobs` — public JSON API, no auth required.

## robots.txt Status
- Checked: 2026-05-09
- `/api/` endpoint: allowed
- Rate limit: undocumented — apply 2–5s polite delay

## Scrape Policy
- Method: httpx (JSON API, no JS rendering needed)
- Endpoint: `GET https://remotive.com/api/remote-jobs?category=software-dev`
- Delay: `scrape_delay_min`–`scrape_delay_max` seconds (from Settings)
- User-Agent: `scrape_user_agent` (from Settings)
- Retries: exponential backoff with jitter, max 3 attempts

## Fields Available
`id`, `title`, `company_name`, `description` (HTML string), `tags`,
`salary`, `url`, `publication_date`

## Notes
`description` is raw HTML — strip tags in normalize stage, do NOT store HTML.
