import Foundation

@MainActor
public final class WatchlistViewModel: ObservableObject {
    public enum State: Equatable {
        case idle
        case loading
        case loaded([WatchedAddressDTO])
        case failed(String)
    }

    @Published public private(set) var state: State = .idle
    @Published public private(set) var addError: String?

    private let api: AegisAPIClient
    private let deviceId: String

    public init(api: AegisAPIClient, deviceId: String) {
        self.api = api
        self.deviceId = deviceId
    }

    public func refresh() async {
        state = .loading
        do {
            let list = try await api.listWatchedAddresses(deviceId: deviceId)
            state = .loaded(list.addresses)
        } catch let err as APIError {
            state = .failed(err.localizedDescription)
        } catch {
            state = .failed(error.localizedDescription)
        }
    }

    /// Returns the inserted/updated row on success. Sets `addError` on validation failure.
    @discardableResult
    public func addAddress(_ raw: String, nickname: String? = nil) async -> WatchedAddressDTO? {
        guard let normalized = EthAddressValidator.normalize(raw) else {
            addError = "Not a valid 0x… address"
            return nil
        }
        addError = nil
        let cleanedNickname: String? = {
            guard let nickname else { return nil }
            let trimmed = nickname.trimmingCharacters(in: .whitespacesAndNewlines)
            return trimmed.isEmpty ? nil : trimmed
        }()
        do {
            let row = try await api.addWatchedAddress(
                deviceId: deviceId,
                body: .init(address: normalized, chain: "ethereum", nickname: cleanedNickname)
            )
            // Optimistically merge into state if currently loaded.
            if case .loaded(var rows) = state {
                if let idx = rows.firstIndex(where: { $0.id == row.id }) {
                    rows[idx] = row
                } else {
                    rows.append(row)
                }
                state = .loaded(rows)
            }
            return row
        } catch let err as APIError {
            addError = err.localizedDescription
            return nil
        } catch {
            addError = error.localizedDescription
            return nil
        }
    }

    public func deleteAddress(id: Int) async {
        let previous = state
        if case .loaded(var rows) = state {
            rows.removeAll { $0.id == id }
            state = .loaded(rows)
        }
        do {
            try await api.deleteWatchedAddress(deviceId: deviceId, addressId: id)
        } catch {
            // Roll back the optimistic delete on failure.
            state = previous
            addError = (error as? APIError)?.localizedDescription ?? error.localizedDescription
        }
    }
}
