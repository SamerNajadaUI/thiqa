import SwiftUI

@main
struct AbuOdehApp: App {
    // الصفحة بتبلّش تتحمّل من أول لحظة، والسبلاش شغّال
    @StateObject private var model: WebModel = {
        let m = WebModel()
        _ = m.makeWebView()
        return m
    }()

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(model)
                .preferredColorScheme(.light)
        }
    }
}
