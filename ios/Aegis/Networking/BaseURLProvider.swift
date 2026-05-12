import Foundation

public protocol BaseURLProviding: Sendable {
    var baseURL: URL { get }
}

/// Reads `API_BASE_URL` from the main bundle's Info.plist. The plist key is set
/// by `Configs/Debug.xcconfig` (or Release) at build time.
public struct BundleBaseURLProvider: BaseURLProviding {
    public let baseURL: URL

    public init(bundle: Bundle = .main) throws {
        guard
            let value = bundle.object(forInfoDictionaryKey: "API_BASE_URL") as? String,
            !value.isEmpty,
            let url = URL(string: value)
        else {
            throw BaseURLError.missingOrInvalid
        }
        self.baseURL = url
    }
}

/// Test-only provider that wraps a known URL.
public struct StaticBaseURLProvider: BaseURLProviding {
    public let baseURL: URL
    public init(_ url: URL) { self.baseURL = url }
}

public enum BaseURLError: Error, Equatable {
    case missingOrInvalid
}
