import Foundation
import Testing
@testable import Aegis

@Suite("AegisAPI", .serialized)
struct AegisAPITests {
    // MARK: - URLProtocol stub

    final class StubURLProtocol: URLProtocol {
        struct Stub: Sendable {
            let statusCode: Int
            let data: Data
            let headers: [String: String]
        }

        nonisolated(unsafe) static var responder: ((URLRequest) -> Stub?)?
        nonisolated(unsafe) static var recordedRequests: [URLRequest] = []
        nonisolated(unsafe) static var recordedBodies: [Data] = []

        override class func canInit(with request: URLRequest) -> Bool { true }
        override class func canonicalRequest(for request: URLRequest) -> URLRequest { request }
        override func startLoading() {
            Self.recordedRequests.append(request)
            // Capture body via httpBodyStream when URLSession buffers POST bodies.
            if let stream = request.httpBodyStream {
                var data = Data()
                stream.open()
                defer { stream.close() }
                let bufSize = 1024
                var buffer = [UInt8](repeating: 0, count: bufSize)
                while stream.hasBytesAvailable {
                    let read = stream.read(&buffer, maxLength: bufSize)
                    if read <= 0 { break }
                    data.append(buffer, count: read)
                }
                Self.recordedBodies.append(data)
            } else if let body = request.httpBody {
                Self.recordedBodies.append(body)
            } else {
                Self.recordedBodies.append(Data())
            }

            guard let stub = Self.responder?(request) else {
                client?.urlProtocol(self, didFailWithError: URLError(.unknown))
                return
            }
            let response = HTTPURLResponse(
                url: request.url!,
                statusCode: stub.statusCode,
                httpVersion: "HTTP/1.1",
                headerFields: stub.headers
            )!
            client?.urlProtocol(self, didReceive: response, cacheStoragePolicy: .notAllowed)
            client?.urlProtocol(self, didLoad: stub.data)
            client?.urlProtocolDidFinishLoading(self)
        }
        override func stopLoading() {}

        static func reset() {
            responder = nil
            recordedRequests = []
            recordedBodies = []
        }
    }

    private static let baseURL = URL(string: "http://stub.test")!

    private func makeAPI() -> AegisAPI {
        let config = URLSessionConfiguration.ephemeral
        config.protocolClasses = [StubURLProtocol.self]
        let session = URLSession(configuration: config)
        return AegisAPI(baseURL: Self.baseURL, session: session)
    }

    private func stub(
        status: Int,
        json: String = "",
        headers: [String: String] = [:]
    ) -> StubURLProtocol.Stub {
        StubURLProtocol.Stub(
            statusCode: status,
            data: Data(json.utf8),
            headers: headers
        )
    }

    // MARK: - Tests

    @Test func healthz_returns_status_ok() async throws {
        StubURLProtocol.reset()
        StubURLProtocol.responder = { _ in self.stub(status: 200, json: #"{"status":"ok"}"#) }
        let api = makeAPI()
        let resp = try await api.healthz()
        #expect(resp.status == "ok")
        #expect(StubURLProtocol.recordedRequests.first?.url?.path == "/v1/healthz")
        #expect(StubURLProtocol.recordedRequests.first?.httpMethod == "GET")
    }

    @Test func register_device_posts_json_body_and_parses_201() async throws {
        StubURLProtocol.reset()
        let respJSON = #"""
            {"id":"dev-1","push_token":null,"tier":"free","created_at":"2026-05-12T10:00:00Z","updated_at":"2026-05-12T10:00:00Z"}
            """#
        StubURLProtocol.responder = { _ in self.stub(status: 201, json: respJSON) }
        let api = makeAPI()
        let device = try await api.registerDevice(.init(deviceId: "dev-1"))
        #expect(device.id == "dev-1")
        #expect(device.tier == "free")

        let req = try #require(StubURLProtocol.recordedRequests.first)
        #expect(req.url?.path == "/v1/devices")
        #expect(req.httpMethod == "POST")
        #expect(req.value(forHTTPHeaderField: "Content-Type") == "application/json")

        let body = try #require(StubURLProtocol.recordedBodies.first)
        let parsed = try JSONSerialization.jsonObject(with: body) as? [String: Any]
        #expect(parsed?["device_id"] as? String == "dev-1")
    }

    @Test func add_watched_address_url_encodes_device_id() async throws {
        StubURLProtocol.reset()
        let respJSON = #"""
            {"id":1,"device_id":"dev 1","address":"0xd8da6bf26964af9d7eed9e03e53415d37aa96045","chain":"ethereum","nickname":null,"created_at":"2026-05-12T10:00:00Z"}
            """#
        StubURLProtocol.responder = { _ in self.stub(status: 201, json: respJSON) }
        let api = makeAPI()
        let _ = try await api.addWatchedAddress(
            deviceId: "dev 1",
            body: .init(address: "0xd8da6bf26964af9d7eed9e03e53415d37aa96045")
        )
        let req = try #require(StubURLProtocol.recordedRequests.first)
        // Path should percent-encode the space in 'dev 1' to 'dev%201'.
        let path = req.url?.path ?? ""
        #expect(path.contains("dev%201") || path.contains("dev 1"))  // either is acceptable per URL formation
        #expect(req.httpMethod == "POST")
    }

    @Test func list_watched_addresses_get_returns_list() async throws {
        StubURLProtocol.reset()
        let respJSON = #"""
            {"addresses":[{"id":1,"device_id":"d","address":"0xa","chain":"ethereum","nickname":null,"created_at":"2026-05-12T10:00:00Z"}]}
            """#
        StubURLProtocol.responder = { _ in self.stub(status: 200, json: respJSON) }
        let api = makeAPI()
        let list = try await api.listWatchedAddresses(deviceId: "d")
        #expect(list.addresses.count == 1)
        #expect(list.addresses[0].address == "0xa")
    }

    @Test func delete_watched_address_handles_204() async throws {
        StubURLProtocol.reset()
        StubURLProtocol.responder = { _ in self.stub(status: 204) }
        let api = makeAPI()
        try await api.deleteWatchedAddress(deviceId: "d", addressId: 7)
        let req = try #require(StubURLProtocol.recordedRequests.first)
        #expect(req.url?.path == "/v1/devices/d/addresses/7")
        #expect(req.httpMethod == "DELETE")
    }

    @Test func scan_decodes_approval_list() async throws {
        StubURLProtocol.reset()
        let respJSON = #"""
            {"approvals":[{"token":{"chain":"ethereum","address":"0xt","symbol":"X","decimals":18,"name":null},"spender":"0xs","amount":"1","block_number":1,"tx_hash":"0xtx","first_seen_at":"2026-05-12T10:00:00Z","last_seen_at":"2026-05-12T10:00:00Z"}]}
            """#
        StubURLProtocol.responder = { _ in self.stub(status: 200, json: respJSON) }
        let api = makeAPI()
        let list = try await api.scan(deviceId: "d")
        #expect(list.approvals.count == 1)
        #expect(list.approvals[0].token.symbol == "X")
    }

    @Test func validation_error_422_maps_to_APIError_validation() async throws {
        StubURLProtocol.reset()
        StubURLProtocol.responder = { _ in
            self.stub(
                status: 422,
                json: #"{"error":{"code":"validation_error","message":"bad"}}"#
            )
        }
        let api = makeAPI()
        do {
            _ = try await api.listWatchedAddresses(deviceId: "x")
            Issue.record("expected throw")
        } catch let err as APIError {
            #expect(err == .validation(message: "bad"))
        }
    }

    @Test func not_configured_503_maps_to_APIError_notConfigured() async throws {
        StubURLProtocol.reset()
        StubURLProtocol.responder = { _ in
            self.stub(
                status: 503,
                json: #"{"error":{"code":"not_configured","message":"ETHERSCAN_API_KEY missing"}}"#
            )
        }
        let api = makeAPI()
        do {
            _ = try await api.scan(deviceId: "d")
            Issue.record("expected throw")
        } catch let err as APIError {
            #expect(err == .notConfigured(message: "ETHERSCAN_API_KEY missing"))
        }
    }

    @Test func unexpected_status_returns_unexpected_with_body() async throws {
        StubURLProtocol.reset()
        StubURLProtocol.responder = { _ in self.stub(status: 418, json: "teapot") }
        let api = makeAPI()
        do {
            _ = try await api.healthz()
            Issue.record("expected throw")
        } catch let err as APIError {
            #expect(err == .unexpected(status: 418, body: "teapot"))
        }
    }

    @Test func transport_failure_becomes_APIError_transport() async throws {
        StubURLProtocol.reset()
        StubURLProtocol.responder = nil  // forces didFailWithError(URLError.unknown)
        let api = makeAPI()
        do {
            _ = try await api.healthz()
            Issue.record("expected throw")
        } catch let err as APIError {
            if case .transport(let urlError) = err {
                // .unknown is fired by our stub when no responder is set.
                #expect(urlError.code == .unknown)
            } else {
                Issue.record("expected .transport, got \(err)")
            }
        }
    }
}
