import Foundation

/// DI container. Holds long-lived dependencies for the app process.
public final class AppEnvironment: ObservableObject, @unchecked Sendable {
    public let api: AegisAPIClient
    public let identity: DeviceIdentityStore
    public let baseURL: URL

    public init(
        api: AegisAPIClient,
        identity: DeviceIdentityStore,
        baseURL: URL
    ) {
        self.api = api
        self.identity = identity
        self.baseURL = baseURL
    }

    /// Convenience builder for production: reads BASE_URL from Info.plist, wires the real Keychain.
    public static func live(bundle: Bundle = .main) throws -> AppEnvironment {
        let provider = try BundleBaseURLProvider(bundle: bundle)
        let api = AegisAPI(provider: provider)
        return AppEnvironment(
            api: api,
            identity: DeviceIdentityStore(),
            baseURL: provider.baseURL
        )
    }
}

/// Result of the startup bootstrap (device id resolution + POST /v1/devices).
public enum BootstrapState: Equatable, Sendable {
    case loading
    case ready(deviceId: String)
    case failed(message: String)
}

/// Drives the bootstrap state machine — used by the root view.
@MainActor
public final class BootstrapCoordinator: ObservableObject {
    @Published public private(set) var state: BootstrapState = .loading
    private let env: AppEnvironment

    public init(env: AppEnvironment) {
        self.env = env
    }

    public func start() async {
        do {
            let deviceId = try await env.identity.deviceId()
            _ = try await env.api.registerDevice(.init(deviceId: deviceId))
            self.state = .ready(deviceId: deviceId)
        } catch let err as APIError {
            self.state = .failed(message: err.localizedDescription)
        } catch {
            self.state = .failed(message: error.localizedDescription)
        }
    }
}
