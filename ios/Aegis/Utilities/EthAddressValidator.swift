import Foundation

public enum EthAddressValidator {
    /// Returns the normalized lowercase 0x… address, or nil if invalid.
    public static func normalize(_ raw: String) -> String? {
        let trimmed = raw.trimmingCharacters(in: .whitespacesAndNewlines)
        guard trimmed.hasPrefix("0x") || trimmed.hasPrefix("0X") else { return nil }
        let lowercased = trimmed.lowercased()
        guard lowercased.count == 42 else { return nil }
        let hex = lowercased.dropFirst(2)
        let valid = hex.allSatisfy { c in
            (c >= "0" && c <= "9") || (c >= "a" && c <= "f")
        }
        return valid ? lowercased : nil
    }
}
