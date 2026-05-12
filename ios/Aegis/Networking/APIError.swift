import Foundation

public enum APIError: Error, Equatable, Sendable {
    case validation(message: String)
    case notFound(message: String)
    case notConfigured(message: String)
    case upstreamRateLimited(message: String)
    case upstreamEtherscan(message: String)
    case upstreamAlchemy(message: String)
    case server(code: String, message: String, status: Int)
    case transport(URLError)
    case decoding(message: String)
    case unexpected(status: Int, body: String?)

    public static func == (lhs: APIError, rhs: APIError) -> Bool {
        switch (lhs, rhs) {
        case (.validation(let a), .validation(let b)): return a == b
        case (.notFound(let a), .notFound(let b)): return a == b
        case (.notConfigured(let a), .notConfigured(let b)): return a == b
        case (.upstreamRateLimited(let a), .upstreamRateLimited(let b)): return a == b
        case (.upstreamEtherscan(let a), .upstreamEtherscan(let b)): return a == b
        case (.upstreamAlchemy(let a), .upstreamAlchemy(let b)): return a == b
        case (.server(let c1, let m1, let s1), .server(let c2, let m2, let s2)):
            return c1 == c2 && m1 == m2 && s1 == s2
        case (.transport(let a), .transport(let b)): return a.code == b.code
        case (.decoding(let a), .decoding(let b)): return a == b
        case (.unexpected(let s1, let b1), .unexpected(let s2, let b2)):
            return s1 == s2 && b1 == b2
        default: return false
        }
    }
}

extension APIError: LocalizedError {
    public var errorDescription: String? {
        switch self {
        case .validation(let m): return m
        case .notFound(let m): return m
        case .notConfigured(let m): return m
        case .upstreamRateLimited(let m): return "Upstream rate limited: \(m)"
        case .upstreamEtherscan(let m): return "Etherscan error: \(m)"
        case .upstreamAlchemy(let m): return "Alchemy error: \(m)"
        case .server(let code, let m, _): return "\(code): \(m)"
        case .transport(let err): return err.localizedDescription
        case .decoding(let m): return "Decoding error: \(m)"
        case .unexpected(let status, let body):
            if let body, !body.isEmpty {
                return "Unexpected response (HTTP \(status)): \(body)"
            }
            return "Unexpected response (HTTP \(status))"
        }
    }
}

/// Parses the backend's `{error:{code,message,details?}}` envelope.
public enum APIErrorEnvelope {
    public static func from(data: Data, status: Int) -> APIError {
        guard
            let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
            let err = json["error"] as? [String: Any],
            let code = err["code"] as? String,
            let message = err["message"] as? String
        else {
            let body = String(data: data, encoding: .utf8)
            return .unexpected(status: status, body: body)
        }
        switch code {
        case "invalid_address", "validation_error":
            return .validation(message: message)
        case "not_found":
            return .notFound(message: message)
        case "not_configured":
            return .notConfigured(message: message)
        case "upstream_rate_limited":
            return .upstreamRateLimited(message: message)
        case "upstream_etherscan":
            return .upstreamEtherscan(message: message)
        case "upstream_alchemy":
            return .upstreamAlchemy(message: message)
        default:
            return .server(code: code, message: message, status: status)
        }
    }
}
