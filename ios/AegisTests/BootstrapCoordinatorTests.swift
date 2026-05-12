import Foundation
import Testing
@testable import Aegis

@Suite("BootstrapCoordinator")
@MainActor
struct BootstrapCoordinatorTests {
    final class MockAPI: AegisAPIClient, @unchecked Sendable {
        var registerResult: Result<DeviceDTO, Error> = .success(
            DeviceDTO(
                id: "test", pushToken: nil, tier: "free",
                createdAt: .distantPast, updatedAt: .distantPast
            )
        )
        var registerCalls: [RegisterDeviceBody] = []

        func healthz() async throws -> HealthResponse {
            HealthResponse(status: "ok")
        }
        func registerDevice(_ body: RegisterDeviceBody) async throws -> DeviceDTO {
            registerCalls.append(body)
            switch registerResult {
            case .success(let d): return d
            case .failure(let e): throw e
            }
        }
        func addWatchedAddress(deviceId: String, body: AddWatchedAddressBody) async throws -> WatchedAddressDTO {
            fatalError("not used in these tests")
        }
        func listWatchedAddresses(deviceId: String) async throws -> WatchedAddressList {
            fatalError("not used in these tests")
        }
        func deleteWatchedAddress(deviceId: String, addressId: Int) async throws {
            fatalError("not used in these tests")
        }
        func scan(deviceId: String) async throws -> ApprovalList {
            fatalError("not used in these tests")
        }
    }

    private func makeEnv(api: MockAPI) -> AppEnvironment {
        AppEnvironment(
            api: api,
            identity: DeviceIdentityStore(storage: InMemoryKeychain()),
            baseURL: URL(string: "http://stub.test")!
        )
    }

    @Test func bootstrap_sets_ready_with_persistent_device_id() async throws {
        let api = MockAPI()
        let env = makeEnv(api: api)
        let coord = BootstrapCoordinator(env: env)
        await coord.start()
        if case .ready(let id) = coord.state {
            #expect(UUID(uuidString: id) != nil)
            #expect(api.registerCalls.first?.deviceId == id)
        } else {
            Issue.record("expected .ready, got \(coord.state)")
        }
    }

    @Test func bootstrap_failure_sets_failed_with_message() async throws {
        let api = MockAPI()
        api.registerResult = .failure(APIError.notConfigured(message: "ETHERSCAN_API_KEY missing"))
        let env = makeEnv(api: api)
        let coord = BootstrapCoordinator(env: env)
        await coord.start()
        if case .failed(let message) = coord.state {
            #expect(message == "ETHERSCAN_API_KEY missing")
        } else {
            Issue.record("expected .failed, got \(coord.state)")
        }
    }

    @Test func bootstrap_reuses_same_device_id_across_starts() async throws {
        let api = MockAPI()
        let env = makeEnv(api: api)
        let coord = BootstrapCoordinator(env: env)
        await coord.start()
        let first: String
        if case .ready(let id) = coord.state {
            first = id
        } else {
            Issue.record("first start didn't reach ready")
            return
        }
        // Reset state and re-run
        await coord.start()
        if case .ready(let id) = coord.state {
            #expect(id == first)
        } else {
            Issue.record("second start didn't reach ready")
        }
        #expect(api.registerCalls.count == 2)
        #expect(api.registerCalls[0].deviceId == api.registerCalls[1].deviceId)
    }
}
