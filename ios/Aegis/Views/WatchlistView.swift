import SwiftUI

struct WatchlistView: View {
    @StateObject var viewModel: WatchlistViewModel
    let deviceId: String

    @State private var showingAdd = false
    @EnvironmentObject private var env: AppEnvironment

    var body: some View {
        NavigationStack {
            content
                .navigationTitle("Watchlist")
                .toolbar {
                    ToolbarItem(placement: .primaryAction) {
                        Button {
                            showingAdd = true
                        } label: {
                            Label("Add", systemImage: "plus")
                        }
                    }
                    ToolbarItem(placement: .topBarLeading) {
                        Button {
                            Task { await viewModel.refresh() }
                        } label: {
                            Label("Refresh", systemImage: "arrow.clockwise")
                        }
                    }
                }
                .sheet(isPresented: $showingAdd) {
                    OnboardingView(viewModel: viewModel)
                }
                .task {
                    await viewModel.refresh()
                }
        }
    }

    @ViewBuilder
    private var content: some View {
        switch viewModel.state {
        case .idle, .loading:
            ProgressView()
        case .loaded(let rows):
            if rows.isEmpty {
                emptyState
            } else {
                list(rows: rows)
            }
        case .failed(let message):
            errorState(message: message)
        }
    }

    private var emptyState: some View {
        VStack(spacing: 16) {
            Image(systemName: "wallet.pass")
                .font(.system(size: 48))
                .foregroundStyle(.tint)
            Text("No wallets yet")
                .font(.title3)
            Text("Add a wallet address to watch its approvals.")
                .font(.callout)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
            Button {
                showingAdd = true
            } label: {
                Label("Add wallet", systemImage: "plus")
            }
            .buttonStyle(.borderedProminent)
        }
        .padding()
    }

    private func errorState(message: String) -> some View {
        VStack(spacing: 12) {
            Image(systemName: "exclamationmark.triangle.fill")
                .foregroundStyle(.orange)
                .font(.system(size: 32))
            Text(message)
                .multilineTextAlignment(.center)
                .padding(.horizontal)
            Button("Retry") {
                Task { await viewModel.refresh() }
            }
            .buttonStyle(.bordered)
        }
    }

    private func list(rows: [WatchedAddressDTO]) -> some View {
        List {
            ForEach(rows) { row in
                NavigationLink {
                    ApprovalsView(
                        viewModel: ApprovalsViewModel(
                            api: env.api,
                            deviceId: deviceId,
                            wallet: row.address
                        ),
                        nickname: row.nickname
                    )
                } label: {
                    WatchlistRow(address: row)
                }
                .swipeActions(edge: .trailing) {
                    Button(role: .destructive) {
                        Task { await viewModel.deleteAddress(id: row.id) }
                    } label: {
                        Label("Delete", systemImage: "trash")
                    }
                }
            }
        }
        .refreshable {
            await viewModel.refresh()
        }
    }
}

private struct WatchlistRow: View {
    let address: WatchedAddressDTO

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(address.nickname ?? truncated(address.address))
                .font(.body)
                .lineLimit(1)
            if address.nickname != nil {
                Text(truncated(address.address))
                    .font(.caption.monospaced())
                    .foregroundStyle(.secondary)
                    .lineLimit(1)
            }
        }
        .padding(.vertical, 4)
    }

    private func truncated(_ s: String) -> String {
        guard s.count > 16 else { return s }
        let prefix = s.prefix(8)
        let suffix = s.suffix(6)
        return "\(prefix)…\(suffix)"
    }
}
