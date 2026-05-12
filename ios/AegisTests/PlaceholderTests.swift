import Testing
@testable import Aegis

@Test func placeholder_version_is_semver_prefix() {
    #expect(AegisPlaceholder.version.hasPrefix("0."))
}
