import Foundation

@MainActor
public final class ApprovalsViewModel: ObservableObject {
    public enum State: Equatable {
        case idle
        case scanning
        case loaded([ApprovalDTO])
        case failed(String)
    }

    /// 2^256 - 1, the canonical "unlimited" ERC-20 approval amount.
    public static let unlimitedAmount =
        "115792089237316195423570985008687907853269984665640564039457584007913129639935"

    @Published public private(set) var state: State = .idle
    @Published public var unlimitedOnly: Bool = false

    private let api: AegisAPIClient
    private let deviceId: String
    /// Lowercase 0x… address of the wallet this view is scoped to.
    public let wallet: String

    public init(api: AegisAPIClient, deviceId: String, wallet: String) {
        self.api = api
        self.deviceId = deviceId
        self.wallet = wallet.lowercased()
    }

    public func scan() async {
        state = .scanning
        do {
            let list = try await api.scan(deviceId: deviceId)
            let sorted = list.approvals.sorted { $0.blockNumber > $1.blockNumber }
            state = .loaded(sorted)
        } catch let err as APIError {
            state = .failed(err.localizedDescription)
        } catch {
            state = .failed(error.localizedDescription)
        }
    }

    /// Approvals for the scoped wallet, with optional `unlimitedOnly` filter applied.
    public var visibleApprovals: [ApprovalDTO] {
        guard case .loaded(let rows) = state else { return [] }
        let scoped = rows.filter { $0.walletAddress == wallet }
        guard unlimitedOnly else { return scoped }
        return scoped.filter { $0.amount == Self.unlimitedAmount }
    }

    /// Whether the scoped wallet has at least one unlimited approval.
    public var hasUnlimitedExposure: Bool {
        guard case .loaded(let rows) = state else { return false }
        return rows.contains { $0.walletAddress == wallet && $0.amount == Self.unlimitedAmount }
    }
}
