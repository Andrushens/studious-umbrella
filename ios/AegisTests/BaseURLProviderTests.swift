import Foundation
import Testing
@testable import Aegis

@Suite("BaseURLProvider")
struct BaseURLProviderTests {
    private final class StubBundle: Bundle {
        let stub: [String: Any]
        init(stub: [String: Any]) {
            self.stub = stub
            super.init()
        }

        required init?(coder: NSCoder) { fatalError() }

        override func object(forInfoDictionaryKey key: String) -> Any? {
            stub[key]
        }
    }

    @Test func reads_api_base_url_from_bundle() throws {
        let bundle = StubBundle(stub: ["API_BASE_URL": "http://localhost:8000"])
        let provider = try BundleBaseURLProvider(bundle: bundle)
        #expect(provider.baseURL.absoluteString == "http://localhost:8000")
    }

    @Test func throws_when_key_missing() {
        let bundle = StubBundle(stub: [:])
        #expect(throws: BaseURLError.missingOrInvalid) {
            _ = try BundleBaseURLProvider(bundle: bundle)
        }
    }

    @Test func throws_when_value_empty() {
        let bundle = StubBundle(stub: ["API_BASE_URL": ""])
        #expect(throws: BaseURLError.missingOrInvalid) {
            _ = try BundleBaseURLProvider(bundle: bundle)
        }
    }

    @Test func throws_when_value_not_a_url() {
        let bundle = StubBundle(stub: ["API_BASE_URL": "   "])
        #expect(throws: BaseURLError.self) {
            _ = try BundleBaseURLProvider(bundle: bundle)
        }
    }

    @Test func static_provider_wraps_url() {
        let url = URL(string: "https://example.com")!
        let provider = StaticBaseURLProvider(url)
        #expect(provider.baseURL == url)
    }
}
