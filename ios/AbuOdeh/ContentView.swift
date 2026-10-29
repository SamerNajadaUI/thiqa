import SwiftUI
import WebKit

let siteURL = URL(string: "https://samernajadaui.github.io/thiqa/?source=ios")!

struct ContentView: View {
    @StateObject private var model = WebModel()

    var body: some View {
        ZStack {
            Color.white.ignoresSafeArea()
            WebView(model: model)
                .ignoresSafeArea()
                .opacity(model.loaded ? 1 : 0)

            if !model.loaded && !model.failed {
                VStack(spacing: 16) {
                    Image("LaunchLogo").resizable().frame(width: 96, height: 96)
                        .clipShape(RoundedRectangle(cornerRadius: 24, style: .continuous))
                    ProgressView()
                }
            }

            if model.failed {
                VStack(spacing: 14) {
                    Image("LaunchLogo").resizable().frame(width: 80, height: 80)
                        .clipShape(RoundedRectangle(cornerRadius: 20, style: .continuous))
                    Text("ما في نت").font(.title2.bold())
                    Text("تأكد من الاتصال وجرّب كمان مرة.").foregroundStyle(.secondary)
                    Button("جرّب كمان مرة") { model.reload() }
                        .buttonStyle(.borderedProminent)
                        .tint(Color(red: 0.36, green: 0.24, blue: 0.96))
                }
                .padding()
            }
        }
        .environment(\.layoutDirection, .rightToLeft)
    }
}

final class WebModel: NSObject, ObservableObject, WKNavigationDelegate {
    @Published var loaded = false
    @Published var failed = false
    weak var webView: WKWebView?

    func reload() {
        failed = false
        webView?.load(URLRequest(url: siteURL, cachePolicy: .returnCacheDataElseLoad))
    }

    func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) {
        loaded = true
        failed = false
        webView.scrollView.refreshControl?.endRefreshing()
    }

    func webView(_ webView: WKWebView, didFail navigation: WKNavigation!, withError error: Error) { fail(webView) }
    func webView(_ webView: WKWebView, didFailProvisionalNavigation navigation: WKNavigation!, withError error: Error) { fail(webView) }

    private func fail(_ webView: WKWebView) {
        webView.scrollView.refreshControl?.endRefreshing()
        if !loaded { failed = true }
    }

    // الروابط اللي برّا الموقع بتفتح بـSafari
    func webView(_ webView: WKWebView, decidePolicyFor action: WKNavigationAction,
                 decisionHandler: @escaping (WKNavigationActionPolicy) -> Void) {
        if let url = action.request.url, action.navigationType == .linkActivated,
           url.host != siteURL.host {
            UIApplication.shared.open(url)
            decisionHandler(.cancel)
            return
        }
        decisionHandler(.allow)
    }

    @objc func refresh() { webView?.reload() }
}

struct WebView: UIViewRepresentable {
    @ObservedObject var model: WebModel

    func makeUIView(context: Context) -> WKWebView {
        let config = WKWebViewConfiguration()
        config.websiteDataStore = .default()
        config.applicationNameForUserAgent = "AbuOdehApp/1.0"
        let web = WKWebView(frame: .zero, configuration: config)
        web.navigationDelegate = model
        web.isOpaque = false
        web.backgroundColor = .white
        web.scrollView.backgroundColor = .white
        web.scrollView.contentInsetAdjustmentBehavior = .never
        web.allowsBackForwardNavigationGestures = false
        let refresh = UIRefreshControl()
        refresh.addTarget(model, action: #selector(WebModel.refresh), for: .valueChanged)
        web.scrollView.refreshControl = refresh
        model.webView = web
        web.load(URLRequest(url: siteURL))
        return web
    }

    func updateUIView(_ uiView: WKWebView, context: Context) {}
}
