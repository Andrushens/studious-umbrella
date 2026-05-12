import Foundation
import Testing
@testable import Aegis

@Suite("EthAddressValidator.normalize")
struct EthAddressValidatorTests {
    @Test func accepts_lowercase() {
        #expect(EthAddressValidator.normalize("0xd8da6bf26964af9d7eed9e03e53415d37aa96045")
            == "0xd8da6bf26964af9d7eed9e03e53415d37aa96045")
    }

    @Test func lowercases_eip55_mixed_case() {
        #expect(EthAddressValidator.normalize("0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045")
            == "0xd8da6bf26964af9d7eed9e03e53415d37aa96045")
    }

    @Test func trims_whitespace() {
        #expect(EthAddressValidator.normalize("  0xd8da6bf26964af9d7eed9e03e53415d37aa96045\n")
            == "0xd8da6bf26964af9d7eed9e03e53415d37aa96045")
    }

    @Test func rejects_without_prefix() {
        #expect(EthAddressValidator.normalize("d8da6bf26964af9d7eed9e03e53415d37aa96045") == nil)
    }

    @Test func rejects_too_short() {
        #expect(EthAddressValidator.normalize("0x1234") == nil)
    }

    @Test func rejects_too_long() {
        #expect(EthAddressValidator.normalize("0xd8da6bf26964af9d7eed9e03e53415d37aa9604500") == nil)
    }

    @Test func rejects_non_hex() {
        #expect(EthAddressValidator.normalize("0xZZZA6BF26964aF9D7eEd9e03E53415D37aA96045") == nil)
    }

    @Test func rejects_empty() {
        #expect(EthAddressValidator.normalize("") == nil)
    }
}
