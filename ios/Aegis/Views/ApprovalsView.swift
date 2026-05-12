import SwiftUI

struct ApprovalsView: View {
    @StateObject var viewModel: ApprovalsViewModel
    let wallet: String
    let nickname: String?

    var body: some View {
        VStack(spacing: 0) {
            content
        }
        .navigationTitle(nickname ?? truncated(wallet))
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .primaryAction) {
                Button {
                    Task { await viewModel.scan() }
                } label: {
                    Label("Scan now", systemImage: "magnifyingglass.circle")
                }
            }
        }
        .task {
            if case .idle = viewModel.state {
                await viewModel.scan()
            }
        }
    }

    @ViewBuilder
    private var content: some View {
        switch viewModel.state {
        case .idle:
            placeholderText("Tap Scan now to fetch approvals.")
        case .scanning:
            VStack(spacing: 12) {
                ProgressView()
                Text("Scanning…")
                    .foregroundStyle(.secondary)
            }
        case .loaded:
            loadedList
        case .failed(let message):
            VStack(spacing: 12) {
                Image(systemName: "exclamationmark.triangle.fill")
                    .foregroundStyle(.orange)
                    .font(.system(size: 32))
                Text(message)
                    .multilineTextAlignment(.center)
                    .padding(.horizontal)
                Button("Retry") {
                    Task { await viewModel.scan() }
                }
                .buttonStyle(.bordered)
            }
            .padding()
        }
    }

    private var loadedList: some View {
        List {
            Section {
                Toggle("Unlimited approvals only", isOn: $viewModel.unlimitedOnly)
            }
            if viewModel.visibleApprovals.isEmpty {
                Section {
                    Text("No approvals match the current filter.")
                        .foregroundStyle(.secondary)
                }
            } else {
                Section("Approvals") {
                    ForEach(viewModel.visibleApprovals) { ap in
                        ApprovalRowView(approval: ap, wallet: wallet)
                    }
                }
            }
        }
        .refreshable {
            await viewModel.scan()
        }
    }

    private func placeholderText(_ s: String) -> some View {
        VStack {
            Text(s)
                .foregroundStyle(.secondary)
                .padding()
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    private func truncated(_ s: String) -> String {
        guard s.count > 16 else { return s }
        return "\(s.prefix(6))…\(s.suffix(4))"
    }
}
