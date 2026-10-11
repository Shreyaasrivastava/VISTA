# VISTA Crowd Safety - UI demo

Open `index.html` in a browser. No install or server needed.
Files: index.html, privacy.html, terms.html, style.css, app.js, theme.js, favicon files, robots.txt, sitemap.xml, LAUNCH-CHECKLIST.md

Navigation: after login, a left sidebar lists the pages for that account (admin: Overview, Live zones, Cameras, Thresholds, Camera setup guide; security: Alerts, Zone status; attendee: Register, My ticket, Venue crowding; guest: Venue crowding, Location alerts). On narrow screens it collapses behind a Menu button.

Theme: the header has Light, System and Dark buttons. The choice is remembered in the browser.

Demo logins:
- jaipur.admin / jj@123 (ADM-101, Jaipur Junction only)
- govind.admin / gd@123 (ADM-102, Govind Dev Ji Temple only)
- stadium.admin / sms@123 (ADM-103, SMS Stadium only)
- security / guard123 (alert feed)
- attendee / attendee123 (registration + QR)
- Continue as guest (public venue check)

Admins can add and edit cameras (stream URL, IP address, zone, range, thresholds) for their own venue only.

Notes:
- Zone readings are simulated in the browser; refresh resets them (camera edits too).
- Login and venue scoping are front-end demo only. Real auth (JWT + RBAC, venue_id on every query) must be done in the FastAPI backend.
- QR code is a demo pattern, not scannable.

Deploy (custom domain):
1. Upload the folder to a static host such as Netlify, Cloudflare Pages, Vercel or GitHub Pages.
2. In the host's settings, add your domain.
3. At your domain registrar, add the DNS records the host shows you (usually a CNAME for www and an A or ALIAS record for the bare domain).
4. Wait for DNS to update, then confirm the site opens over https.
Then work through LAUNCH-CHECKLIST.md.
