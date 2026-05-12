import Foundation

public struct DeviceDTO: Codable, Equatable, Sendable {
    public let id: String
    public let pushToken: String?
    public let tier: String
    public let createdAt: Date
    public let updatedAt: Date
}
