import Foundation

public protocol AegisAPIClient: Sendable {
    func healthz() async throws -> HealthResponse
    func registerDevice(_ body: RegisterDeviceBody) async throws -> DeviceDTO
    func addWatchedAddress(
        deviceId: String, body: AddWatchedAddressBody
    ) async throws -> WatchedAddressDTO
    func listWatchedAddresses(deviceId: String) async throws -> WatchedAddressList
    func deleteWatchedAddress(deviceId: String, addressId: Int) async throws
    func scan(deviceId: String) async throws -> ApprovalList
}

public struct HealthResponse: Codable, Equatable, Sendable {
    public let status: String
}

public struct RegisterDeviceBody: Codable, Equatable, Sendable {
    public let deviceId: String
    public let pushToken: String?
    public let tier: String?

    public init(deviceId: String, pushToken: String? = nil, tier: String? = nil) {
        self.deviceId = deviceId
        self.pushToken = pushToken
        self.tier = tier
    }
}

public struct AddWatchedAddressBody: Codable, Equatable, Sendable {
    public let address: String
    public let chain: String?
    public let nickname: String?

    public init(address: String, chain: String? = "ethereum", nickname: String? = nil) {
        self.address = address
        self.chain = chain
        self.nickname = nickname
    }
}

public actor AegisAPI: AegisAPIClient {
    private let baseURL: URL
    private let session: URLSession
    private let decoder: JSONDecoder
    private let encoder: JSONEncoder

    public init(
        baseURL: URL,
        session: URLSession = .shared,
        decoder: JSONDecoder = AegisDecoders.backend,
        encoder: JSONEncoder = AegisDecoders.backendEncoder
    ) {
        self.baseURL = baseURL
        self.session = session
        self.decoder = decoder
        self.encoder = encoder
    }

    public convenience init(
        provider: BaseURLProviding,
        session: URLSession = .shared
    ) {
        self.init(baseURL: provider.baseURL, session: session)
    }

    // MARK: - Endpoints

    public func healthz() async throws -> HealthResponse {
        try await request(.get, path: "/v1/healthz", expecting: [200])
    }

    public func registerDevice(_ body: RegisterDeviceBody) async throws -> DeviceDTO {
        try await request(.post, path: "/v1/devices", body: body, expecting: [201])
    }

    public func addWatchedAddress(
        deviceId: String, body: AddWatchedAddressBody
    ) async throws -> WatchedAddressDTO {
        try await request(
            .post,
            path: "/v1/devices/\(percentEncoded(deviceId))/addresses",
            body: body,
            expecting: [201]
        )
    }

    public func listWatchedAddresses(deviceId: String) async throws -> WatchedAddressList {
        try await request(
            .get,
            path: "/v1/devices/\(percentEncoded(deviceId))/addresses",
            expecting: [200]
        )
    }

    public func deleteWatchedAddress(deviceId: String, addressId: Int) async throws {
        _ = try await requestVoid(
            .delete,
            path: "/v1/devices/\(percentEncoded(deviceId))/addresses/\(addressId)",
            expecting: [204]
        )
    }

    public func scan(deviceId: String) async throws -> ApprovalList {
        try await request(
            .post,
            path: "/v1/devices/\(percentEncoded(deviceId))/scan",
            expecting: [200]
        )
    }

    // MARK: - Internals

    private enum HTTPMethod: String {
        case get = "GET"
        case post = "POST"
        case delete = "DELETE"
    }

    private func percentEncoded(_ s: String) -> String {
        s.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed) ?? s
    }

    private func makeURL(path: String) -> URL {
        baseURL.appendingPathComponent(path.trimmingCharacters(in: CharacterSet(charactersIn: "/")))
    }

    private func makeRequest<B: Encodable>(
        _ method: HTTPMethod, path: String, body: B?
    ) throws -> URLRequest {
        var req = URLRequest(url: makeURL(path: path))
        req.httpMethod = method.rawValue
        req.setValue("application/json", forHTTPHeaderField: "Accept")
        if let body {
            req.setValue("application/json", forHTTPHeaderField: "Content-Type")
            req.httpBody = try encoder.encode(body)
        }
        return req
    }

    private func perform(_ req: URLRequest) async throws -> (Data, HTTPURLResponse) {
        do {
            let (data, response) = try await session.data(for: req)
            guard let http = response as? HTTPURLResponse else {
                throw APIError.unexpected(status: -1, body: nil)
            }
            return (data, http)
        } catch let urlError as URLError {
            throw APIError.transport(urlError)
        } catch let apiError as APIError {
            throw apiError
        } catch {
            throw APIError.unexpected(status: -1, body: error.localizedDescription)
        }
    }

    private func request<R: Decodable>(
        _ method: HTTPMethod,
        path: String,
        expecting okStatuses: Set<Int>
    ) async throws -> R {
        let req = try makeRequest(method, path: path, body: nil as Empty?)
        let (data, http) = try await perform(req)
        try validate(status: http.statusCode, data: data, expecting: okStatuses)
        return try decode(R.self, from: data)
    }

    private func request<B: Encodable, R: Decodable>(
        _ method: HTTPMethod,
        path: String,
        body: B,
        expecting okStatuses: Set<Int>
    ) async throws -> R {
        let req = try makeRequest(method, path: path, body: body)
        let (data, http) = try await perform(req)
        try validate(status: http.statusCode, data: data, expecting: okStatuses)
        return try decode(R.self, from: data)
    }

    private func requestVoid(
        _ method: HTTPMethod, path: String, expecting okStatuses: Set<Int>
    ) async throws -> Void {
        let req = try makeRequest(method, path: path, body: nil as Empty?)
        let (data, http) = try await perform(req)
        try validate(status: http.statusCode, data: data, expecting: okStatuses)
    }

    private func validate(status: Int, data: Data, expecting okStatuses: Set<Int>) throws {
        if okStatuses.contains(status) { return }
        throw APIErrorEnvelope.from(data: data, status: status)
    }

    private func decode<R: Decodable>(_ type: R.Type, from data: Data) throws -> R {
        do {
            return try decoder.decode(R.self, from: data)
        } catch {
            throw APIError.decoding(message: String(describing: error))
        }
    }
}

/// Helper sentinel for the no-body GET / DELETE cases.
private struct Empty: Encodable {}
