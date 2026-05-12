# Aegis iOS

Swift / SwiftUI client for the Aegis backend. Monitors EVM wallets for
risky ERC-20 approvals.

> **Mac required.** This directory contains source files + an XcodeGen
> `project.yml`. The `.xcodeproj` is generated on demand and not
> committed — regenerate locally with `xcodegen`.

## Prerequisites

- macOS with **Xcode 16.0+** (Swift 5.10, iOS 17 SDK, Swift Testing).
- [XcodeGen](https://github.com/yonaskolb/XcodeGen): `brew install xcodegen`.
- The Aegis backend running locally (see `../backend/README.md`).

## First-time setup

```bash
cd ios
xcodegen generate          # creates Aegis.xcodeproj
open Aegis.xcodeproj
```

## Build

```bash
xcodebuild -project Aegis.xcodeproj \
           -scheme Aegis \
           -destination 'platform=iOS Simulator,name=iPhone 15' \
           build
```

## Test

```bash
xcodebuild -project Aegis.xcodeproj \
           -scheme Aegis \
           -destination 'platform=iOS Simulator,name=iPhone 15' \
           test
```

The Swift Testing suite covers:

| Area | Tests |
|------|-------|
| DTO decoding | snake_case → camelCase, ISO 8601, nested `TokenDTO` |
| `APIError` envelope | every backend error code → mapped Swift case |
| `BaseURLProvider` | Info.plist → URL, missing/invalid handling |
| `AegisAPI` | every endpoint, URLProtocol-stubbed, error paths |
| `EthAddressValidator` | EIP-55 normalization, format rejection |
| `DeviceIdentityStore` | first-call generates, reused across calls, reset |
| `BootstrapCoordinator` | happy path, failure, reuse of device id |
| `WatchlistViewModel` | refresh, add (with normalization), idempotent add, delete (optimistic + rollback) |
| `ApprovalsViewModel` | sorting, filter, unlimited detection, failure |

## End-to-end smoke test with the backend

In one terminal:

```bash
cd ../backend
cp .env.example .env
# Fill in ETHERSCAN_API_KEY and ALCHEMY_API_KEY from your dashboards.
SCHEDULER_ENABLED=false uv run uvicorn aegis.main:app --port 8000
```

In Xcode:

1. Select the **Aegis** scheme + an iPhone Simulator.
2. Run.
3. On launch, the app generates a device UUID (Keychain), then calls
   `POST /v1/devices` against `http://localhost:8000` (per
   `Configs/Debug.xcconfig`).
4. Tap **+**, paste `0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045`, tap **Add**.
   You should see the wallet appear in the Watchlist.
5. Tap the wallet → tap **Scan now** → approvals populate from real
   Etherscan + Alchemy data.
6. Tap **Revoke** on any approval → Safari opens revoke.cash for that
   wallet.

## Configuration

| Build config | `API_BASE_URL` source                            |
|--------------|--------------------------------------------------|
| Debug        | `Configs/Debug.xcconfig` → `http://localhost:8000` |
| Release      | `Configs/Release.xcconfig` → `https://api.aegis.app` (placeholder) |

`Info.plist` references `$(API_BASE_URL)`; the value is substituted at
build time by Xcode. `BundleBaseURLProvider` reads
`Bundle.main.object(forInfoDictionaryKey: "API_BASE_URL")` at app launch.

## Directory layout

```
ios/
├── project.yml                     # XcodeGen
├── Configs/                        # xcconfig per build configuration
├── Aegis/
│   ├── App/                        # @main + DI container + Info.plist
│   ├── Models/                     # Codable DTOs + JSONDecoder helper
│   ├── Networking/                 # APIError, BaseURLProvider, AegisAPI
│   ├── Identity/                   # Keychain-backed device UUID
│   ├── Utilities/                  # EthAddressValidator
│   ├── ViewModels/                 # WatchlistViewModel, ApprovalsViewModel
│   ├── Views/                      # SwiftUI screens + RevokeLinkButton
│   ├── Localization/               # en / es / ar Localizable.strings
│   └── Resources/                  # Assets.xcassets
└── AegisTests/                     # Swift Testing suites + JSON fixtures
```

## Localization

English is populated; Spanish (`es.lproj`) and Arabic (`ar.lproj`) ship
with English placeholders (see TODO comments in each
`Localizable.strings`). Translation + RTL audit land in PRD week 7.

## Backend pairing

Every iOS HTTP call hits one of the backend's v1 endpoints. See
[`../docs/superpowers/specs/2026-05-11-aegis-week1-backend-design.md`](../docs/superpowers/specs/2026-05-11-aegis-week1-backend-design.md)
for the contract. The iOS DTOs mirror `backend/src/aegis/schemas.py` exactly
(snake_case keys at the wire, camelCase Swift properties).

## Linux dev environment limitation

The repo is primarily scaffolded from a Linux dev environment which has
no Xcode. Source files are checked in but never compiled on Linux. Run
the build + test recipe above on a Mac before merging changes.

## Known limitations

- **Device-wide scan, per-wallet navigation.** `POST /v1/devices/{id}/scan`
  aggregates approvals across every watched wallet on the device. The current
  iOS navigation routes from a tapped wallet row into `ApprovalsView`, but the
  data shown is device-wide. The `Revoke` deep-link on each row uses the
  wallet address the user navigated from, which may not match the actual
  owner of that approval when multiple wallets are watched. Resolution path:
  backend follow-up to include `wallet_address` in the `ApprovalOut`
  schema, then group/badge approvals by wallet in the iOS view.
- **`armv7` placeholder in `Info.plist`.** Cosmetic only — iOS 17 hardware is
  all `arm64`. Update before App Store submission.
- **Signing.** `project.yml` ships no `DEVELOPMENT_TEAM`. Add yours in
  Xcode's Signing &amp; Capabilities tab (or in xcconfig) before building to a
  physical device.

## Out of scope (later PRD weeks)

- SwiftData + CloudKit sync (week 3)
- Wallet Health Score + Swift Charts (week 3)
- Push notifications via FCM/APNs (week 4)
- RevenueCat paywall + IAP trial flow (week 5)
- Token Risk Scanner screen (week 6)
- Biometric lock, Widgets, Apple Watch (post-MVP)
- ENS resolution (needs backend; week 2)
- QR-scanner camera UI (week 2)
- Full Spanish + Arabic translations + RTL screenshot testing (week 7)
- TelemetryDeck analytics, Sentry for iOS (week 6 onward)
- Multi-chain UI (Base / Arbitrum / Optimism / Polygon / BSC) (week 2)
