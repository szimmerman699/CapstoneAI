# Ad Infinitum / Calendar Warehouse — Website Project Roadmap

*Source: kickoff call with Chaim Jaroslawicz (Ad Infinitum), April 24*

## Company Background

Ad Infinitum is a promotional products company (imprinted pens, mugs, towels, calendars, umbrellas, etc.). They don't inventory anything — a client orders, Ad Infinitum places the order with a manufacturer, and it ships direct to the client. The core business runs on referrals and personal/direct contact (LinkedIn, word of mouth), not web search — they deliberately avoid looking like a generic "everything imprinted" site.

**Calendar Warehouse** is the one exception: a long-running vertical site (~20 years old) that exists specifically to capture organic search traffic for custom-imprinted calendars. They used to spend real money on Google Ads for it but haven't in years. There's also a newer Israel-focused arm selling promotional products to Israeli high-tech companies exhibiting abroad.

## Current State

- Built on WordPress + Elementor, using two third-party plugins (tiered pricing + product add-ons) that, combined, get checkout to roughly **80% functional**.
- The plugin vendors are responsive (based in Ukraine/Eastern Europe) and have fixed at least one bug already (a cart-quantity carryover issue).
- Design/layout is basically fine and doesn't need rework — the gap is in the underlying functionality ("programming," in Chaim's words), not visual design.
- Chaim wants someone who can go deep on debugging and customizing existing plugins — not just someone who's good at initial plugin setup.

## Phased Rollout

### Phase 1 — Bidmaster Calendar site (top priority, already overdue)
A narrow, 3-product site (Bidmaster Wall, Bidmaster Desk, Small Bidmaster) meant to prove out the full order → checkout → fulfillment flow before scaling up.
- Originally meant to launch in time to catch late-2024/2025-season calendar orders; still not live as of this call.
- Order flow: select calendar → choose imprint color(s) (base imprint is 1 color; additional colors cost more) → tiered/quantity pricing with a 150-unit minimum (special case: ordering 2 different designs allows 75 units each) and custom order increments (e.g., +25 units) → upload artwork (or send by email instead) → checkout with credit card.

### Phase 2 — Full Calendar Warehouse relaunch
Same engine and flow as Phase 1, scaled from 3 products to ~7 categories / roughly 1,000–1,200 calendar SKUs (many are the same calendar in different colors/photos, i.e., identical pricing/functionality).
- Needs a fast/bulk way to load ~1,000+ products instead of entering them one at a time.
- Some individual calendars will need unique one-off logic layered on top of the shared flow.

### Phase 3 — Additional vertical sites
Same underlying engine, different product line. An "umbrella" vertical site is next (domain already registered, same category → imprint-colors → tiered-pricing → upload flow). Other verticals (e.g., a "cooler" site) are planned but on hold — Chaim is explicit that nothing beyond Phase 1–2 starts until the core flow is proven out on one site. Their Elementor/plugin licenses were already bought at a multi-site tier in anticipation of this.

## Key Functional Issues to Fix

1. **Checkout totals don't calculate correctly.** Example from the call: a $0.33/unit add-on option, base product price $11.26 — the displayed total comes out to $10.93 instead of the correct ~$44.59 (100 units × $11.26 + add-on). Need to determine whether this is fixable in Elementor, needs plugin configuration, or is a plugin limitation.
2. **Stray "$0" labels** shown next to imprint-color options that shouldn't display a price at all — needs to be hidden.
3. **Duplicated price tables.** Right now every product has its own copy of what is often an identical price table (e.g., the same calendar in 20 colors = 20 duplicate tables). Their old legacy system (from ~15 years ago) supported ~15 shared/central price tables that individual products could simply point to. Need to determine if the current plugin stack supports shared pricing, so updates only have to happen once.
4. **Freight/shipping estimate at checkout.** They don't want real UPS/FedEx shipping integration — they never ship anything themselves, it all goes factory-direct — but they do need a built-in freight *estimate* at checkout so they're not stuck absorbing unexpected shipping costs. A conservative/rough number is fine; doesn't need to be exact.
5. **Annual price change (July 1).** Calendar pricing changes every year on July 1 and needs to switch automatically, ideally with an "order now before the price increases" prompt beforehand.
6. **File upload size limits.** Vector logo files are small (under 1MB typically), but full-color print-ready artwork (21"×6" @ 300 DPI) can run to hundreds of MB. Need to check/raise WordPress upload limits, or keep directing large-file customers to send artwork by email instead of uploading.
7. **Cart-quantity carryover bug** — already caught and fixed by the plugin vendor (previously, re-adding a calendar to the cart added to the existing quantity instead of prompting fresh), but worth re-verifying it's actually resolved.

## Order Flow (confirmed as-is, no redesign needed)

1. Customer configures the product (calendar type, imprint colors, quantity) and pays by credit card up front — this is what "commits" the order.
2. **Manual review is required and non-negotiable**: staff verify the submitted artwork matches what was priced (e.g., a customer paid for a 1-color imprint but submitted 5-color art — needs re-pricing before production).
3. Staff send the customer a PDF proof of the imprint; customer must sign off before anything goes to production.
4. Follow-up communication can happen by email or phone — it doesn't all need to be online, and Chaim is fine with that (values the "touch" of a phone call for edge cases).
5. Optional: scheduled shipping — customer can order early (e.g., June) to lock in pricing but request shipment on a later release date (Sept–Dec), rather than receiving stock immediately. Not needed for Phase 1 launch but flagged as a "has to come in eventually" feature.

## Open / Unresolved Items (explicitly flagged as not yet decided)

- Whether/how a completed website order should create a matching record in their Zoho CRM. Currently nothing is connected — the demo site takes no live orders, and even their older semi-live setup generates an order number in the web system that doesn't match the order number generated by the accounting system.
- Whether integration should be real-time or a batch transfer of orders at the end of the day (Chaim's tentative preference is that the systems can stay independent, at least initially).
- Credit card processing is already wired into the site, but sales tax calculation and full reconciliation with accounting is unconfirmed/untested.

## Commercial Terms Discussed

- Shoshana's rate: **$150/hour**, or a **fixed project estimate** for defined chunks of work.
- A paid exploratory/discovery pass to properly scope the project: **~$250**, after which Shoshana estimated most individual fixes/tasks would fall in the **1–5 hour range** each.
- Chaim's own rough estimate (unprompted): the whole scope discussed might be **under 40 hours** total, though he acknowledged that's likely optimistic given the scope.
- Ongoing maintenance proposal (from Shoshana): **$200/month per site**, or **$500/month for all three** (Bidmaster, Calendar Warehouse, future umbrella site) — covers monitoring plugin/version updates, backups, and up to ~30 minutes of fixes per issue; anything beyond that billed separately. Options discussed: auto-updates with monitoring, or updates first tested on a staging site.
- Shoshana offered a discount to **$125/hour** if Chaim could confirm a decision by the following Sunday/Monday.
- Chaim's reaction: called both the hourly rate and project-style pricing "well above" what he was expecting for an Israel-based developer, but did not name a counter-number or walk away — said he needed to check with his business partner Anne on budget before committing either way.

## Status as of Call End

No budget, scope, or engagement type has been agreed. Chaim's explicit next step: discuss budget with Anne and get back to Shoshana with a yes/no (and, if yes, which pricing structure) — he committed to giving her a clear answer either way rather than leaving her hanging.
