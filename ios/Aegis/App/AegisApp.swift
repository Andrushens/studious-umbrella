import SwiftUI

@main
struct AegisApp: App {
    @StateObject private var coordinator: BootstrapCoordinator
    private let env: AppEnvironment

    init() {
        let env: AppEnvironment
        do {
            env = try AppEnvironment.live()
        } catch {
            // Fall back to a placeholder env that points at localhost; the
            // bootstrap will surface the configuration error to the user.
            let fallbackURL = URL(string: "http://localhost:8000")!
            let provider = StaticBaseURLProvider(fallbackURL)
            env = AppEnvironment(
                api: AegisAPI(provider: provider),
                identity: DeviceIdentityStore(),
                baseURL: fallbackURL
            )
        }
        self.env = env
        _coordinator = StateObject(wrappedValue: BootstrapCoordinator(env: env))
    }

    var body: some Scene {
        WindowGroup {
            BootstrapRootView()
                .environmentObject(env)
                .environmentObject(coordinator)
                .task {
                    await coordinator.start()
                }
        }
    }
}

/// Temporary root view. Real views ship in iOS Tasks 9-10.
struct BootstrapRootView: View {
    @EnvironmentObject private var env: AppEnvironment
    @EnvironmentObject private var coordinator: BootstrapCoordinator

    var body: some View {
        NavigationStack {
            VStack(spacing: 16) {
                switch coordinator.state {
                case .loading:
                    ProgressView("Connecting to Aegis…")
                case .ready(let deviceId):
                    Image(systemName: "shield.checkered")
                        .font(.system(size: 48))
                        .foregroundStyle(.tint)
                    Text("Aegis")
                        .font(.largeTitle).bold()
                    Text("Device registered")
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                    Text(deviceId)
                        .font(.caption.monospaced())
                        .textSelection(.enabled)
                case .failed(let message):
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
            }
            .padding()
            .navigationTitle("Aegis")
        }
    }
}
