import Foundation

public struct WatchedAddressDTO: Codable, Equatable, Identifiable, Sendable {
    public let id: Int
    public let deviceId: String
    public let address: String
    public let chain: String
    public let nickname: String?
    public let createdAt: Date
}

public struct WatchedAddressList: Codable, Equatable, Sendable {
    public let addresses: [WatchedAddressDTO]
}
