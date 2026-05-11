# Aegis — Crypto Wallet Security Monitor

## 1. Overview

**Aegis** is a read-only iOS app that continuously monitors crypto wallets for security risks: dangerous token approvals, exposure to known drainer contracts, address-poisoning attacks, and malicious tokens. Users add wallet addresses (no keys, no custody), get push alerts when risk is detected, and tap through to revoke.cash or their own wallet to fix issues.

**Problem:** $494M was stolen from 332K crypto users via wallet drainers in 2024. All existing security tools (Wallet Guard — sunset March 2025, Pocket Universe, Revoke.cash, Web3 Antivirus) are browser extensions or web apps. No native iOS app owns this niche.

**Target user:** Multi-wallet HODLers with $50K–$500K in crypto across 2–6 EVM wallets, EN/ES/AR speakers, iPhone users worried about getting drained.

**Value prop:** *“Watch all your wallets. Get a push alert the moment any of them is exposed to a drainer, risky approval, or poisoning attack. One tap to fix.”*

-----

## 2. Scope

### In scope (v1)

1. **Multi-wallet watchlist** — unlimited EVM addresses (paste, QR scan, ENS), no keys ever
1. **Approval scanner** — ERC-20/721/1155 allowances across 6 EVM chains, sorted by risk + USD exposure, deep-link to revoke.cash for fixing
1. **Risk feed + push alerts** — daily background scan + push when: new approval to flagged contract, address-poisoning tx detected, held token flips to honeypot/blacklist behavior, drainer-adjacent outgoing tx
1. **Wallet Health Score (0–100)** — single number per wallet via simple weighted formula, with “Top 3 things to fix” action list
1. **Token Risk Scanner** — paste contract address → GoPlus-powered one-screen report (honeypot, mintable, tax %, owner privileges, LP locked, top holder concentration)

### Chains supported (v1)

- Ethereum
- Base
- Arbitrum
- Optimism
- Polygon
- BNB Chain

### Out of scope (v1)

- ❌ In-app revoke / WalletConnect signing (App Store risk, +weeks of work)
- ❌ Solana / Bitcoin / non-EVM (add later if requested)
- ❌ Tax / cost basis / portfolio P&L (saturated market)
- ❌ NFT galleries / marketplaces
- ❌ Staking / yield / swaps
- ❌ Social features, in-app sharing, comments
- ❌ Browser extension companion

-----

## 3. Pricing & Monetization

**Tiers:**

- **Free:** 1 wallet, manual refresh, hourly background scans, see approvals (read-only), no push alerts, no health score history
- **Aegis Pro:**
  - **$4.99 / month**
  - **$39.99 / year** (33% off) — primary annual option with 7-day free trial

**Pro unlocks:** unlimited wallets, 5-minute real-time scans, push alerts, full health score + history, weekly digest, widgets, biometric lock, iCloud sync, unlimited token scans

**Paywall strategy:** Soft paywall. Free user adds 1 wallet, sees real risks → emotional trigger → upgrade. Annual plan defaults to 7-day trial.

**SDK:** RevenueCat (free up to $2.5K MRR, then 1% of revenue).

-----

## 4. Wallet Health Score (Algorithm)

Start at 100, subtract:

- **−10** per unlimited (uint256.max) ERC-20 approval still active
- **−20** per approval to a contract flagged by GoPlus malicious-address API
- **−30** if wallet has any exposure to a known drainer contract (ChainPatrol / Scam Sniffer blocklists)
- **−15** per approval older than 365 days
- **−5** per honeypot / blacklisted token currently held
- **−10** if wallet has received an address-poisoning transaction in last 30 days

Score floor = 0. Display with color: 80–100 green, 50–79 yellow, 0–49 red.

“Top 3 things to fix” = the 3 deductions with highest `weight × USD exposure`.

-----

## 5. Technical Architecture

### iOS Client

|Layer        |Choice                                                     |
|-------------|-----------------------------------------------------------|
|Language / UI|Swift 5.10+ / SwiftUI                                      |
|Min iOS      |iOS 17.0                                                   |
|Architecture |MVVM + Repository pattern                                  |
|Persistence  |SwiftData (local) + CloudKit private DB (cross-device sync)|
|Auth         |Anonymous device UUID, no accounts                         |
|Networking   |URLSession + async/await + AsyncStream                     |
|Paywall      |RevenueCat SDK                                             |
|Charts       |Swift Charts (health score over time)                      |
|Analytics    |TelemetryDeck (privacy-respecting, no ATT prompt needed)   |
|Push         |APNs via Firebase Cloud Messaging                          |
|Localization |English, Spanish, Arabic (incl. RTL layout testing)        |

### Backend (Python on existing DigitalOcean VPS)

|Component      |Choice                                      |
|---------------|--------------------------------------------|
|Framework      |FastAPI (async)                             |
|Database       |SQLite + WAL mode + SQLAlchemy ORM          |
|Scheduler      |APScheduler (in-process background jobs)    |
|Push           |Firebase Admin SDK → APNs                   |
|Process manager|systemd                                     |
|Reverse proxy  |Caddy (auto-HTTPS) or nginx                 |
|Deployment     |Push-to-deploy via git pull + systemd reload|

**Backend responsibilities (kept minimal):**

- Accept device registration (device_id + APNs/FCM token + watched addresses + tier)
- Scan watched wallets on schedule (5 min for paid devices, 1 hr for free)
- Compare current state vs last-scan state in SQLite
- Send push via FCM when risk is detected
- That’s it. **No user data lives on the backend beyond watched addresses + push tokens.**

### Data sources (all free tiers at launch)

- **GoPlus Security API** — token risk, approval risk, malicious address detection, phishing detection (free 30 req/min)
- **Alchemy** — multichain RPC, eth_getLogs, token allowances (free 12M req/month)
- **Etherscan / Basescan / Arbiscan / Polygonscan / BSCscan / Optimistic Etherscan** — approval history (free 5 req/sec per chain)
- **CoinGecko** — token USD prices for exposure calculation (free 30 req/min)
- **Scam Sniffer + ChainPatrol** — phishing/drainer blocklist public feeds

**API cost path:** $0/mo at launch → ~$200–500/mo around 10K MAU (paid by subscribers by then).

### Scan frequency

- **Pro users:** every 5 minutes per wallet
- **Free users:** every 60 minutes per wallet

-----

## 6. User Flows

### Onboarding (first launch)

1. Splash → 2-screen value prop carousel
1. Paste / scan / type wallet address (or tap “Try with sample wallet”)
1. **Instant scan in <10s** → show health score animating up, list of risks
1. Soft paywall sheet: “Watch unlimited wallets and get real-time alerts” → 7-day trial CTA + monthly option
1. If dismissed → user has free tier with 1 wallet watched

### Daily use

- Push alert arrives → tap opens app to the specific risk
- User reviews risk detail → taps “Fix” → opens Safari to revoke.cash for that address/contract
- User completes revoke in their own wallet → returns to Aegis → next scan picks up the cleaned state → health score rises

### Settings

- Manage wallets (add/remove/rename)
- Subscription management (RevenueCat customer info link)
- Language toggle
- Notification preferences (which risk types trigger push)
- Biometric lock toggle
- Privacy policy + ToS

-----

## 7. App Store Compliance

**Critical:** Apple guideline **3.1.5(b)** requires *organization* enrollment for crypto wallet-adjacent apps. User has chosen **individual developer account** — this is a known risk (see §10).

**Notes for App Review** must explicitly state:

- “Aegis is a *read-only monitoring tool*. It does not store, transmit, or facilitate transactions in any cryptocurrency.”
- “Users enter only public wallet addresses. No private keys, seed phrases, or signing capability exist in the app.”
- “Any state-changing action (revoking an approval) deep-links to Safari → revoke.cash, where the user signs the transaction in their own wallet outside of Aegis.”

**Guidelines explicitly addressed:**

- **3.1.1 (IAP):** All paid features via StoreKit 2 only. No alternative payment, no NFT/crypto unlock.
- **3.1.5(b)(iii) Exchanges:** N/A — no exchange.
- **3.1.5(b)(iv) ICOs:** N/A.
- **3.1.5(b)(v) Token rewards:** N/A.
- **2.4.2 Mining:** N/A — only standard Background App Refresh.
- **4.1(c) Anti-clone (Nov 2025):** Original branding “Aegis”; no reference to competitor names in title/icon.
- **5.1.1 Privacy:** No tracking, no user accounts, App Privacy nutrition labels = “No data collected.”

**Demo video for reviewers** showing: read-only architecture, no key entry, revoke flow opening Safari externally.

-----

## 8. Build Plan (8 weeks solo)

|Week|Backend deliverable                                                                      |iOS deliverable                                                                    |
|----|-----------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------|
|1   |FastAPI skeleton, SQLite schema, Etherscan + Alchemy clients, single-wallet scan job     |Swift/SwiftUI ramp-up; “Hello, Etherscan” prototype fetching one wallet’s approvals|
|2   |Multi-chain scan pipeline (6 EVM chains), GoPlus integration, malicious address detection|SwiftData models, add/remove wallet flows, ENS resolution, paste/QR/clipboard input|
|3   |Health score algorithm, state-diff logic, scheduler across all wallets                   |Approval list UI, risk detail screens, deep-link to revoke.cash                    |
|4   |FCM push integration, device registration endpoint, push templates                       |Push notification handling, notification deep-links, health score chart            |
|5   |Rate limiting, error handling, monitoring, free vs pro scan-frequency tiers              |RevenueCat paywall, IAP, trial flow, soft-paywall UX                               |
|6   |Production deploy on DO VPS, Caddy + systemd, logging                                    |Token Risk Scanner screen, settings, biometric lock, widgets                       |
|7   |Load testing, bug fixes, monitoring dashboard                                            |Spanish + Arabic localization (incl. RTL testing), App Store assets, landing page  |
|8   |—                                                                                        |TestFlight beta (50 users), bug fixes, App Store submission, Notes-for-Review video|

**Pre-week-1 (start day 1, parallel to coding):**

- Reserve App Store name “Aegis Wallet”
- Get Apple Developer account (individual — see risk in §10)
- Build email-capture landing page, post to crypto Twitter, collect 200 emails
- Apply for GoPlus, Alchemy, Etherscan API keys
- Set up Firebase project for FCM

-----

## 9. Go-to-Market

**Primary channel: ASO**

- Title: *Aegis — Wallet Security Scanner*
- Subtitle: *Approval Monitor & Drainer Alerts*
- Keywords: wallet security, crypto safety, token approval, drainer protection, revoke, web3 security, defi safety, scam protection, metamask security, crypto antivirus
- 5 screenshots: Health Score, Approval list with red flags, Drainer push alert, Token risk report, Multi-chain watchlist
- 30-second preview video: wallet health 23 → 91 after revoking 7 approvals

**Content + community:**

- Weekly “Drainer Report” newsletter / X thread cataloging fresh drainer contracts
- Reddit: r/CryptoCurrency, r/ethfinance, r/defi (case studies, not promo)
- Telegram: Spanish-speaking crypto channels (LATAM underserved by Western incumbents)
- Arabic-speaking crypto Telegrams + Twitter (UAE has 30.4% crypto penetration — highest globally)
- Indie Hackers + Product Hunt launch

**PR hook:** Cite Scam Sniffer + GoPlus + ChainPatrol data in-app; reach out as a “mobile consumer partner” — they cite back.

**Influencer:** $200–500 sponsorships with mid-tier crypto educators (“I scanned my own wallet and found 17 risky approvals” thread).

-----

## 10. Risks & Mitigations

|Risk                                                                                   |Likelihood|Impact                 |Mitigation                                                                                                                                                                                                         |
|---------------------------------------------------------------------------------------|----------|-----------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
|**Apple rejects under 3.1.5(b)** due to individual (not organization) developer account|**High**  |Medium — 2–6 week delay|Submit with thorough Notes-for-Review + demo video emphasizing read-only architecture. If rejected, convert to organization via Stripe Atlas Delaware LLC (~$500, ~2 weeks). Budget 2 extra weeks for review cycle.|
|Wallet drainer landscape changes (2025 H2 losses dropped 83% YoY)                      |Medium    |Medium                 |Pivot marketing from fear-of-drainer to general wallet hygiene + approval cleanup. The underlying need (stale approvals) is permanent.                                                                             |
|Free API tier limits hit before MRR covers paid tiers                                  |Medium    |Low                    |Monitor at 5K MAU; upgrade GoPlus + Alchemy first (highest impact). Paid tiers ~$200–500/mo, easily covered by ~50 paid users at $39.99/yr.                                                                        |
|Competitor (Wallet Guard / Pocket Universe) ships native iOS app                       |Medium    |High                   |Differentiation: (a) multilingual EN/ES/AR, (b) multi-wallet vs single-wallet focus, (c) widgets + Apple Watch focus. Ship updates faster than incumbents.                                                         |
|Push notification delays                                                               |Low       |Medium                 |FCM + APNs is industry-standard; backend polls every 5 min; alert latency under 6 min p95.                                                                                                                         |
|RTL layout bugs in Arabic build                                                        |Medium    |Low                    |Test every screen with `.environment(\.layoutDirection, .rightToLeft)` in week 7. Apple’s RTL support is mature in SwiftUI.                                                                                        |
|Low conversion (<3% trial→paid by month 3)                                             |Medium    |High                   |Tighten paywall: gate Wallet Health Score behind paid; surface “exposure value in USD” prominently. Run RevenueCat paywall A/B tests.                                                                              |
|Low MAU (<15K by month 6)                                                              |Medium    |High                   |Invest $3–5K in Apple Search Ads on “wallet security” / “revoke approvals” once trial→paid conversion ≥5%.                                                                                                         |
|Pivot needed (security framing doesn’t convert)                                        |Low       |High                   |Same codebase + RevenueCat + multilingual stack pivots in 1–2 weeks to “crypto net-worth tracker for MENA/Ru” — the #2 opportunity.                                                                                |

-----

## 11. Success Metrics (Year 1)

|Metric                       |M3     |M6      |M12      |
|-----------------------------|-------|--------|---------|
|Downloads                    |10K    |75K     |350K     |
|MAU                          |4K     |25K     |90K      |
|Trial start rate (free→trial)|5%     |8%      |10%      |
|Trial→paid conversion        |35%    |45%     |55%      |
|Paid subscribers             |200    |1,800   |7,500    |
|Blended ARPU (annualized)    |$30    |$34     |$38      |
|**ARR**                      |**$6K**|**$61K**|**$285K**|
|Annual retention (M12 cohort)|—      |—       |40%      |
|App Store rating             |4.5+   |4.6+    |4.7+     |

-----

## 12. Open Questions for Next Iteration

Decided post-launch based on user signal:

- Add Solana support? (Threshold: >30% of feedback requests it)
- Add Apple Watch app + complications? (M3–M6)
- Add Lock Screen widgets? (M3)
- Add B2B SDK “Aegis Inside” for wallet apps to embed? (M12 if PMF clear)
- Convert individual → organization developer account proactively? (Probably yes by M3)
- Migrate SQLite → Postgres if write volume exceeds ~50 writes/sec? (Unlikely before M12)
