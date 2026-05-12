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
            ContentView()
                .environmentObject(env)
                .environmentObject(coordinator)
                .task {
                    await coordinator.start()
                }
        }
    }
}
