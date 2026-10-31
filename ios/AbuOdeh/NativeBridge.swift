import UIKit
import WebKit
import Speech
import AVFoundation

/// جسر بين الموقع والتطبيق:
/// - haptic: اهتزاز للصح ("success") والغلط ("error")
/// - speech: التعرّف على الكلام من التلفون نفسه:
///   * بيسمع بالعربي والإنجليزي بنفس اللحظة (نفس الصوت لاثنين)، وبيرجّع احتمالات الاثنين
///   * بياخذ من الصفحة أسماء اللاعبين المتوقعة (contextualStrings) عشان يميل إلها
///   * بيبعت قوة الصوت للصفحة عشان موجة الصوت، وبيوقف لحاله لما تسكت
///   النتائج بترجع للصفحة على window.__speech
final class NativeBridge: NSObject, WKScriptMessageHandler {
    weak var webView: WKWebView?

    private let engine = AVAudioEngine()
    private struct Lane {
        let recognizer: SFSpeechRecognizer
        let request: SFSpeechAudioBufferRecognitionRequest
        var task: SFSpeechRecognitionTask?
        var alts: [String] = []
        var finished = false
    }
    private var lanes: [Lane] = []
    private var silence: Timer?
    private var hardStop: Timer?
    private var ended = true
    private var lastLevel = Date.distantPast
    private var heardSomething = false

    func userContentController(_ controller: WKUserContentController, didReceive message: WKScriptMessage) {
        switch message.name {
        case "haptic":
            let kind = message.body as? String ?? "success"
            UINotificationFeedbackGenerator().notificationOccurred(kind == "error" ? .error : .success)
        case "speech":
            guard let body = message.body as? [String: Any], let cmd = body["cmd"] as? String else { return }
            if cmd == "start" {
                let langs = [body["lang"] as? String ?? "ar-JO", body["also"] as? String].compactMap { $0 }
                let hints = (body["hints"] as? [String] ?? []).prefix(100).map { $0 }
                start(langs: langs, hints: Array(hints))
            } else {
                finishAudio()
            }
        default: break
        }
    }

    // MARK: - البداية

    private func start(langs: [String], hints: [String]) {
        cleanup(emitEnd: false)
        SFSpeechRecognizer.requestAuthorization { status in
            DispatchQueue.main.async {
                guard status == .authorized else { return self.emit(["type": "error", "error": "not-allowed"]) }
                AVAudioSession.sharedInstance().requestRecordPermission { ok in
                    DispatchQueue.main.async { ok ? self.begin(langs, hints) : self.emit(["type": "error", "error": "not-allowed"]) }
                }
            }
        }
    }

    /// أول لغة مدعومة من القائمة (مثلاً ar-JO إذا موجودة، وإلا ar-SA)
    private func recognizer(for lang: String) -> SFSpeechRecognizer? {
        let candidates: [String]
        if lang.hasPrefix("ar") { candidates = [lang, "ar-JO", "ar-SA", "ar-AE", "ar-KW", "ar-QA"] }
        else { candidates = [lang, "en-US", "en-GB"] }
        for id in candidates {
            if let r = SFSpeechRecognizer(locale: Locale(identifier: id)), r.isAvailable { return r }
        }
        return nil
    }

    private func begin(_ langs: [String], _ hints: [String]) {
        let recognizers = langs.compactMap { recognizer(for: $0) }
        guard !recognizers.isEmpty else { return emit(["type": "error", "error": "unavailable"]) }
        do {
            let session = AVAudioSession.sharedInstance()
            try session.setCategory(.playAndRecord, mode: .measurement, options: [.duckOthers, .defaultToSpeaker])
            try session.setActive(true, options: .notifyOthersOnDeactivation)

            ended = false
            heardSomething = false
            lanes = recognizers.map { r in
                let req = SFSpeechAudioBufferRecognitionRequest()
                req.shouldReportPartialResults = true
                req.taskHint = .search
                req.contextualStrings = hints
                if #available(iOS 16, *) { req.addsPunctuation = false }
                return Lane(recognizer: r, request: req)
            }

            let input = engine.inputNode
            let format = input.outputFormat(forBus: 0)
            input.removeTap(onBus: 0)
            let requests = lanes.map { $0.request }
            input.installTap(onBus: 0, bufferSize: 1024, format: format) { [weak self] buffer, _ in
                for r in requests { r.append(buffer) }
                self?.reportLevel(buffer)
            }
            engine.prepare()
            try engine.start()

            for k in lanes.indices {
                let lane = lanes[k]
                lanes[k].task = lane.recognizer.recognitionTask(with: lane.request) { [weak self] result, error in
                    DispatchQueue.main.async { self?.handle(lane: k, result: result, error: error) }
                }
            }
            UIImpactFeedbackGenerator(style: .light).impactOccurred()
            emit(["type": "listening"])
            armSilence(6)   // إذا ما حكى إشي خلال 6 ثواني بنسكّر
            hardStop?.invalidate()
            hardStop = Timer.scheduledTimer(withTimeInterval: 12, repeats: false) { [weak self] _ in self?.finishAudio() }
        } catch {
            emit(["type": "error", "error": "audio"])
            cleanup(emitEnd: false)
        }
    }

    // MARK: - النتائج

    private func handle(lane k: Int, result: SFSpeechRecognitionResult?, error: Error?) {
        guard k < lanes.count, !ended else { return }
        if let result = result {
            let alts = result.transcriptions.prefix(5).map { $0.formattedString }.filter { !$0.isEmpty }
            if !alts.isEmpty { lanes[k].alts = Array(alts); heardSomething = true }
            emit(["type": "partial", "alts": merged()])
            if result.isFinal { lanes[k].finished = true } else { armSilence(1.3) }
        } else if error != nil {
            lanes[k].finished = true
        }
        if lanes.allSatisfy({ $0.finished }) { done() }
    }

    /// احتمالات العربي أول، بعدين الإنجليزي (بدون تكرار)
    private func merged() -> [String] {
        var seen = Set<String>(), out: [String] = []
        let maxLen = lanes.map { $0.alts.count }.max() ?? 0
        for i in 0..<maxLen {
            for lane in lanes where i < lane.alts.count {
                let a = lane.alts[i]
                if seen.insert(a.lowercased()).inserted { out.append(a) }
            }
        }
        return out
    }

    // MARK: - الإيقاف

    private func armSilence(_ seconds: TimeInterval) {
        silence?.invalidate()
        silence = Timer.scheduledTimer(withTimeInterval: seconds, repeats: false) { [weak self] _ in self?.finishAudio() }
    }

    /// بنوقف التسجيل، والتعرّف بيعطي النتيجة النهائية خلال لحظات
    private func finishAudio() {
        guard !ended else { return }
        silence?.invalidate(); hardStop?.invalidate()
        if engine.isRunning { engine.stop(); engine.inputNode.removeTap(onBus: 0) }
        for lane in lanes { lane.request.endAudio() }
        UIImpactFeedbackGenerator(style: .soft).impactOccurred()
        DispatchQueue.main.asyncAfter(deadline: .now() + 1.6) { [weak self] in self?.done() }
    }

    private func done() {
        guard !ended else { return }
        let alts = merged()
        if !alts.isEmpty { emit(["type": "final", "alts": alts]) }
        cleanup(emitEnd: true)
    }

    private func cleanup(emitEnd: Bool) {
        let wasRunning = !ended
        ended = true
        silence?.invalidate(); hardStop?.invalidate()
        if engine.isRunning { engine.stop() }
        engine.inputNode.removeTap(onBus: 0)
        for lane in lanes { lane.task?.cancel() }
        lanes = []
        try? AVAudioSession.sharedInstance().setCategory(.ambient)
        try? AVAudioSession.sharedInstance().setActive(false, options: .notifyOthersOnDeactivation)
        if emitEnd && wasRunning { emit(["type": "end"]) }
    }

    // MARK: - قوة الصوت (للموجة)

    private func reportLevel(_ buffer: AVAudioPCMBuffer) {
        guard Date().timeIntervalSince(lastLevel) > 0.08, let data = buffer.floatChannelData?[0] else { return }
        lastLevel = Date()
        let n = Int(buffer.frameLength)
        guard n > 0 else { return }
        var sum: Float = 0
        for i in 0..<n { sum += data[i] * data[i] }
        let rms = sqrt(sum / Float(n))
        let level = min(1, max(0, (20 * log10(max(rms, 0.000_01)) + 55) / 45))   // من -55dB لـ -10dB
        emit(["type": "level", "v": Double(level)])
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
