# RemoteOK Scraper

## API Endpoint
`https://remoteok.com/api` — public JSON API, no auth required.

## robots.txt Status
- Checked: 2026-05-09
- `/api` endpoint: allowed
- Rate limit: undocumented — apply 2–5s polite delay

## Scrape Policy
- Method: httpx (JSON API, no JS rendering needed)
- Endpoint: `GET https://remoteok.com/api`
- Delay: `scrape_delay_min`–`scrape_delay_max` seconds (from Settings)
- User-Agent: `scrape_user_agent` (from Settings)
- Retries: exponential backoff with jitter, max 3 attempts

## Fields Available
`slug`, `company`, `position` (title), `description`, `tags`, `salary_min`,
`salary_max`, `url`, `date`

## Notes
First element in API response is a metadata object, not a job — skip index 0.
