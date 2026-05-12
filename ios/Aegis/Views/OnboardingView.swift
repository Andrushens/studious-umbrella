import SwiftUI

/// Modal sheet for adding a watched wallet address.
struct OnboardingView: View {
    @ObservedObject var viewModel: WatchlistViewModel
    @Environment(\.dismiss) private var dismiss

    @State private var rawAddress: String = ""
    @State private var nickname: String = ""
    @State private var submitting: Bool = false

    private var isAddressLikelyValid: Bool {
        EthAddressValidator.normalize(rawAddress) != nil
    }

    var body: some View {
        NavigationStack {
            Form {
                Section("Wallet address") {
                    TextField("0x…", text: $rawAddress)
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()
                        .font(.body.monospaced())
                    if !rawAddress.isEmpty && !isAddressLikelyValid {
                        Label("Not a valid 0x address", systemImage: "exclamationmark.triangle")
                            .font(.caption)
                            .foregroundStyle(.orange)
                    }
                }
                Section("Nickname (optional)") {
                    TextField("e.g. Vitalik", text: $nickname)
                }
                if let error = viewModel.addError {
                    Section {
                        Label(error, systemImage: "exclamationmark.octagon.fill")
                            .foregroundStyle(.red)
                            .font(.callout)
                    }
                }
            }
            .navigationTitle("Add wallet")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Add") {
                        Task {
                            submitting = true
                            let row = await viewModel.addAddress(rawAddress, nickname: nickname)
                            submitting = false
                            if row != nil { dismiss() }
                        }
                    }
                    .disabled(!isAddressLikelyValid || submitting)
                }
            }
        }
    }
}
