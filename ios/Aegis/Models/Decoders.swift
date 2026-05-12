import Foundation

public enum AegisDecoders {
    /// Shared JSONDecoder for backend responses (snake_case → camelCase, ISO 8601 dates).
    public static let backend: JSONDecoder = {
        let d = JSONDecoder()
        d.keyDecodingStrategy = .convertFromSnakeCase
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        let fallback = ISO8601DateFormatter()
        fallback.formatOptions = [.withInternetDateTime]

        let naiveFractional = DateFormatter()
        naiveFractional.locale = Locale(identifier: "en_US_POSIX")
        naiveFractional.timeZone = TimeZone(secondsFromGMT: 0)
        naiveFractional.dateFormat = "yyyy-MM-dd'T'HH:mm:ss.SSSSSS"

        let naive = DateFormatter()
        naive.locale = Locale(identifier: "en_US_POSIX")
        naive.timeZone = TimeZone(secondsFromGMT: 0)
        naive.dateFormat = "yyyy-MM-dd'T'HH:mm:ss"

        d.dateDecodingStrategy = .custom { decoder in
            let container = try decoder.singleValueContainer()
            let s = try container.decode(String.self)
            if let date = formatter.date(from: s) {
                return date
            }
            if let date = fallback.date(from: s) {
                return date
            }
            if let date = naiveFractional.date(from: s) {
                return date
            }
            if let date = naive.date(from: s) {
                return date
            }
            throw DecodingError.dataCorruptedError(
                in: container,
                debugDescription: "Invalid ISO 8601 date: \(s)"
            )
        }
        return d
    }()

    /// Shared JSONEncoder for request bodies.
    public static let backendEncoder: JSONEncoder = {
        let e = JSONEncoder()
        e.keyEncodingStrategy = .convertToSnakeCase
        e.dateEncodingStrategy = .iso8601
        return e
    }()
}
