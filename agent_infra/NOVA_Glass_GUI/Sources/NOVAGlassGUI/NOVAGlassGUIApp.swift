import AppKit
import SwiftUI

@main
struct NOVAGlassGUIApp: App {
    init() {
        NSApplication.shared.setActivationPolicy(.regular)
    }

    var body: some Scene {
        WindowGroup {
            NOVAPromptOverlay()
                .frame(minWidth: 760, minHeight: 420)
                .onAppear {
                    NSApplication.shared.activate(ignoringOtherApps: true)
                    NSApplication.shared.windows.first?.makeKeyAndOrderFront(nil)
                }
        }
        .windowStyle(.hiddenTitleBar)
    }
}

@MainActor
final class NOVAProcess: ObservableObject {
    @Published var transcript = ""
    @Published var isRunning = false

    private let projectRoot = URL(fileURLWithPath: "/Users/eligross/Desktop/local_agent_infra/agent_infra")
    private let command = """
    if [ -f /Users/eligross/Desktop/local_agent_infra/venv/bin/activate ]; then source /Users/eligross/Desktop/local_agent_infra/venv/bin/activate; fi; python -u main.py
    """

    private var process: Process?
    private var inputPipe: Pipe?
    private var outputPipe: Pipe?
    private var errorPipe: Pipe?

    deinit {
        process?.terminate()
        outputPipe?.fileHandleForReading.readabilityHandler = nil
        errorPipe?.fileHandleForReading.readabilityHandler = nil
    }

    func start() {
        guard !isRunning else { return }

        let process = Process()
        let inputPipe = Pipe()
        let outputPipe = Pipe()
        let errorPipe = Pipe()

        process.executableURL = URL(fileURLWithPath: "/bin/zsh")
        process.arguments = ["-lc", command]
        process.currentDirectoryURL = projectRoot
        process.standardInput = inputPipe
        process.standardOutput = outputPipe
        process.standardError = errorPipe
        process.environment = ProcessInfo.processInfo.environment.merging(
            ["PYTHONUNBUFFERED": "1"]
        ) { _, new in new }

        outputPipe.fileHandleForReading.readabilityHandler = { [weak self] handle in
            let data = handle.availableData
            guard !data.isEmpty, let text = String(data: data, encoding: .utf8) else { return }
            Task { @MainActor in self?.append(text) }
        }

        errorPipe.fileHandleForReading.readabilityHandler = { [weak self] handle in
            let data = handle.availableData
            guard !data.isEmpty, let text = String(data: data, encoding: .utf8) else { return }
            Task { @MainActor in self?.append(text) }
        }

        process.terminationHandler = { [weak self] process in
            Task { @MainActor in
                self?.isRunning = false
                self?.append("\n[backend exited: \(process.terminationStatus)]\n")
            }
        }

        do {
            try process.run()
            self.process = process
            self.inputPipe = inputPipe
            self.outputPipe = outputPipe
            self.errorPipe = errorPipe
            self.transcript = ""
            self.isRunning = true
        } catch {
            append("Could not start NOVA: \(error.localizedDescription)\n")
        }
    }

    func stop() {
        process?.terminate()
        outputPipe?.fileHandleForReading.readabilityHandler = nil
        errorPipe?.fileHandleForReading.readabilityHandler = nil
        process = nil
        inputPipe = nil
        outputPipe = nil
        errorPipe = nil
        isRunning = false
    }

    func send(_ text: String) {
        guard isRunning else { return }
        guard let data = (text + "\n").data(using: .utf8) else { return }
        append("\nYou: \(text)\n")
        inputPipe?.fileHandleForWriting.write(data)
    }

    private func append(_ text: String) {
        transcript += text
    }
}

struct NOVAPromptOverlay: View {
    @StateObject private var nova = NOVAProcess()
    @State private var prompt = ""
    @FocusState private var promptFocused: Bool

    private var hasOutput: Bool {
        !nova.transcript.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
    }

    var body: some View {
        ZStack {
            QuietBackground()

            VStack(spacing: 12) {
                PromptCapsule(
                    text: $prompt,
                    isRunning: nova.isRunning,
                    focused: $promptFocused,
                    send: sendPrompt
                )
                .frame(maxWidth: 720)

                if hasOutput {
                    OutputDrawer(text: nova.transcript)
                        .frame(maxWidth: 720, maxHeight: 320)
                        .transition(.opacity.combined(with: .move(edge: .top)))
                }
            }
            .padding(36)
        }
        .preferredColorScheme(.dark)
        .onAppear {
            nova.start()
            focusPrompt()
        }
        .onDisappear {
            nova.stop()
        }
        .onTapGesture {
            focusPrompt()
        }
        .onChange(of: nova.isRunning) {
            focusPrompt()
        }
    }

    private func sendPrompt() {
        let trimmed = prompt.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return }
        nova.send(trimmed)
        prompt = ""
        focusPrompt()
    }

    private func focusPrompt() {
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.12) {
            NSApplication.shared.activate(ignoringOtherApps: true)
            NSApplication.shared.windows.first?.makeKeyAndOrderFront(nil)
            promptFocused = true
        }
    }
}

struct PromptCapsule: View {
    @Binding var text: String
    let isRunning: Bool
    var focused: FocusState<Bool>.Binding
    let send: () -> Void

    var body: some View {
        HStack(spacing: 14) {
            Text("NOVA")
                .font(.system(size: 12, weight: .medium))
                .foregroundStyle(.white.opacity(0.62))
                .frame(width: 48, alignment: .leading)

            TextField(isRunning ? "Ask anything..." : "Starting...", text: $text)
                .textFieldStyle(.plain)
                .font(.system(size: 16, weight: .regular))
                .foregroundStyle(.white.opacity(0.92))
                .focused(focused)
                .onSubmit(send)
                .disabled(!isRunning)

            Button(action: send) {
                Image(systemName: "arrow.up")
                    .font(.system(size: 13, weight: .semibold))
                    .frame(width: 28, height: 28)
            }
            .buttonStyle(.send)
            .disabled(!isRunning || text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
        }
        .padding(.leading, 20)
        .padding(.trailing, 14)
        .padding(.vertical, 14)
        .glassSurface(cornerRadius: 26, interactive: true)
    }
}

struct OutputDrawer: View {
    let text: String

    var body: some View {
        ScrollViewReader { proxy in
            ScrollView {
                Text(text)
                    .font(.system(size: 12, weight: .regular, design: .monospaced))
                    .foregroundStyle(.white.opacity(0.76))
                    .frame(maxWidth: .infinity, alignment: .topLeading)
                    .textSelection(.enabled)
                    .padding(18)

                Color.clear.frame(height: 1).id("bottom")
            }
            .onChange(of: text) {
                withAnimation(.easeOut(duration: 0.14)) {
                    proxy.scrollTo("bottom", anchor: .bottom)
                }
            }
        }
        .background(.black.opacity(0.22), in: RoundedRectangle(cornerRadius: 22))
        .glassSurface(cornerRadius: 24, interactive: false)
    }
}

struct QuietBackground: View {
    var body: some View {
        LinearGradient(
            colors: [
                Color(red: 0.025, green: 0.030, blue: 0.036),
                Color(red: 0.038, green: 0.045, blue: 0.052),
                Color(red: 0.020, green: 0.026, blue: 0.030),
            ],
            startPoint: .topLeading,
            endPoint: .bottomTrailing
        )
        .overlay {
            Rectangle()
                .fill(.white.opacity(0.018))
        }
        .ignoresSafeArea()
    }
}

struct GlassSurface: ViewModifier {
    let cornerRadius: CGFloat
    let interactive: Bool

    func body(content: Content) -> some View {
        if #available(macOS 26.0, *) {
            GlassEffectContainer(spacing: 12) {
                content
                    .glassEffect(
                        interactive ? .regular.tint(.white.opacity(0.08)).interactive() : .regular.tint(.white.opacity(0.06)),
                        in: .rect(cornerRadius: cornerRadius)
                    )
            }
        } else {
            content
                .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: cornerRadius))
                .overlay(
                    RoundedRectangle(cornerRadius: cornerRadius)
                        .stroke(.white.opacity(0.10), lineWidth: 1)
                )
        }
    }
}

extension View {
    func glassSurface(cornerRadius: CGFloat, interactive: Bool) -> some View {
        modifier(GlassSurface(cornerRadius: cornerRadius, interactive: interactive))
    }
}

struct SendButtonStyle: ButtonStyle {
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .foregroundStyle(.black.opacity(configuration.isPressed ? 0.58 : 0.84))
            .background(
                Circle()
                    .fill(.cyan.opacity(configuration.isPressed ? 0.58 : 0.86))
            )
    }
}

extension ButtonStyle where Self == SendButtonStyle {
    static var send: SendButtonStyle { SendButtonStyle() }
}
