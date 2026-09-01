# Anonymous Home Flow Plan

## Goal

Build an ordered anonymous-user regression suite of approximately 50 small,
independently reportable cases. The cases follow one realistic Home-to-Article
journey, but each YAML must be able to establish its own starting state so a
failure does not invalidate every later result.

## State contract

- The app starts with cleared state.
- The user is not signed in.
- Home is identified by `id: screen_home`.
- The header Subscribe action is expected to be visible.
- Advertisements can appear for this user state.
- Restricted actions must offer sign-in or subscription instead of silently succeeding.

## First six cases

### ANON_HOME_001 — Fresh launch and anonymous Home

1. Clear state and launch the app.
2. Complete or dismiss anonymous onboarding.
3. Wait for `screen_home`.
4. Assert Home is visible.
5. Assert `SUBSCRIBE` is visible in the header.

Pass condition: Home loads without authentication and Subscribe is visible.

### ANON_HOME_002 — Pull to refresh Home

1. Establish anonymous Home.
2. Pull downward from the upper Home feed.
3. Wait for refresh/animation to finish.
4. Assert `screen_home` remains visible.
5. Assert at least one content card is available after refresh.

Pass condition: the refresh completes without blanking or leaving Home.

### ANON_HOME_003 — Home feed advertising while scrolling

1. Establish anonymous Home.
2. Scroll the Home feed upward in controlled steps.
3. Assert the validated `ADVERTISEMENT` label when an ad slot loads.
4. Record evidence for the Home sticky-ad unit when exposed by hierarchy.
5. Continue toward the lower feed and check the recommendation/Taboola region.

Important: this case needs an agreed ad-network policy. A missing network ad may
be an environment/content result rather than an application defect. Sticky-ad
and Taboola selectors must be confirmed on the current build before making them
hard assertions.

### ANON_HOME_004 — Open article and validate article controls/content

1. Establish anonymous Home.
2. Tap a verified `article_card`.
3. Dismiss a dynamic interstitial when present.
4. Assert `screen_article_detail`.
5. Check available article controls: AI Summary, Bookmark, Share, and Comments.
6. Scroll in controlled steps through the article.
7. Assert applicable advertisement and in-content Subscribe placements.
8. Scroll to post-article content.
9. Assert `Post a comment`.
10. Assert `Related Topics` and `Headlines` only for article types where those
    sections are part of the selected test data.

Pass condition: the article route, required controls, anonymous monetisation,
and applicable post-article sections are correct.

### ANON_HOME_005 — Article pager and premium/interstitial handling

1. Open a known article from anonymous Home.
2. Swipe left to the next article and verify article detail remains visible.
3. Swipe right and verify the previous article returns.
4. Repeat against controlled premium-badge test data.
5. When an interstitial ad appears, capture a screenshot.
6. Close the interstitial using the verified close control.
7. Assert article detail is restored.
8. Scroll the premium article and verify the anonymous restriction/paywall
   expected for that article type.

Pass condition: pager navigation works, interstitial recovery works, and the
premium restriction is correct for an anonymous user.

### ANON_HOME_006 — AI Summary, Bookmark, Share, and Comment restrictions

This must use a known long-form article that is confirmed to expose AI Summary.

1. Open the controlled long-form article.
2. Assert the AI Summary action is visible.
3. Tap AI Summary.
4. Assert the anonymous summary/Subscribe prompt.
5. Tap Subscribe and assert the bottom paywall sheet.
6. Close the sheet and return to the same article.
7. Tap Bookmark.
8. Assert navigation to the `Login to your account` page.
9. Capture a screenshot of that login page and end the Bookmark case without signing in.

Share and Comment checks must be separate anonymous cases so the Bookmark case
does not continue after reaching Login:

- Share case: reopen the article, tap Share, verify stable share options, capture
  evidence, close the share sheet, and end without signing in.
- Comment case: reopen the article, scroll to `Post a comment`, enter only
  non-destructive test text, assert navigation to `Login to your account`, capture
  a screenshot, and end without signing in or submitting a comment.

Correct anonymous Bookmark result: navigation to `Login to your account`, followed
by a screenshot and case completion. Authentication is outside this anonymous suite.
A bookmark-success toast belongs in a later authenticated-user flow.

## How to extend this to approximately 50 cases

- Home launch, header, navigation, refresh, loading, empty/error recovery: 8 cases.
- Home feed cards, widgets, sections, scrolling, timestamps, media: 10 cases.
- Home ad, sticky-ad, Taboola, interstitial and recovery behavior: 7 cases.
- Article opening, content, controls and post-article sections: 10 cases.
- Article pager, premium articles, paywall and Subscribe routes: 6 cases.
- AI Summary anonymous restrictions: 3 cases.
- Bookmark, Share, Comment and sign-in gates: 6 cases.

Total: 50 cases.

## Automation design rules

1. Keep one business result per YAML so reports show the exact failing behavior.
2. Reuse a common anonymous setup instead of depending on the previous case.
3. Use controlled article links/data for premium and AI Summary behavior.
4. Do not make important assertions optional.
5. Use conditional commands only for allowed dynamic interruptions, such as ads.
6. Capture screenshots at meaningful checkpoints, not after every swipe.
7. Never submit a public comment or trigger a real purchase.
8. Classify missing ad inventory separately from a broken ad container.
9. Keep authentication-entry validation separate from actual login flows. Anonymous
   cases stop after asserting and capturing the login page.

## Locator work still required before executable YAML

- Current AI Summary control selector.
- Article Bookmark and Share control selectors.
- Comment input and anonymous sign-in prompt selectors.
- Bottom paywall Subscribe and close selectors.
- Current Taboola marker.
- Sticky Home ad container/close selector.
- Premium badge selector and controlled premium article test data.
