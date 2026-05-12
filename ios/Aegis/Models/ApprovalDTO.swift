import Foundation

public struct ApprovalDTO: Codable, Equatable, Sendable, Identifiable {
    public let token: TokenDTO
    public let spender: String
    public let amount: String
    public let blockNumber: Int
    public let txHash: String
    public let firstSeenAt: Date
    public let lastSeenAt: Date

    /// Stable identity unique even when the device-wide scan aggregates approvals
    /// from multiple watched wallets (same token+spender pair can recur per wallet).
    public var id: String { "\(token.address)|\(spender)|\(txHash)" }
}

public struct ApprovalList: Codable, Equatable, Sendable {
    public let approvals: [ApprovalDTO]
}
