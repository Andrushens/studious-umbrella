import Foundation

public struct ApprovalDTO: Codable, Equatable, Sendable, Identifiable {
    public let token: TokenDTO
    public let walletAddress: String
    public let spender: String
    public let amount: String
    public let blockNumber: Int
    public let txHash: String
    public let firstSeenAt: Date
    public let lastSeenAt: Date

    /// Stable identity unique across watched wallets (same token+spender pair
    /// may legitimately appear per wallet) AND across event re-emissions
    /// (tx_hash tiebreaks).
    public var id: String { "\(walletAddress)|\(token.address)|\(spender)|\(txHash)" }
}

public struct ApprovalList: Codable, Equatable, Sendable {
    public let approvals: [ApprovalDTO]
}
