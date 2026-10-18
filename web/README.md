# VISTA web dashboard

Plain HTML, CSS and JavaScript. Admin and security screens read live data from the VISTA API (see ../backend). Attendee and guest screens still show sample data.

Files: index.html, privacy.html, terms.html, style.css, theme.js, config.js, api.js, sample.js, app.js, favicon files, robots.txt, sitemap.xml, LAUNCH-CHECKLIST.md

## Run it

1. Start the backend (see ../docs/PHASE1-README.md). It must allow this page's address in `CORS_ORIGINS` in `backend/.env`. The default `http://localhost:8080` already works.
2. From this folder, serve the page. Do not open index.html by double clicking, because the browser blocks API calls from file pages.
   `python -m http.server 8080`
3. Open http://localhost:8080 and log in with an account made by `python -m app.seed` (the seed prints the passwords once).

If the API is on another address, change `apiBase` in `config.js`.

## What each login sees

- **Venue admin:** Overview, Live zones, Cameras (add, edit, delete, new ingest key, apply calibration file), Thresholds, Camera setup guide. Only their own venue.
- **Security:** Alerts (placeholder until Phase 2) and Zone status for their own venue.
- **Attendee and guest:** pages with sample data until the registration and public APIs exist.
- **Platform admin (superadmin):** no dashboard yet. Use the API docs.

## Code layout

- `api.js`: every call to the backend. Nothing else uses fetch.
- `sample.js`: sample data for attendee and guest screens only.
- `app.js`: screens, navigation and forms.
- `theme.js`: light, system and dark theme.

## Notes

- The login token is kept in sessionStorage, so it is cleared when the tab closes.
- Camera stream URLs may contain a password. The table hides it, but the API returns the full URL to admin and security accounts. Hide it from the security role before launch.
- Live data refreshes every 2 seconds. A zone shows Stale after 30 seconds without a reading.

## Deploy (custom domain)

1. Upload the folder to a static host such as Netlify, Cloudflare Pages, Vercel or GitHub Pages.
2. In the host's settings, add your domain.
3. At your domain registrar, add the DNS records the host shows you (usually a CNAME for www and an A or ALIAS record for the bare domain).
4. Wait for DNS to update, then confirm the site opens over https.
5. Point `apiBase` in config.js at your real backend address, which must also be https.

Then work through LAUNCH-CHECKLIST.md.
