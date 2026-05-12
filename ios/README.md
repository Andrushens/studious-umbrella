# Aegis iOS

Swift / SwiftUI app that monitors EVM wallets via the Aegis backend.

> **Mac required.** This directory contains source files + an XcodeGen
> `project.yml`. The Xcode project itself is regenerated on demand.

## Prerequisites

- macOS with Xcode 16.0+ (Swift 5.10, iOS 17 SDK, Swift Testing).
- [XcodeGen](https://github.com/yonaskolb/XcodeGen): `brew install xcodegen`.

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

## Running against the local backend

In a separate terminal:

```bash
cd ../backend
cp .env.example .env       # then fill ETHERSCAN_API_KEY and ALCHEMY_API_KEY
SCHEDULER_ENABLED=false uv run uvicorn aegis.main:app --port 8000
```

Then build and run Aegis in the Simulator. Debug builds point at
`http://localhost:8000` via `Configs/Debug.xcconfig`.

## Configuration

| Build config | `API_BASE_URL` source                         |
|--------------|-----------------------------------------------|
| Debug        | `Configs/Debug.xcconfig` → `http://localhost:8000` |
| Release      | `Configs/Release.xcconfig` → `https://api.aegis.app` (placeholder) |

The Info.plist references `$(API_BASE_URL)`; the value is substituted at
build time.

## Linux dev environment limitation

Most of this repository is scaffolded from a Linux dev environment which
has no Xcode. Source files are checked in but never compiled here. Run
the build + tests on a Mac before merging changes.
