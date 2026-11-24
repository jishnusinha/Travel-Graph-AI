# Visual Deviations Log

| Area | Mockup | Decision |
|---|---|---|
| OAuth Google/GitHub | Login/Signup | Buttons shown disabled: “Not available in local demo” |
| Premium upsell | Plan / My Trips / Settings | Omitted |
| 2FA toggle | Settings | Shown disabled / Unavailable |
| Dashboard metrics | 248 trips / ₹2,946 AI cost | Replaced with DB-derived seed metrics; AI cost in **USD** |
| Cost run detail totals | $0.0032 / 10.8s / 1245 tokens | Use coherent seed: **$0.237 / 14.2s / 36,420 tokens** |
| Agent graph nodes | No Validator | Product includes **Validator** (deterministic) |
| Dates | Various 2025 dates | Canonical demo: **Jan 12–16, 2027** |
| Font | Inter-like | System UI stack (Segoe UI / Palatino). Google Fonts CDN removed so offline mode does not request fonts. |
| Scenic photos | Embedded in mockups | Local gradient/illustration assets + documented stock placeholders in `frontend/public/assets/` |
