import Foundation

public struct TokenDTO: Codable, Equatable, Hashable, Sendable {
    public let chain: String
    public let address: String
    public let symbol: String?
    public let decimals: Int?
    public let name: String?
}
