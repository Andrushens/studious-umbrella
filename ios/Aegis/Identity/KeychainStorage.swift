import Foundation
import Security

/// Minimal Keychain-shaped storage abstraction so tests can swap in an in-memory fake.
public protocol KeychainStorage: Sendable {
    func read(service: String, account: String) throws -> Data?
    func write(_ data: Data, service: String, account: String) throws
    func delete(service: String, account: String) throws
}

public enum KeychainError: Error, Equatable {
    case unhandledStatus(OSStatus)
    case unexpectedItemFormat
}

public struct SystemKeychainStorage: KeychainStorage {
    public init() {}

    public func read(service: String, account: String) throws -> Data? {
        var query = baseQuery(service: service, account: account)
        query[kSecMatchLimit as String] = kSecMatchLimitOne
        query[kSecReturnData as String] = true

        var item: CFTypeRef?
        let status = SecItemCopyMatching(query as CFDictionary, &item)
        if status == errSecItemNotFound { return nil }
        guard status == errSecSuccess else {
            throw KeychainError.unhandledStatus(status)
        }
        guard let data = item as? Data else {
            throw KeychainError.unexpectedItemFormat
        }
        return data
    }

    public func write(_ data: Data, service: String, account: String) throws {
        let baseAttrs = baseQuery(service: service, account: account)

        // Try update first.
        let updateAttrs: [String: Any] = [kSecValueData as String: data]
        let updateStatus = SecItemUpdate(baseAttrs as CFDictionary, updateAttrs as CFDictionary)
        if updateStatus == errSecSuccess { return }
        if updateStatus != errSecItemNotFound {
            throw KeychainError.unhandledStatus(updateStatus)
        }

        // Otherwise add.
        var addAttrs = baseAttrs
        addAttrs[kSecValueData as String] = data
        addAttrs[kSecAttrAccessible as String] = kSecAttrAccessibleAfterFirstUnlock
        let addStatus = SecItemAdd(addAttrs as CFDictionary, nil)
        guard addStatus == errSecSuccess else {
            throw KeychainError.unhandledStatus(addStatus)
        }
    }

    public func delete(service: String, account: String) throws {
        let query = baseQuery(service: service, account: account)
        let status = SecItemDelete(query as CFDictionary)
        guard status == errSecSuccess || status == errSecItemNotFound else {
            throw KeychainError.unhandledStatus(status)
        }
    }

    private func baseQuery(service: String, account: String) -> [String: Any] {
        [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account,
        ]
    }
}
