import Foundation
import Testing
@testable import Aegis

@Suite("APIError envelope parsing")
struct APIErrorTests {
    private func body(_ json: String) -> Data { Data(json.utf8) }

    @Test func parses_invalid_address() {
        let data = body(#"{"error":{"code":"invalid_address","message":"bad addr"}}"#)
        let err = APIErrorEnvelope.from(data: data, status: 422)
        #expect(err == .validation(message: "bad addr"))
    }

    @Test func parses_validation_error() {
        let data = body(#"{"error":{"code":"validation_error","message":"Request validation failed"}}"#)
        let err = APIErrorEnvelope.from(data: data, status: 422)
        #expect(err == .validation(message: "Request validation failed"))
    }

    @Test func parses_not_found() {
        let data = body(#"{"error":{"code":"not_found","message":"missing"}}"#)
        let err = APIErrorEnvelope.from(data: data, status: 404)
        #expect(err == .notFound(message: "missing"))
    }

    @Test func parses_not_configured() {
        let data = body(#"{"error":{"code":"not_configured","message":"ETHERSCAN_API_KEY missing"}}"#)
        let err = APIErrorEnvelope.from(data: data, status: 503)
        #expect(err == .notConfigured(message: "ETHERSCAN_API_KEY missing"))
    }

    @Test func parses_upstream_rate_limited() {
        let data = body(#"{"error":{"code":"upstream_rate_limited","message":"Max rate limit reached"}}"#)
        let err = APIErrorEnvelope.from(data: data, status: 503)
        #expect(err == .upstreamRateLimited(message: "Max rate limit reached"))
    }

    @Test func parses_upstream_etherscan() {
        let data = body(#"{"error":{"code":"upstream_etherscan","message":"Invalid API Key"}}"#)
        let err = APIErrorEnvelope.from(data: data, status: 502)
        #expect(err == .upstreamEtherscan(message: "Invalid API Key"))
    }

    @Test func parses_upstream_alchemy() {
        let data = body(#"{"error":{"code":"upstream_alchemy","message":"execution reverted"}}"#)
        let err = APIErrorEnvelope.from(data: data, status: 502)
        #expect(err == .upstreamAlchemy(message: "execution reverted"))
    }

    @Test func unknown_code_becomes_server_error() {
        let data = body(#"{"error":{"code":"weird_unknown","message":"oops"}}"#)
        let err = APIErrorEnvelope.from(data: data, status: 500)
        #expect(err == .server(code: "weird_unknown", message: "oops", status: 500))
    }

    @Test func malformed_body_becomes_unexpected() {
        let data = body("not json")
        let err = APIErrorEnvelope.from(data: data, status: 500)
        #expect(err == .unexpected(status: 500, body: "not json"))
    }

    @Test func empty_body_becomes_unexpected_with_empty_body() {
        let err = APIErrorEnvelope.from(data: Data(), status: 504)
        #expect(err == .unexpected(status: 504, body: ""))
    }

    @Test func error_description_is_user_friendly() {
        #expect(APIError.validation(message: "bad addr").errorDescription == "bad addr")
        #expect(APIError.notFound(message: "missing").errorDescription == "missing")
        #expect(
            APIError.upstreamRateLimited(message: "Max rate").errorDescription
                == "Upstream rate limited: Max rate"
        )
        #expect(
            APIError.server(code: "x_err", message: "y", status: 500).errorDescription == "x_err: y"
        )
    }
}
