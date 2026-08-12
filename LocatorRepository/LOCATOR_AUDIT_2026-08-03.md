# Locator Audit

Date: 3 August 2026

## Current inventory

- Validated records: 29
- Extracted candidates: 151
- Validated screen labels: 11
- Candidate screen labels: none; all 151 candidates are currently unassigned

## Validated navigation coverage

- Home: `nav_home`, `screen_home`
- Trending: `nav_trending`, `screen_trending`
- Premium: `nav_premium`, `screen_premium`
- Ebooks: `nav_ebooks`, `screen_ebooks`
- Games: `nav_games`, `screen_games`
- Account: `nav_account`, `screen_user_menu`, `cta_login`, `cta_menu_close`
- Hamburger: `nav_menu`, `screen_hamburger`, `cta_drawer_close`, `cta_search`
- Section entry text: Videos, Photos, India, World, Editorial, Opinion, Sports, Sport and Business
- Shared section destination: `screen_section`

## Repository issue

`screen_section` is duplicated for `sport_page` and `business_page`. It should become one canonical shared locator with page aliases or navigation assertions providing page identity.

## Candidate quality issue

All smart candidates are unassigned. They cannot be safely promoted until each record stores:

- Screen name
- App build
- Device
- Source hierarchy
- Locator type and value
- Validation action
- Validation result and timestamp

## Page-by-page device audit order

1. Home shell and bottom navigation
2. Hamburger and Account
3. Videos
4. Photos
5. India and World
6. Editorial and Opinion
7. Sports and Business
8. Article detail common controls

## Required checks per page

- Destination screen identifier
- Page title or stable identity assertion
- Primary tab/subtab controls
- Article-card identifier
- Search/filter controls when present
- Scroll container
- Shared article actions: Back, Share, Bookmark, Comment and Text size
- Overlay close controls
- Screenshot checkpoint name

## Promotion rule

Use resource ID first, accessibility label second and stable text third. Coordinates remain scenario-level fallbacks and are not promoted as reusable validated locators.

Each candidate must pass `assertVisible`; interactive controls must also pass `tapOn` and destination verification before promotion.

