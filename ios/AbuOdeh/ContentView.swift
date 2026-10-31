import SwiftUI
import WebKit

let siteURL = URL(string: "https://samernajadaui.github.io/thiqa/?source=ios")!

struct ContentView: View {
    @EnvironmentObject private var model: WebModel
    @State private var splashDone = false

    var body: some View {
        ZStack {
            Color.white.ignoresSafeArea()
            WebView(model: model)
                .ignoresSafeArea()

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
                .environment(\.layoutDirection, .rightToLeft)
            }

            if !splashDone {
                SplashView()
                    .transition(.opacity.combined(with: .scale(scale: 1.08)))
                    .zIndex(2)
            }
        }
        .onChange(of: model.loaded) { done in if done { hideSplash() } }
        .onChange(of: model.failed) { failed in if failed { hideSplash() } }
        .task {
            // ما بنخلي السبلاش أكثر من 3 ثواني حتى لو النت بطيء
            try? await Task.sleep(nanoseconds: 3_000_000_000)
            hideSplash()
        }
    }

    private func hideSplash() {
        guard !splashDone else { return }
        // أقل إشي ثانية وحدة عشان الحركة تبيّن
        let wait = max(0, 1.0 - Date().timeIntervalSince(model.startedAt))
        DispatchQueue.main.asyncAfter(deadline: .now() + wait) {
            withAnimation(.easeOut(duration: 0.35)) { splashDone = true }
        }
    }
}

// شاشة البداية: اللوغو بينط، والاسم بيطلع تحته، والخلفية بنفسجية متدرجة
struct SplashView: View {
    @State private var pop = false
    @State private var showText = false
    @State private var spin = false

    var body: some View {
        ZStack {
            LinearGradient(colors: [Color(red: 0.42, green: 0.30, blue: 0.98), Color(red: 0.30, green: 0.18, blue: 0.85)],
                           startPoint: .top, endPoint: .bottom)
                .ignoresSafeArea()
            Circle().fill(Color.white.opacity(0.08)).frame(width: 420).offset(x: -150, y: -320)
            Circle().fill(Color.white.opacity(0.06)).frame(width: 300).offset(x: 170, y: 330)

            VStack(spacing: 18) {
                Image("LaunchLogo").resizable().frame(width: 128, height: 128)
                    .clipShape(RoundedRectangle(cornerRadius: 32, style: .continuous))
                    .shadow(color: .black.opacity(0.25), radius: 18, y: 10)
                    .scaleEffect(pop ? 1 : 0.4)
                    .rotationEffect(.degrees(spin ? 0 : -18))
                    .opacity(pop ? 1 : 0)
                VStack(spacing: 6) {
                    Text("أبو عودة").font(.system(size: 40, weight: .black, design: .rounded))
                    Text("للمرح").font(.system(size: 22, weight: .bold, design: .rounded)).opacity(0.85)
                }
                .foregroundStyle(.white)
                .opacity(showText ? 1 : 0)
                .offset(y: showText ? 0 : 14)
            }
        }
        .onAppear {
            withAnimation(.spring(response: 0.55, dampingFraction: 0.55)) { pop = true; spin = true }
            withAnimation(.easeOut(duration: 0.45).delay(0.25)) { showText = true }
        }
    }
}

final class WebModel: NSObject, ObservableObject, WKNavigationDelegate {
    @Published var loaded = false
    @Published var failed = false
    let startedAt = Date()
    weak var webView: WKWebView?

    func reload() {
        failed = false
        webView?.load(URLRequest(url: siteURL, cachePolicy: .returnCacheDataElseLoad))
    }

    // بنشيل السبلاش أول ما الصفحة تبلّش ترسم، مش لما كل الصور تخلص
    func webView(_ webView: WKWebView, didCommit navigation: WKNavigation!) {
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.25) { self.loaded = true }
    }

    func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) {
        loaded = true
        failed = false
        webView.scrollView.refreshControl?.endRefreshing()
    }

    func webView(_ webView: WKWebView, didFail navigation: WKNavigation!, withError error: Error) { fail(webView, error) }
    func webView(_ webView: WKWebView, didFailProvisionalNavigation navigation: WKNavigation!, withError error: Error) { fail(webView, error) }

    private func fail(_ webView: WKWebView, _ error: Error) {
        webView.scrollView.refreshControl?.endRefreshing()
        if (error as NSError).code == NSURLErrorCancelled { return }
        // إذا ما في نت، جرّب النسخة المحفوظة قبل ما نطلّع شاشة "ما في نت"
        if !loaded {
            if !triedCache {
                triedCache = true
                webView.load(URLRequest(url: siteURL, cachePolicy: .returnCacheDataDontLoad))
            } else {
                failed = true
            }
        }
    }
    private var triedCache = false

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

    // بنجهّز الصفحة من أول ما يفتح التطبيق، قبل ما الواجهة تنرسم
    func makeWebView() -> WKWebView {
        if let web = webView { return web }
        let config = WKWebViewConfiguration()
        config.websiteDataStore = .default()
        config.applicationNameForUserAgent = "AbuOdehApp/1.0"
        config.allowsInlineMediaPlayback = true
        config.suppressesIncrementalRendering = false
        let web = WKWebView(frame: UIScreen.main.bounds, configuration: config)
        web.navigationDelegate = self
        web.isOpaque = false
        web.backgroundColor = .white
        web.scrollView.backgroundColor = .white
        web.scrollView.contentInsetAdjustmentBehavior = .never
        // رجوع بالسحب من طرف الشاشة اليسار (ولقدّام من اليمين)
        web.allowsBackForwardNavigationGestures = true
        web.semanticContentAttribute = .forceLeftToRight
        let refresh = UIRefreshControl()
        refresh.addTarget(self, action: #selector(WebModel.refresh), for: .valueChanged)
        web.scrollView.refreshControl = refresh
        webView = web
        web.load(URLRequest(url: siteURL, cachePolicy: .useProtocolCachePolicy, timeoutInterval: 20))
        return web
    }
}

struct WebView: UIViewRepresentable {
    @ObservedObject var model: WebModel

    func makeUIView(context: Context) -> WKWebView { model.makeWebView() }
    func updateUIView(_ uiView: WKWebView, context: Context) {}
}
