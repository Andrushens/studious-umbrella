import Foundation

public struct ApprovalDTO: Codable, Equatable, Sendable, Identifiable {
    public let token: TokenDTO
    public let spender: String
    public let amount: String
    public let blockNumber: Int
    public let txHash: String
    public let firstSeenAt: Date
    public let lastSeenAt: Date

    /// Stable identity for SwiftUI ForEach: (token.address, spender) is the unique pair.
    public var id: String { "\(token.address)|\(spender)" }
}

public struct ApprovalList: Codable, Equatable, Sendable {
    public let approvals: [ApprovalDTO]
}
