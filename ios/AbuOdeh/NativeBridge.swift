import UIKit
import WebKit
import Speech
import AVFoundation

/// جسر بين الموقع والتطبيق:
/// - haptic: اهتزاز خفيف للصح ("success") والغلط ("error")
/// - speech: التعرّف على الكلام من التلفون نفسه، والنتيجة بترجع للصفحة على window.__speech
final class NativeBridge: NSObject, WKScriptMessageHandler {
    weak var webView: WKWebView?

    private let engine = AVAudioEngine()
    private var request: SFSpeechAudioBufferRecognitionRequest?
    private var task: SFSpeechRecognitionTask?
    private var silence: Timer?
    private var finished = false

    func userContentController(_ controller: WKUserContentController, didReceive message: WKScriptMessage) {
        switch message.name {
        case "haptic":
            let kind = message.body as? String ?? "success"
            let gen = UINotificationFeedbackGenerator()
            gen.notificationOccurred(kind == "error" ? .error : .success)
        case "speech":
            guard let body = message.body as? [String: Any], let cmd = body["cmd"] as? String else { return }
            if cmd == "start" { start(lang: body["lang"] as? String ?? "ar-JO") } else { finishAudio() }
        default: break
        }
    }

    // MARK: - الكلام

    private func start(lang: String) {
        cleanup()
        SFSpeechRecognizer.requestAuthorization { status in
            DispatchQueue.main.async {
                guard status == .authorized else { return self.emit(["type": "error", "error": "not-allowed"]) }
                AVAudioSession.sharedInstance().requestRecordPermission { ok in
                    DispatchQueue.main.async { ok ? self.begin(lang) : self.emit(["type": "error", "error": "not-allowed"]) }
                }
            }
        }
    }

    private func begin(_ lang: String) {
        guard let recognizer = SFSpeechRecognizer(locale: Locale(identifier: lang)), recognizer.isAvailable else {
            return emit(["type": "error", "error": "unavailable"])
        }
        do {
            let session = AVAudioSession.sharedInstance()
            try session.setCategory(.playAndRecord, mode: .measurement, options: [.duckOthers, .defaultToSpeaker])
            try session.setActive(true, options: .notifyOthersOnDeactivation)

            let req = SFSpeechAudioBufferRecognitionRequest()
            req.shouldReportPartialResults = true
            request = req
            finished = false

            let input = engine.inputNode
            let format = input.outputFormat(forBus: 0)
            input.removeTap(onBus: 0)
            input.installTap(onBus: 0, bufferSize: 1024, format: format) { buffer, _ in req.append(buffer) }
            engine.prepare()
            try engine.start()

            task = recognizer.recognitionTask(with: req) { [weak self] result, error in
                guard let self = self else { return }
                if let result = result {
                    let alts = result.transcriptions.prefix(5).map { $0.formattedString }
                    self.emit(["type": result.isFinal ? "final" : "partial", "alts": Array(alts)])
                    if result.isFinal { self.done() } else { self.armSilence(1.4) }
                } else if error != nil {
                    self.done()
                }
            }
            emit(["type": "listening"])
            armSilence(6)   // إذا ما حكى إشي خلال 6 ثواني بنسكّر
        } catch {
            emit(["type": "error", "error": "audio"])
            cleanup()
        }
    }

    // بعد سكوت قصير بنوقف التسجيل، والتعرّف بيعطي النتيجة النهائية
    private func armSilence(_ seconds: TimeInterval) {
        silence?.invalidate()
        silence = Timer.scheduledTimer(withTimeInterval: seconds, repeats: false) { [weak self] _ in self?.finishAudio() }
    }

    private func finishAudio() {
        silence?.invalidate()
        if engine.isRunning { engine.stop(); engine.inputNode.removeTap(onBus: 0) }
        request?.endAudio()
        // إذا ما إجت نتيجة نهائية خلال ثانيتين بنسكّر
        DispatchQueue.main.asyncAfter(deadline: .now() + 2) { [weak self] in self?.done() }
    }

    private func done() {
        guard !finished else { return }
        finished = true
        cleanup()
        emit(["type": "end"])
    }

    private func cleanup() {
        silence?.invalidate()
        if engine.isRunning { engine.stop() }
        engine.inputNode.removeTap(onBus: 0)
        task?.cancel(); task = nil
        request = nil
        try? AVAudioSession.sharedInstance().setCategory(.ambient)
        try? AVAudioSession.sharedInstance().setActive(false, options: .notifyOthersOnDeactivation)
    }

    private func emit(_ payload: [String: Any]) {
        guard let data = try? JSONSerialization.data(withJSONObject: payload),
              let json = String(data: data, encoding: .utf8) else { return }
        DispatchQueue.main.async {
            self.webView?.evaluateJavaScript("window.__speech && window.__speech(\(json))", completionHandler: nil)
        }
    }
}

/// عشان ما يصير تعلّق بالذاكرة بين الصفحة والجسر
final class WeakHandler: NSObject, WKScriptMessageHandler {
    weak var target: WKScriptMessageHandler?
    init(_ target: WKScriptMessageHandler) { self.target = target }
    func userContentController(_ c: WKUserContentController, didReceive m: WKScriptMessage) {
        target?.userContentController(c, didReceive: m)
    }
}
