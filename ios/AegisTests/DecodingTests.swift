import Foundation
import Testing
@testable import Aegis

@Suite("DTO decoding")
struct DecodingTests {
    private func loadFixture(_ name: String) throws -> Data {
        let bundle = Bundle(for: type(of: FixtureLoaderProbe()))
        guard let url = bundle.url(forResource: name, withExtension: "json", subdirectory: "Fixtures")
            ?? bundle.url(forResource: name, withExtension: "json")
        else {
            throw FixtureError.notFound(name)
        }
        return try Data(contentsOf: url)
    }

    @Test func decodes_device_response() throws {
        let data = try loadFixture("device_response")
        let device = try AegisDecoders.backend.decode(DeviceDTO.self, from: data)
        #expect(device.id == "test-device-1")
        #expect(device.pushToken == nil)
        #expect(device.tier == "free")
    }

    @Test func decodes_addresses_response_with_nullable_nickname() throws {
        let data = try loadFixture("addresses_response")
        let list = try AegisDecoders.backend.decode(WatchedAddressList.self, from: data)
        #expect(list.addresses.count == 2)
        #expect(list.addresses[0].address == "0xd8da6bf26964af9d7eed9e03e53415d37aa96045")
        #expect(list.addresses[0].nickname == "Vitalik")
        #expect(list.addresses[1].nickname == nil)
    }

    @Test func decodes_approvals_response_with_nested_token() throws {
        let data = try loadFixture("approvals_response")
        let list = try AegisDecoders.backend.decode(ApprovalList.self, from: data)
        #expect(list.approvals.count == 2)
        let usdc = list.approvals[0]
        #expect(usdc.token.symbol == "USDC")
        #expect(usdc.token.decimals == 6)
        #expect(usdc.amount == "0")
        #expect(usdc.blockNumber == 258)
        #expect(usdc.txHash == "0xaaaa2")
        let usdt = list.approvals[1]
        #expect(usdt.amount == "100000000000000000")
    }

    @Test func approval_id_includes_tx_hash() throws {
        let data = try loadFixture("approvals_response")
        let list = try AegisDecoders.backend.decode(ApprovalList.self, from: data)
        let usdc = list.approvals[0]
        #expect(usdc.id == "0xd8da6bf26964af9d7eed9e03e53415d37aa96045|0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48|0x1111111254eeb25477b68fb85ed929f73a960582|0xaaaa2")
    }

    @Test func decodes_iso8601_with_fractional_seconds() throws {
        let data = try loadFixture("device_response")
        let device = try AegisDecoders.backend.decode(DeviceDTO.self, from: data)
        #expect(device.createdAt == device.updatedAt)
        let components = Calendar(identifier: .gregorian).dateComponents(
            in: TimeZone(identifier: "UTC")!, from: device.createdAt
        )
        #expect(components.year == 2026)
        #expect(components.month == 5)
        #expect(components.day == 12)
    }

    @Test func decodes_iso8601_without_tz_designator() throws {
        // Backend may sometimes emit naive timestamps; treat as UTC.
        let naive = #"{"id":"x","push_token":null,"tier":"free","created_at":"2026-05-12T10:00:00.123456","updated_at":"2026-05-12T10:00:00"}"#
        let device = try AegisDecoders.backend.decode(DeviceDTO.self, from: Data(naive.utf8))
        #expect(device.id == "x")
        // Should be parsed as UTC even without a designator.
        let components = Calendar(identifier: .gregorian).dateComponents(
            in: TimeZone(identifier: "UTC")!, from: device.createdAt
        )
        #expect(components.hour == 10)
        #expect(components.minute == 0)
    }
}

/// Helper class so `Bundle(for:)` resolves the test bundle that owns the JSON fixtures.
private final class FixtureLoaderProbe {}

private enum FixtureError: Error {
    case notFound(String)
}
