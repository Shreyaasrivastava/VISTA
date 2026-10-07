# VISTA Crowd Safety - UI demo

Open `index.html` in a browser. No install or server needed.
Files: index.html, style.css, app.js

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
