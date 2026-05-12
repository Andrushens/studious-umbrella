import SwiftUI

struct ApprovalRowView: View {
    let approval: ApprovalDTO

    private var amountDisplay: String {
        if approval.amount == ApprovalsViewModel.unlimitedAmount {
            return "UNLIMITED"
        }
        return approval.amount
    }

    private var amountStyle: HierarchicalShapeStyle {
        approval.amount == ApprovalsViewModel.unlimitedAmount ? .primary : .secondary
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack(alignment: .firstTextBaseline) {
                Text(approval.token.symbol ?? "Unknown token")
                    .font(.headline)
                Spacer()
                Text(amountDisplay)
                    .font(.subheadline.monospaced())
                    .foregroundStyle(amountStyle)
            }
            Text("Spender: \(truncated(approval.spender))")
                .font(.caption.monospaced())
                .foregroundStyle(.secondary)
            HStack(spacing: 12) {
                RevokeLinkButton(wallet: approval.walletAddress)
                    .buttonStyle(.bordered)
                Spacer()
                Text("Block \(approval.blockNumber)")
                    .font(.caption2.monospaced())
                    .foregroundStyle(.tertiary)
            }
        }
        .padding(.vertical, 4)
    }

    private func truncated(_ s: String) -> String {
        guard s.count > 16 else { return s }
        return "\(s.prefix(8))…\(s.suffix(6))"
    }
}
