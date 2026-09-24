# Clifton Community Site — Design & Feature Review Roadmap

*Source: 30-minute meeting between Yonah Lazar, Yehuda Davis, and Shoshana Zimmerman*

## Overview

Review call for a community portal site (working name references "Archila/Arqihila" as the site's logo/brand mark, tagline "Bringing [the community] together"). The site aggregates local Jewish community info — minyan times, business listings, jobs, classifieds, community events, Torah content — and doubles as an ad/announcement platform for the community. Yehuda mentioned the current business model is largely built around sending out community announcements/email blasts, so that functionality is central and must not get lost in the redesign. Yehuda had to drop off partway through for another meeting; the rest of the design discussion continued with Yonah and Shoshana.

## Header / Top-of-Page Layout Decisions

- **Problem flagged:** the logo currently sits right above a blue bar and gets visually lost/squished against the white background as you scroll.
- **Fix agreed:**
  - Move the top bar down so there's a thin, dark-blue line above the white section (so the page doesn't look like it "starts with white").
  - Make the logo bar itself a **gradient blue** (lighter → darker), rather than one flat blue, so it pops more against the rest of the page's blue elements. General principle raised: too much single-shade blue causes everything to blend together — contrasting/complementary shades of blue make elements stand out.
  - Logo should be made bigger; the tagline **"Bringing [Community] Together"** should be added/expanded to help fill the whitespace next to the logo.
  - The top 3 elements (logo bar, gradient bar, and the menu below it) should be **locked/sticky** while scrolling — always visible.
  - Consider a subtle shadow/texture behind the white area so it "pops" off the screen a bit more (Shoshana to experiment).
  - Optional/nice-to-have: a text-box/border treatment around the logo and other header elements to make them feel more distinct ("pop out more").

## Second Bar — Repurposed as an Ad/Info Bar

- The existing "Khaverim Hatzalah" phone-number bar is being removed as a static feature — Yehuda flagged it as a likely source of "politics" (other organizations like JFS will want their numbers listed too if some numbers are shown).
- Decision: turn that space into a **flashing/scrolling ad bar** instead (similar to what the Baltimore Jewish Life site does) — sponsors, community announcements, event promos, etc. can run through it.
- If there's no paid ad running, the bar can show useful filler content instead — e.g. the current Hebrew date, or the current week's Torah portion (Parsha). Yehuda offered to build this via a small custom endpoint (he's comfortable spinning something up on Vercel with Python) if no existing lookup/API is easy to find; Shoshana will check for an existing solution first.
- No static organization phone numbers stay in this bar going forward.

## Main Navigation Menu

Goal: shorten/simplify the menu so it doesn't overflow and get pushed to a second line on smaller screens.
- **Remove "Home"** — redundant since the logo already serves as the home link.
- **Rename "Business Listings" → "Businesses"** (shorter).
- **Rename "Community Events" → "Events"** (shorter, same meaning).
- **Group related items under dropdowns** to reduce top-level items:
  - A combined dropdown for **Minyanim, Shiurim, Devar Torah** (exact label still to be finalized — something like "Minyanim & Shiurim").
  - A combined dropdown for **Businesses, Buy/Sell, Real Estate** (local business/classifieds group), possibly including Jobs.
- On mobile, the menu already correctly collapses into a hamburger menu — confirmed working. On a narrow desktop/tablet width, items currently overflow to a second line; Yehuda suggested applying the same hamburger-collapse behavior there too, once the item count is reduced by the above changes.

## Listings Layout (Business/Job/Classified pages)

- Two competing layout options for listing cards were shown: (1) an image + info side-by-side (asymmetric) layout, or (2) a centered rectangle without an image.
- **Decision: go with the image-based/asymmetric layout** (like the one shown for Jobs) — Yonah preferred it and wants the same style carried across other listing pages (business listings, etc.) for visual consistency.
- If a listing has no submitted image, it falls back to a plain gray placeholder box with just the text details — approved.
- Ad space sits alongside listings, but **must stay visually smaller than the actual content** (roughly a 2:1 ratio of content to ad) so the page doesn't read as "just an ad page."
- **Search vs. filters/categories:** Yehuda pushed back on category filters, since this is user-submitted content and users won't reliably tag things — a plain keyword search bar is more realistic than relying on filters/categories. Shoshana to fix/verify how the current search functionality works.
- Listings expire after ~30 days and must be resubmitted — noted as a known limitation while testing with sample data.
- The Gemachs (free-loan/lending listings) page layout, using a 3-bar/category-grouped design, was shown and **approved as-is** — Yonah confirmed this is exactly the direction he wants, and there are more categories to add beyond the three shown in the demo.
- Styling idea floated (not firmly decided): a monospace/terminal, "black-and-white Python" aesthetic for at least part of the listings UI — Yehuda would personally like this; treated as a nice-to-have to play with fonts/styling later, not a blocker.

## Minyanim (Prayer Times) Page

This was the most substantively debated feature.
- **Two display concepts discussed:**
  1. A rotating "next minyan" widget (like Baltimore's site) that shows the very next prayer time coming up.
  2. A plain sorted list of all minyan times across shuls (not grouped by shul), sorted by clock time.
- **Concern raised about option 1:** a "next minyan" countdown could mislead someone who's a minute late for the listed time (e.g., a 5:01 arrival missing the "5:00" minyan that's shown as next) — a buffer window would need to be considered.
- **Decision:** default toward a **simple list of times sorted chronologically across all shuls**, rather than a per-shul breakdown — Yehuda's reasoning: nobody wants to hunt through 30 individual shul listings; the value is seeing *all* nearby minyan options together. A per-shul view can exist as a secondary/optional view later, but is not the primary design.
- **Data sourcing is unresolved and flagged as the harder problem:**
  - Ideal long-term solution: each shul creates its own account and submits/maintains its own minyan times directly (Yehuda's original intended design).
  - Realistic fallback: much of the data will have to be manually collected/maintained by a person (tentatively "Moshe's job," per Yonah) by checking shul websites periodically — Yonah suggested checking ~3x/year, especially around times like before Pesach, when schedules commonly change.
  - Precedent problem noted: a similar existing directory (referenced as "Arshul") is unreliable because it's poorly maintained and even people nominally listed as maintainers can't get login access to update it.
  - Conclusion: allow both self-submission (ideal) and manual/admin-maintained entries (realistic fallback) since some shuls won't self-maintain.

## Local Kashrus Info / Devar Torah Sections

- Originally considered routing local kashrus alerts/updates through the (unnamed) local kosher supervision organization, but that org has been unresponsive/uncertain, so this is on hold.
- **New direction:** rather than a local org, look for individual respected community rabbis (names discussed: Rabbi Gutterman, Rabbi Jakobowitz, possibly others) who would be willing to post community-relevant halachic content directly (similar to how sites like Star-K post practical/topical content, e.g. on washing vegetables) — this avoids depending on a single organizational gatekeeper and sidesteps the "politics" of only one group being featured.
- Kashrus info and Devar Torah content are to be displayed as **regular listings**, same format/style as everything else on the site.
- Devar Torah section specifically still needs outreach — Yonah to talk to "Zecharya" about contributing/curating; unresolved as of the call. Possibility of a rotation among multiple contributing rabbis was floated, not finalized.
- Both of these sections were temporarily **hidden/deprioritized** for the initial launch — Yehuda's suggestion, which Yonah agreed to — since the content pipeline for them isn't settled yet. Priority for launch should be the fixed, reliable content (Minyanim, listings) first; things requiring ongoing content sourcing (events, kashrus, Devar Torah) come after.

## Listings: Free vs. Paid

- **Gemach (free community lending) listings are and remain free** — confirmed by Yehuda.
- **Business listings are intended to be paid**, structured as an **annual subscription** (ballpark figure discussed: ~$50/year), with an auto-renew option under consideration.
- The existing "add a listing" flow currently shows fixed expiration options (90 / 180 / 360 days) that need to be replaced/reconciled with the annual-subscription pricing model.
- **Unresolved / flagged as its own follow-up discussion:** how listing pricing interacts with the site's existing announcement/email-blast product — they're currently two separate systems/products (a business listing vs. a paid email announcement) and need a coherent combined structure (what's included, how long, at what price tiers). Both Yonah and Yehuda agreed this needs dedicated discussion time, not something to resolve on this call.
- Whatever pricing/duration options exist should be **editable from the admin panel** per listing type, since Yehuda expects pricing to keep changing as they learn what works ("going to take a year for everything to settle").

## Announcements (Email Blast) Feature

- Currently the core of the existing business model — sending paid announcements/email blasts to the community — and must remain easy to find/use once the new site launches, not get buried.
- Currently only reachable indirectly via the "Add a Listing" flow; not its own clearly visible option.
- **Decision:** add a separate, clearly labeled "Add Announcement" button/entry point distinct from "Add Listing," so it doesn't get lost in the redesign.
- Open technical question (unresolved): how to structure the relationship between a listing and an announcement/email blast when they're tied to the same submission — flagged by Yehuda as needing real design thought, not a quick fix.

## Sponsorships (mentioned, not yet designed)

- Idea floated: a "this week's [Devar Torah / local content] is sponsored by [name]" model, where a sponsor's name is attached to a specific piece of content and there's a printable/shareable version.
- Yonah wants to discuss this further with Yehuda separately before bringing requirements to Shoshana — not yet in scope for building.

## Other Notes

- Payment page: Shoshana showed the listing-payment flow; described as a standard payment page — no changes discussed/requested.
- Account type: Yehuda raised whether an account should remember "who an announcement/listing is submitted on behalf of" (e.g., auto-fill or persist organization identity across submissions) — raised as a nice-to-have, not resolved, no action taken on this call.

## Next Steps

- A follow-up meeting was tentatively scheduled for **the following Thursday** — all three participants confirmed the time works.
