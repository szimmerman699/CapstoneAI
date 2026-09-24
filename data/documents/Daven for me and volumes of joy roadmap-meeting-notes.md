# Roadmap Meeting — Dev + Daven for Me / Volumes of Joy Team
**Date:** July 20
**Recording:** [Fathom Video](https://fathom.video/share/f1m_ejX8YDHy_uxNjFP96xRFvUguxv1a) — 52 mins

**Attendees:**
- Shoshana Zimmerman — developer
- Malky Salzer — marketing/branding partner
- Blimie/Channy — Daven for Me & Volumes of Joy organization

---

## Overview

The call covered the technical roadmap for two programs run by the same organization: **Daven for Me** (Tehillim/prayer-partner matching service) and **Volumes of Joy** (personalized birthday-book program for children who lost a parent). Both are funded through Focus Camera — neither relies on donations.

---

## Daven for Me

### Current system
- Built ~14 years ago with help from GCNY, on a WordPress database/backend, replacing an older "1990s-style" system.
- Close to **5,000 participants**; Blimie estimates only ~30% are active.
- Matching is manual and color-coded by category (e.g., seeking refuah, childbearing). Blimie pairs two people in the same category using a paper-based process (two envelopes/Tehillim books), enters the match, and the system is supposed to auto-send a match-confirmation email.
- Daily/periodic reminder emails go out, but reliability isn't fully verified — Blimie only knows her own reminders arrive.
- Messaging currently runs through:
  - **Twilio** — text messages
  - **MailChimp** — email (considered clunky; Blimie has had trouble pausing it in the past)
- Domain/hosting is through Focus Camera's setup; frontend is GoDaddy-hosted — unclear if it's WordPress or something else (needs confirming).

### Pain points
- No reliable way to track who is/isn't still saying Tehillim, or who opened/received communications.
- No clean opt-out or check-in flow — everything is currently manual via email.
- Large backlog of inactive/stale participants with no cleanup process.
- No current in-house technical owner — the IT person who used to manage this left.

### Proposed direction
- **Keep WordPress as the backend/database** — no need to migrate data.
- Replace MailChimp with a more user-friendly ESP (e.g., **MailerLite** or **ActiveCampaign**) with built-in automations, easier to self-manage than WordPress-native tools.
- Consider **Make/Zapier**-style automation to connect Twilio/WhatsApp messaging, since Twilio alone doesn't have a full automation interface.
- Add **WhatsApp** as a third channel alongside email and text — participants choose their preferred channel.
- Rebuild the **frontend** in **React** (converted from Figma designs) rather than building natively inside WordPress — faster to build/iterate than native WordPress blocks. WordPress stays as the backend only.
- Manual match-pairing stays manual — the organization is fine doing this themselves since it needs human judgment (missing phone numbers/emails, data-quality issues).

### Planned automations
- Recurring **check-in prompts** (e.g., every 30 days) asking participants if they're still saying Tehillim, with an opt-out button built into the reminder email.
- **Database cleanup campaign**: participants who signed up before ~June 2025 get an email/text asking them to reconfirm; only confirmed responders stay active. Anyone from June 2025 onward stays active automatically.
- Deliver a Tehillim link/booklet at reminder time; many participants are older and may not have smartphones, so text/email must stay available, not just app/link-based.
- Participants still waiting for a match should get an automated "still waiting for a suitable partner" notice instead of the regular saying-reminder, until they're matched.
- Opt-out button included directly on the daily/periodic reminder emails.

---

## Volumes of Joy

### Overview
- Personalized birthday gift-book program for children who lost a parent (~1,500 children in the database).
- Each child gets a book matched to age/gender/language (English/Yiddish) plus a birthday card (currently ~4 core card designs split by age/language/gender).
- **Frontend only** requested for this project — there is no existing backend; it will be built from scratch.
- Website will be **private/unlisted**, not publicly searchable — reached only via direct links shared by word of mouth, organizations, or the org's own outreach. Sign-up form should collect enough info (phone number, what was lost/when) for the org to follow up directly, especially for sensitive cases.

### Current (manual) process
- Uses a static **Excel sheet** of ~1,500 names.
- Each month, someone manually filters the sheet for children with birthdays that month and tags age group.
- Orders are entered into **Seller Cloud** (Focus Camera's system) using a template/format provided by IT, including generating a username and order number per kid; Seller Cloud creates the shipping labels.
- Book selection is manual and intentional — a person still matches/chooses the book per child; only the label/order creation is a candidate for automation.
- Pain point with Seller Cloud: the warehouse chases the team by email when orders sit unfulfilled/unshipped.

### Pain points
- No birthday-lookup automation — everything is manual spreadsheet filtering, done monthly (could ideally run more than once a month).
- No backend/database at all currently for this project.
- Dependence on Seller Cloud for order/label creation is a pain point.
- Book catalog needs regular pruning as old titles are replaced with new ones — currently a "sea of books."

### Proposed direction
- Build a **database** (CRM- or Airtable-style) to replace the Excel sheet, storing:
  - Child records (birthday, age, gender, language, address, etc.)
  - Book catalog table, with each title tagged to an age range/gender/language, so the system can **suggest** (not auto-select) an appropriate book per child.
- Automate **monthly birthday pulls** (e.g., 1st–15th of each month, possibly more frequent) instead of manual filtering.
- Automatically generate **order numbers/shipping labels** once a book is confirmed — possibly replacing or reducing dependence on Seller Cloud.
- **Branding/design refresh**: Malky to build a cohesive brand identity based on the existing "balloon" visual style — logo, streamlined birthday cards (~4-6 core designs across Yiddish/English, boy/girl), sign-up form, and landing page.

---

## Roadmap phases (as presented by Malky)

1. **Phase 1 — Technical Roadmap** *(this meeting)*
2. **Phase 2 — Strategy & Mission Messaging**
   - Needed for Daven for Me (explaining the program to prospective participants).
   - Not needed for Volumes of Joy — Blimie considers it self-explanatory (books + birthday gifts for kids who lost a parent), and the program isn't donation-funded.
3. **Phase 3 — Design & Copy**
   - Volumes of Joy: logo, branding, birthday card designs, sign-up form, landing page.
   - Daven for Me: frontend facelift only (backend stays WordPress).
   - Build (site + copy + design) and the automations/flows happen together, not sequentially.
4. **Migration, QA & Launch**
   - Data cleanup, full process testing, list migration/testing.
   - Target launch discussed as potentially before Rosh Hashanah, though flagged as tight — more realistically after Sukkot depending on timelines.
5. **Growth Stage**
   - Expanding features and growing the participant database further — to be discussed later.

### Priority
- Blimie considers both projects roughly equal priority/importance, but felt Daven for Me carries more responsibility given its scale.
- **Daven for Me** development was chosen to start first since it already has a working system to build on; **Volumes of Joy** design/branding work can proceed in parallel since it starts from scratch (frontend + design don't need to wait on backend decisions).

---

## Action items

- [ ] **Email IT (Focus Camera IT manager)** — confirm Focus Camera ESP capabilities/access.
- [ ] **Email Blimie/Channy** — Daven for Me tech roadmap + ESP options; then send pricing/scope.
- [ ] **Email Blimie/Channy** — confirm Daven for Me frontend tech stack (WordPress vs. React, GoDaddy-hosted).
- [ ] **Email Shoshana** — Volumes of Joy book inventory + Seller Cloud order-import template.
- [ ] **Email Blimie/Channy** — cleaned-up roadmap + pricing/scope, then schedule a review call.

---

## Open questions

- Is the current Daven for Me frontend actually built on WordPress, or something else (GoDaddy-hosted)?
- Final scope for WhatsApp automation — likely a separate automation track from email/SMS since each channel needs its own automation set.
- Exact cutoff logic for the Daven for Me participant-database cleanup (currently proposed: June 2025 as the active/inactive line).
- Realistic launch date — Rosh Hashanah target flagged as likely too tight; post-Sukkot considered more realistic.
- Alternative to Seller Cloud for Volumes of Joy order/label creation — not yet decided.
