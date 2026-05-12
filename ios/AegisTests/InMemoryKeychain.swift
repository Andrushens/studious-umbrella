import Foundation
@testable import Aegis

/// Thread-safe in-memory KeychainStorage for tests.
final class InMemoryKeychain: KeychainStorage, @unchecked Sendable {
    private let lock = NSLock()
    private var data: [String: Data] = [:]

    private func key(service: String, account: String) -> String {
        "\(service)::\(account)"
    }

    func read(service: String, account: String) throws -> Data? {
        lock.lock(); defer { lock.unlock() }
        return data[key(service: service, account: account)]
    }

    func write(_ data: Data, service: String, account: String) throws {
        lock.lock(); defer { lock.unlock() }
        self.data[key(service: service, account: account)] = data
    }

    func delete(service: String, account: String) throws {
        lock.lock(); defer { lock.unlock() }
        data.removeValue(forKey: key(service: service, account: account))
    }
}
