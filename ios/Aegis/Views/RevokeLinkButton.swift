import SwiftUI

/// Opens revoke.cash for the given wallet address. Mainnet only (chainId=1) for week 1.
struct RevokeLinkButton: View {
    let wallet: String
    @Environment(\.openURL) private var openURL

    var body: some View {
        Button {
            guard let url = url else { return }
            openURL(url)
        } label: {
            Label("Revoke", systemImage: "arrow.up.right.square")
        }
        .disabled(url == nil)
    }

    private var url: URL? {
        var components = URLComponents()
        components.scheme = "https"
        components.host = "revoke.cash"
        components.path = "/address/\(wallet)"
        components.queryItems = [URLQueryItem(name: "chainId", value: "1")]
        return components.url
    }
}
