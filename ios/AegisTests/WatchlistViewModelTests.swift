import Foundation
import Testing
@testable import Aegis

@Suite("WatchlistViewModel")
@MainActor
struct WatchlistViewModelTests {
    // MARK: - Stub API

    final class StubAPI: AegisAPIClient, @unchecked Sendable {
        var listResult: Result<WatchedAddressList, Error> = .success(WatchedAddressList(addresses: []))
        var addResult: Result<WatchedAddressDTO, Error>?
        var deleteResult: Result<Void, Error> = .success(())
        var listCalls = 0
        var addCalls: [(deviceId: String, body: AddWatchedAddressBody)] = []
        var deleteCalls: [(deviceId: String, addressId: Int)] = []

        func healthz() async throws -> HealthResponse { HealthResponse(status: "ok") }
        func registerDevice(_ body: RegisterDeviceBody) async throws -> DeviceDTO {
            fatalError("unused")
        }
        func addWatchedAddress(deviceId: String, body: AddWatchedAddressBody) async throws -> WatchedAddressDTO {
            addCalls.append((deviceId, body))
            switch addResult {
            case .none: fatalError("addResult not configured")
            case .some(.success(let d)): return d
            case .some(.failure(let e)): throw e
            }
        }
        func listWatchedAddresses(deviceId: String) async throws -> WatchedAddressList {
            listCalls += 1
            switch listResult {
            case .success(let l): return l
            case .failure(let e): throw e
            }
        }
        func deleteWatchedAddress(deviceId: String, addressId: Int) async throws {
            deleteCalls.append((deviceId, addressId))
            switch deleteResult {
            case .success: return
            case .failure(let e): throw e
            }
        }
        func scan(deviceId: String) async throws -> ApprovalList {
            fatalError("unused")
        }
    }

    private func vitalik(id: Int = 1, nickname: String? = "Vitalik") -> WatchedAddressDTO {
        WatchedAddressDTO(
            id: id,
            deviceId: "dev",
            address: "0xd8da6bf26964af9d7eed9e03e53415d37aa96045",
            chain: "ethereum",
            nickname: nickname,
            createdAt: .distantPast
        )
    }

    @Test func refresh_loaded_state_on_success() async {
        let api = StubAPI()
        api.listResult = .success(WatchedAddressList(addresses: [vitalik()]))
        let vm = WatchlistViewModel(api: api, deviceId: "dev")
        await vm.refresh()
        if case .loaded(let rows) = vm.state {
            #expect(rows.count == 1)
            #expect(rows[0].address == "0xd8da6bf26964af9d7eed9e03e53415d37aa96045")
        } else {
            Issue.record("expected .loaded, got \(vm.state)")
        }
    }

    @Test func refresh_failed_state_on_apierror() async {
        let api = StubAPI()
        api.listResult = .failure(APIError.notFound(message: "no device"))
        let vm = WatchlistViewModel(api: api, deviceId: "dev")
        await vm.refresh()
        if case .failed(let msg) = vm.state {
            #expect(msg == "no device")
        } else {
            Issue.record("expected .failed")
        }
    }

    @Test func add_address_normalizes_and_appends() async {
        let api = StubAPI()
        api.listResult = .success(WatchedAddressList(addresses: []))
        api.addResult = .success(vitalik(id: 1))
        let vm = WatchlistViewModel(api: api, deviceId: "dev")
        await vm.refresh()
        _ = await vm.addAddress("0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045", nickname: "  Vitalik ")
        #expect(vm.addError == nil)
        #expect(api.addCalls.first?.body.address == "0xd8da6bf26964af9d7eed9e03e53415d37aa96045")
        #expect(api.addCalls.first?.body.nickname == "Vitalik")
        if case .loaded(let rows) = vm.state {
            #expect(rows.count == 1)
            #expect(rows[0].id == 1)
        } else {
            Issue.record("expected .loaded after add")
        }
    }

    @Test func add_address_rejects_invalid_locally_without_api_call() async {
        let api = StubAPI()
        let vm = WatchlistViewModel(api: api, deviceId: "dev")
        let result = await vm.addAddress("nope")
        #expect(result == nil)
        #expect(vm.addError == "Not a valid 0x… address")
        #expect(api.addCalls.isEmpty)
    }

    @Test func add_address_idempotent_replaces_existing_row() async {
        let api = StubAPI()
        let existing = vitalik(id: 5, nickname: "old")
        api.listResult = .success(WatchedAddressList(addresses: [existing]))
        api.addResult = .success(vitalik(id: 5, nickname: "new"))
        let vm = WatchlistViewModel(api: api, deviceId: "dev")
        await vm.refresh()
        _ = await vm.addAddress("0xd8da6bf26964af9d7eed9e03e53415d37aa96045", nickname: "new")
        if case .loaded(let rows) = vm.state {
            #expect(rows.count == 1)
            #expect(rows[0].nickname == "new")
        } else {
            Issue.record("expected .loaded")
        }
    }

    @Test func delete_optimistic_removes_then_persists() async {
        let api = StubAPI()
        api.listResult = .success(WatchedAddressList(addresses: [vitalik(id: 1), vitalik(id: 2, nickname: "Other")]))
        let vm = WatchlistViewModel(api: api, deviceId: "dev")
        await vm.refresh()
        await vm.deleteAddress(id: 1)
        #expect(api.deleteCalls.first?.addressId == 1)
        if case .loaded(let rows) = vm.state {
            #expect(rows.map(\.id) == [2])
        } else {
            Issue.record("expected .loaded")
        }
    }

    @Test func delete_rolls_back_on_failure() async {
        let api = StubAPI()
        api.listResult = .success(WatchedAddressList(addresses: [vitalik(id: 1)]))
        api.deleteResult = .failure(APIError.notConfigured(message: "boom"))
        let vm = WatchlistViewModel(api: api, deviceId: "dev")
        await vm.refresh()
        await vm.deleteAddress(id: 1)
        if case .loaded(let rows) = vm.state {
            #expect(rows.count == 1)
        } else {
            Issue.record("expected rollback to .loaded")
        }
        #expect(vm.addError == "boom")
    }

    @Test func add_address_propagates_api_error_to_addError() async {
        let api = StubAPI()
        api.listResult = .success(WatchedAddressList(addresses: []))
        api.addResult = .failure(APIError.validation(message: "server says no"))
        let vm = WatchlistViewModel(api: api, deviceId: "dev")
        await vm.refresh()
        let result = await vm.addAddress("0xd8da6bf26964af9d7eed9e03e53415d37aa96045")
        #expect(result == nil)
        #expect(vm.addError == "server says no")
        // State should not have gained a phantom row.
        if case .loaded(let rows) = vm.state {
            #expect(rows.isEmpty)
        } else {
            Issue.record("expected .loaded with empty rows")
        }
    }
}
