import Foundation

public actor DeviceIdentityStore {
    public static let service = "app.aegis.identity"
    public static let account = "device_id"

    private let storage: KeychainStorage

    public init(storage: KeychainStorage = SystemKeychainStorage()) {
        self.storage = storage
    }

    /// Returns the persistent device UUID, generating + storing on first call.
    public func deviceId() throws -> String {
        if let existing = try storage.read(service: Self.service, account: Self.account),
           let value = String(data: existing, encoding: .utf8),
           !value.isEmpty {
            return value
        }
        let fresh = UUID().uuidString
        try storage.write(Data(fresh.utf8), service: Self.service, account: Self.account)
        return fresh
    }

    /// Clears the stored device id. Intended for tests / sign-out flows.
    public func reset() throws {
        try storage.delete(service: Self.service, account: Self.account)
    }
}
