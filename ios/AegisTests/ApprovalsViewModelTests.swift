import Foundation
import Testing
@testable import Aegis

@Suite("ApprovalsViewModel")
@MainActor
struct ApprovalsViewModelTests {
    final class StubAPI: AegisAPIClient, @unchecked Sendable {
        var scanResult: Result<ApprovalList, Error> = .success(ApprovalList(approvals: []))
        var scanCalls: [String] = []

        func healthz() async throws -> HealthResponse { HealthResponse(status: "ok") }
        func registerDevice(_ body: RegisterDeviceBody) async throws -> DeviceDTO { fatalError() }
        func addWatchedAddress(deviceId: String, body: AddWatchedAddressBody) async throws -> WatchedAddressDTO { fatalError() }
        func listWatchedAddresses(deviceId: String) async throws -> WatchedAddressList { fatalError() }
        func deleteWatchedAddress(deviceId: String, addressId: Int) async throws { fatalError() }
        func scan(deviceId: String) async throws -> ApprovalList {
            scanCalls.append(deviceId)
            switch scanResult {
            case .success(let l): return l
            case .failure(let e): throw e
            }
        }
    }

    private func token(_ symbol: String, address: String = "0xtok") -> TokenDTO {
        TokenDTO(chain: "ethereum", address: address, symbol: symbol, decimals: 18, name: nil)
    }

    private func approval(
        symbol: String, amount: String, block: Int, spender: String = "0xs"
    ) -> ApprovalDTO {
        ApprovalDTO(
            token: token(symbol),
            spender: spender,
            amount: amount,
            blockNumber: block,
            txHash: "0xtx\(block)",
            firstSeenAt: .distantPast,
            lastSeenAt: .distantPast
        )
    }

    @Test func scan_loaded_sorted_by_descending_block_number() async {
        let api = StubAPI()
        api.scanResult = .success(ApprovalList(approvals: [
            approval(symbol: "A", amount: "1", block: 100),
            approval(symbol: "B", amount: "2", block: 300),
            approval(symbol: "C", amount: "3", block: 200, spender: "0xs2"),
        ]))
        let vm = ApprovalsViewModel(api: api, deviceId: "dev")
        await vm.scan()
        if case .loaded(let rows) = vm.state {
            #expect(rows.map(\.blockNumber) == [300, 200, 100])
        } else {
            Issue.record("expected .loaded")
        }
        #expect(api.scanCalls == ["dev"])
    }

    @Test func scan_failed_state_on_apierror() async {
        let api = StubAPI()
        api.scanResult = .failure(APIError.notConfigured(message: "ETHERSCAN_API_KEY missing"))
        let vm = ApprovalsViewModel(api: api, deviceId: "dev")
        await vm.scan()
        if case .failed(let msg) = vm.state {
            #expect(msg == "ETHERSCAN_API_KEY missing")
        } else {
            Issue.record("expected .failed")
        }
    }

    @Test func visibleApprovals_returns_all_when_filter_off() async {
        let api = StubAPI()
        api.scanResult = .success(ApprovalList(approvals: [
            approval(symbol: "USDC", amount: "100", block: 1),
            approval(symbol: "USDT", amount: ApprovalsViewModel.unlimitedAmount, block: 2, spender: "0xs2"),
        ]))
        let vm = ApprovalsViewModel(api: api, deviceId: "dev")
        await vm.scan()
        #expect(vm.unlimitedOnly == false)
        #expect(vm.visibleApprovals.count == 2)
    }

    @Test func visibleApprovals_filters_when_unlimited_only() async {
        let api = StubAPI()
        api.scanResult = .success(ApprovalList(approvals: [
            approval(symbol: "USDC", amount: "100", block: 1),
            approval(symbol: "USDT", amount: ApprovalsViewModel.unlimitedAmount, block: 2, spender: "0xs2"),
        ]))
        let vm = ApprovalsViewModel(api: api, deviceId: "dev")
        await vm.scan()
        vm.unlimitedOnly = true
        #expect(vm.visibleApprovals.map(\.amount) == [ApprovalsViewModel.unlimitedAmount])
    }

    @Test func hasUnlimitedExposure_detects_max_uint256() async {
        let api = StubAPI()
        api.scanResult = .success(ApprovalList(approvals: [
            approval(symbol: "X", amount: "1", block: 1),
            approval(symbol: "Y", amount: ApprovalsViewModel.unlimitedAmount, block: 2, spender: "0xs2"),
        ]))
        let vm = ApprovalsViewModel(api: api, deviceId: "dev")
        await vm.scan()
        #expect(vm.hasUnlimitedExposure == true)
    }

    @Test func hasUnlimitedExposure_false_in_idle() async {
        let api = StubAPI()
        let vm = ApprovalsViewModel(api: api, deviceId: "dev")
        #expect(vm.hasUnlimitedExposure == false)
    }
}
