import Foundation
import SwiftUI

/// One reasoning step (thinking or tool call).
struct Step: Identifiable, Equatable {
    enum Kind: String { case thinking, tool, final }
    let id = UUID()
    var kind: Kind
    var text: String = ""        // body of a thinking step
    var tool: String = ""        // tool name
    var args: String = ""        // compact JSON args
    var result: String = ""      // truncated tool result
}

/// One conversation turn.
struct Turn: Identifiable, Equatable {
    let id = UUID()
    var prompt: String
    var steps: [Step] = []
    var answer: String = ""      // streamed final answer
    var status: String = ""      // current pill: "Thinking…" / "Tool: get_datetime" / "Answering…" / "Done"
    var streaming: Bool = true
    var error: String? = nil
}

/// Owns the python child. Spawns `python -u aura_backend/bridge.py`, watches
/// stdout for line-prefixed events (and the `__READY__` / `__END__` sentinels),
/// publishes `turns` for the UI. Stdin gets one line per prompt.
@MainActor
final class Bridge: ObservableObject {
    @Published var turns: [Turn] = []
    @Published var isReady: Bool = false
    @Published var lastError: String? = nil

    private var process: Process?
    private var stdin: FileHandle?
    private var stdoutBuffer = Data()

    /// Once a turn enters `[FINAL]` state, every subsequent non-prefix line
    /// is part of the streamed answer until `__END__`.
    private var inFinal: Bool = false

    // MARK: lifecycle

    func start() {
        guard process == nil else { return }
        do {
            try spawn()
        } catch {
            lastError = error.localizedDescription
        }
    }

    func stop() {
        if let p = process, p.isRunning { p.terminate() }
        try? stdin?.close()
        stdin = nil
        process = nil
        isReady = false
    }

    private func spawn() throws {
        let python = resolvePython()
        let bridgePy = repoRoot().appendingPathComponent("aura_backend/bridge.py")
        guard FileManager.default.fileExists(atPath: bridgePy.path) else {
            throw NSError(domain: "Aura", code: 1, userInfo: [NSLocalizedDescriptionKey: "bridge.py not found at \(bridgePy.path)"])
        }

        let p = Process()
        p.executableURL = python
        p.arguments = ["-u", bridgePy.path]
        p.currentDirectoryURL = repoRoot()
        var env = ProcessInfo.processInfo.environment
        env["PYTHONUNBUFFERED"] = "1"
        p.environment = env

        let inPipe = Pipe()
        let outPipe = Pipe()
        let errPipe = Pipe()
        p.standardInput = inPipe
        p.standardOutput = outPipe
        p.standardError = errPipe

        outPipe.fileHandleForReading.readabilityHandler = { [weak self] handle in
            let data = handle.availableData
            guard !data.isEmpty else { return }
            Task { @MainActor in self?.consume(data) }
        }
        errPipe.fileHandleForReading.readabilityHandler = { handle in
            let data = handle.availableData
            if !data.isEmpty {
                FileHandle.standardError.write(data)
            }
        }

        p.terminationHandler = { [weak self] proc in
            Task { @MainActor in
                self?.isReady = false
                self?.process = nil
                self?.stdin = nil
                if proc.terminationStatus != 0 {
                    self?.lastError = "python exited with status \(proc.terminationStatus)"
                }
            }
        }

        try p.run()
        process = p
        stdin = inPipe.fileHandleForWriting
    }

    // MARK: requests

    func send(_ prompt: String) {
        let trimmed = prompt.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty, isReady else { return }
        guard !(turns.last?.streaming ?? false) else { return }

        var t = Turn(prompt: trimmed)
        t.status = "Thinking…"
        turns.append(t)
        inFinal = false
        write(trimmed + "\n")
    }

    /// SIGINT the child to interrupt mid-generation.
    func cancel() {
        guard let p = process, p.isRunning else { return }
        kill(p.processIdentifier, SIGINT)
        if let i = lastStreamingIndex() {
            turns[i].streaming = false
            turns[i].status = "Cancelled"
        }
        inFinal = false
    }

    // MARK: stdout parsing

    private func consume(_ data: Data) {
        stdoutBuffer.append(data)
        while let nl = stdoutBuffer.firstIndex(of: 0x0A) {
            let lineData = stdoutBuffer.prefix(upTo: nl)
            stdoutBuffer.removeSubrange(stdoutBuffer.startIndex...nl)
            let line = String(data: lineData, encoding: .utf8) ?? ""
            handleLine(line, terminated: true)
        }
        // Stream partial lines (no trailing \n) to the answer if we're in
        // final mode — animated streaming arrives in <chunk>-byte writes.
        if !stdoutBuffer.isEmpty,
           let partial = String(data: stdoutBuffer, encoding: .utf8) {
            stdoutBuffer.removeAll(keepingCapacity: true)
            handleLine(partial, terminated: false)
        }
    }

    private func handleLine(_ raw: String, terminated: Bool) {
        // Sentinels.
        if raw == "__READY__" {
            isReady = true
            return
        }
        if raw == "__END__" {
            if let i = lastStreamingIndex() {
                turns[i].streaming = false
                turns[i].status = "Done"
            }
            inFinal = false
            return
        }

        guard let i = lastStreamingIndex() else {
            // unsolicited line; surface to stderr
            FileHandle.standardError.write(Data((raw + "\n").utf8))
            return
        }

        // Prefix events. They always arrive on terminated lines.
        if terminated, let event = parseEvent(raw) {
            apply(event, toTurnAt: i)
            return
        }

        // Otherwise: in-final streamed text (terminated or not).
        if inFinal {
            turns[i].answer += raw
            if terminated { turns[i].answer += "\n" }
        } else {
            // Pre-final text without a recognised prefix: stash on the
            // current step so we don't lose it.
            ensureCurrentStep(in: i, kind: .thinking)
            turns[i].steps[turns[i].steps.count - 1].text += raw
            if terminated {
                turns[i].steps[turns[i].steps.count - 1].text += "\n"
            }
        }
    }

    private enum Event {
        case step(String)            // [STEP] thinking|tool|final
        case text(String)            // [TEXT] ...
        case tool(String)            // [TOOL] name
        case args(String)            // [ARGS] {...}
        case result(String)          // [RESULT] ...
        case finalStart              // [FINAL]
        case error(String)           // [ERROR] ...
    }

    private func parseEvent(_ raw: String) -> Event? {
        guard raw.hasPrefix("[") else { return nil }
        if let body = strip(prefix: "[STEP] ", from: raw)   { return .step(body) }
        if let body = strip(prefix: "[TEXT] ", from: raw)   { return .text(body) }
        if let body = strip(prefix: "[TOOL] ", from: raw)   { return .tool(body) }
        if let body = strip(prefix: "[ARGS] ", from: raw)   { return .args(body) }
        if let body = strip(prefix: "[RESULT] ", from: raw) { return .result(body) }
        if let body = strip(prefix: "[ERROR] ", from: raw)  { return .error(body) }
        if raw == "[FINAL]" { return .finalStart }
        return nil
    }

    private func strip(prefix: String, from s: String) -> String? {
        guard s.hasPrefix(prefix) else { return nil }
        return String(s.dropFirst(prefix.count))
    }

    private func apply(_ event: Event, toTurnAt i: Int) {
        switch event {
        case .step(let role):
            switch role {
            case "thinking":
                turns[i].steps.append(Step(kind: .thinking))
                turns[i].status = "Thinking…"
            case "tool":
                turns[i].steps.append(Step(kind: .tool))
                turns[i].status = "Calling tool…"
            case "final":
                turns[i].status = "Answering…"
            default:
                break
            }
        case .text(let body):
            ensureCurrentStep(in: i, kind: .thinking)
            let last = turns[i].steps.count - 1
            if !turns[i].steps[last].text.isEmpty {
                turns[i].steps[last].text += " "
            }
            turns[i].steps[last].text += body
        case .tool(let name):
            ensureCurrentStep(in: i, kind: .tool)
            let last = turns[i].steps.count - 1
            turns[i].steps[last].tool = name
            turns[i].status = "Tool: \(name)"
        case .args(let body):
            ensureCurrentStep(in: i, kind: .tool)
            let last = turns[i].steps.count - 1
            turns[i].steps[last].args = body
        case .result(let body):
            ensureCurrentStep(in: i, kind: .tool)
            let last = turns[i].steps.count - 1
            turns[i].steps[last].result = body
        case .finalStart:
            inFinal = true
            turns[i].status = "Answering…"
        case .error(let msg):
            turns[i].error = msg
            turns[i].streaming = false
            turns[i].status = "Error"
            lastError = msg
            inFinal = false
        }
    }

    private func ensureCurrentStep(in i: Int, kind: Step.Kind) {
        if turns[i].steps.last?.kind != kind {
            turns[i].steps.append(Step(kind: kind))
        }
    }

    private func lastStreamingIndex() -> Int? {
        for i in turns.indices.reversed() where turns[i].streaming {
            return i
        }
        return nil
    }

    // MARK: stdin

    private func write(_ s: String) {
        guard let stdin, let data = s.data(using: .utf8) else { return }
        do { try stdin.write(contentsOf: data) }
        catch { lastError = "stdin write: \(error.localizedDescription)" }
    }

    // MARK: paths

    private func repoRoot() -> URL {
        let exe = Bundle.main.executableURL ?? URL(fileURLWithPath: CommandLine.arguments[0])
        var dir = exe.deletingLastPathComponent()
        for _ in 0..<8 {
            let cand = dir.appendingPathComponent("aura_backend/bridge.py")
            if FileManager.default.fileExists(atPath: cand.path) { return dir }
            dir = dir.deletingLastPathComponent()
        }
        return URL(fileURLWithPath: FileManager.default.currentDirectoryPath)
    }

    private func resolvePython() -> URL {
        // 1. repo venv (the one with mlx_lm)
        let venv = repoRoot().appendingPathComponent("venv/bin/python")
        if FileManager.default.isExecutableFile(atPath: venv.path) { return venv }
        // 2. python3 on PATH
        let path = ProcessInfo.processInfo.environment["PATH"] ?? "/usr/bin:/usr/local/bin:/opt/homebrew/bin"
        for dir in path.split(separator: ":") {
            let cand = URL(fileURLWithPath: String(dir)).appendingPathComponent("python3")
            if FileManager.default.isExecutableFile(atPath: cand.path) { return cand }
        }
        // 3. last resort
        return URL(fileURLWithPath: "/usr/bin/env")
    }
}
