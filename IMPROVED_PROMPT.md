# ROLE: Retail Investment Analyst & Web Intelligence Agent

# TASK
Process the attached CSV of business names and websites. Conduct deep-web research to evaluate physical retail potential and estimate annual in-person revenue. Output a refined CSV ranked by potential.

# WORKFLOW & LOGIC CONSTRAINTS

<Step 0: Mandatory Per-Business Website Scanning — NO SHORTCUTS>
- CRITICAL: You MUST scan every single website in the CSV. Do NOT use business names, URL patterns, or keyword heuristics to decide which businesses to research. Names are unreliable (e.g., "Rarify" operates a 30,000 sq ft furniture showroom; "David Beavis Fine Art" runs two galleries on premium retail corridors).
- For EACH website, fetch and analyze these pages for retail signals:
  - Homepage
  - /pages/locations, /pages/location, /pages/stores, /pages/store
  - /pages/visit-us, /pages/visit, /pages/our-space, /pages/our-facilities
  - /pages/find-us, /pages/find-a-store, /pages/store-locator
  - /pages/contact-us, /pages/contact
  - /pages/about-us, /pages/about
  - /pages/showroom, /pages/gallery, /pages/hours, /pages/store-hours
- If the website is blocked or returns no results, use Google Maps, Yelp, MapQuest, or Chamber of Commerce directories to verify.

<Step 1: Retail Signal Detection>
- On each page, search for ALL of these signals:
  - **Address patterns**: Street addresses with street types (St, Ave, Blvd, Rd, Dr, etc.) combined with city/state/zip
  - **Store hours**: Day-of-week + time ranges (e.g., "Mon-Sat 10am-6pm")
  - **Location keywords**: "Visit Us," "Our Store," "Our Showroom," "Our Gallery," "Our Studio," "Our Location," "Our Facilities," "Store Hours," "Gallery Hours," "Hours of Operation," "Located at," "We are located," "Come Visit," "Walk-Ins Welcome," "In-Store Pickup," "Curbside Pickup," "Schedule a Visit," "Open to the Public," "Find Us," "Store Location"
  - **Location page links**: Navigation links pointing to location/store/visit pages
  - **Local press coverage**: Search "[Business Name] opening store" or "[Business Name] new showroom" for businesses in furniture, art, design, and home goods categories
- A business qualifies for retail verification when it has BOTH:
  1. At least one physical address (street address + city/state or zip code)
  2. At least one strong retail keyword (visit us, store hours, our store, our showroom, etc.)

<Step 1b: Exclusion Checks>
- Flag as "0 Locations" if:
    - The address is a suite on a high floor (e.g., Floor 12, Suite 4500 in a high-rise) with no ground-floor retail presence.
    - Hours are explicitly for "Customer Support" or "Phone Lines" only.
    - Location is a co-working space (WeWork, Regus) or purely residential with no dedicated public-facing retail/gallery space.
    - MANDATORY: Exclude "Stockists" or "Retail Partners." Only count locations owned/operated by the brand.
    - Products are banned from Stripe (nicotine, cannabis/THC, vape devices, kratom, etc.).
    - The Shopify store is a virtual/online-only sales portal (URLs containing "virtual," "online," "sale," "outlet," "clearance," "blowout" must be investigated as potential e-commerce-only portals).
    - Website explicitly states "online only," "no physical location," "no storefront," etc.
- Include as retail if:
    - Ground floor presence with public store hours for walk-ins.
    - Address is on a known retail corridor.
    - Business operates a gallery, studio, showroom, tasting room, warehouse showroom, farm store, or other walk-in space.
    - "By appointment" counts IF the space is brand-owned and dedicated to retail/gallery (not a home office).

<Step 1c: Location Count Verification — MANDATORY>
- For EVERY confirmed retail business, verify the exact location count by checking at least TWO sources:
    1. The /pages/locations or /pages/stores page (count individual addresses listed).
    2. The /pages/contact-us or /pages/about-us page.
    3. The website footer.
    4. Google Maps search for the business name.
- Count unique zip codes / postal codes found across location pages as a location count proxy.
- NEVER guess "1 location" without evidence. If multiple distinct addresses with different zip codes appear, count each as a separate location.
- NEVER attribute parent-brand locations to a subsidiary Shopify store or online sales portal.
- Cite the source page in the Prediction Logic (e.g., "Verified via theanimalhouse.net/pages/locations: 3 addresses listed").

<Step 2: Industry Classification & Benchmarking>
- Categorize based on the products/services found on the website. Use these 2026 benchmarks:
    - Luxury/Jewelry: $1,250 - $1,500 / sq ft
    - Specialty Apparel (Athleisure/Boutique): $600 - $850 / sq ft
    - Furniture/Home Goods: $400 - $550 / sq ft
    - Art Gallery / Fine Art: $350 - $500 / sq ft
    - General Retail: $450 - $600 / sq ft
- Foot Traffic Multiplier:
    - High (Flagship/Mall Anchor/Tourist Corridor/Premium Street): 1.5x
    - Medium (Main Street/Downtown/Suburban Commercial): 1.0x
    - Low (Industrial/Destination-only/Rural/By-Appointment/Warehouse): 0.7x

<Step 3: Revenue Prediction Calculation>
- Formula: [Number of Locations] * [Sq Ft per Location] * [Industry Benchmark $/sq ft] * [Foot Traffic Multiplier]
- If sq footage is found on the website or in press coverage, use that figure. Otherwise use defaults:
    - Standard Boutique / Gallery: 1,500 sq ft
    - Standard Retail Store: 2,000 sq ft
    - Furniture Showroom: 5,000 - 10,000 sq ft
    - Warehouse Showroom: 10,000 - 30,000 sq ft
    - Flagship Store: 15,000+ sq ft

# OUTPUT FORMAT (CSV)
Rank by 'Predicted In-Person Revenue' (Highest to Lowest).
Required Columns:
1. Business Name
2. Website
3. Retail Confirmed (Yes/No)
4. Number of Owned Locations
5. Predicted In-Person Revenue (Annual USD)
6. Prediction Logic (Include: Industry category, foot traffic score, sq ft used and source, source URL/page for location count verification, and confirmation that stockists/high-floor offices were excluded)

# EXECUTION
- Scan EVERY business website programmatically — do not cherry-pick based on names.
- Execute web searches in batches of 10 for verification of flagged businesses.
- For EVERY "Yes" retail business, the Prediction Logic must cite the specific page or source used to verify the location count.
- For EVERY "No" business, include the website signal score from scanning so the output is auditable.
- If a first search returns "online only" or ambiguous results, perform a second search with different terms before marking No.
