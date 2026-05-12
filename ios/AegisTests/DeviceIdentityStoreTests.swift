import Foundation
import Testing
@testable import Aegis

@Suite("DeviceIdentityStore")
struct DeviceIdentityStoreTests {
    @Test func first_call_generates_uuid() async throws {
        let storage = InMemoryKeychain()
        let store = DeviceIdentityStore(storage: storage)
        let id = try await store.deviceId()
        #expect(UUID(uuidString: id) != nil)
    }

    @Test func subsequent_calls_return_same_id() async throws {
        let storage = InMemoryKeychain()
        let store = DeviceIdentityStore(storage: storage)
        let id1 = try await store.deviceId()
        let id2 = try await store.deviceId()
        #expect(id1 == id2)
    }

    @Test func reset_clears_storage_and_next_call_generates_new() async throws {
        let storage = InMemoryKeychain()
        let store = DeviceIdentityStore(storage: storage)
        let id1 = try await store.deviceId()
        try await store.reset()
        let id2 = try await store.deviceId()
        #expect(id1 != id2)
    }

    @Test func storage_value_is_utf8_uuid_string() async throws {
        let storage = InMemoryKeychain()
        let store = DeviceIdentityStore(storage: storage)
        let id = try await store.deviceId()
        let raw = try storage.read(
            service: DeviceIdentityStore.service,
            account: DeviceIdentityStore.account
        )
        #expect(raw == Data(id.utf8))
    }
}
