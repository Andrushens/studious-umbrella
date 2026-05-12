import SwiftUI

/// Root view: switches on bootstrap state and routes the user into the main flow.
struct ContentView: View {
    @EnvironmentObject private var env: AppEnvironment
    @EnvironmentObject private var coordinator: BootstrapCoordinator

    var body: some View {
        Group {
            switch coordinator.state {
            case .loading:
                VStack(spacing: 16) {
                    ProgressView()
                    Text("Connecting to Aegis…")
                        .font(.callout)
                        .foregroundStyle(.secondary)
                }
            case .ready(let deviceId):
                WatchlistView(
                    viewModel: WatchlistViewModel(api: env.api, deviceId: deviceId),
                    deviceId: deviceId
                )
            case .failed(let message):
                VStack(spacing: 16) {
                    Image(systemName: "exclamationmark.triangle.fill")
                        .font(.system(size: 48))
                        .foregroundStyle(.orange)
                    Text("Bootstrap failed")
                        .font(.headline)
                    Text(message)
                        .font(.callout)
                        .multilineTextAlignment(.center)
                        .padding(.horizontal)
                    Button("Retry") {
                        Task { await coordinator.start() }
                    }
                    .buttonStyle(.borderedProminent)
                }
                .padding()
            }
        }
    }
}
