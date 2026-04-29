import SwiftUI
import AppKit

// MARK: - App Glass

struct VisualEffect: NSViewRepresentable {
    var material: NSVisualEffectView.Material = .hudWindow
    var blendingMode: NSVisualEffectView.BlendingMode = .behindWindow

    func makeNSView(context: Context) -> NSVisualEffectView {
        let view = NSVisualEffectView()
        view.material = material
        view.blendingMode = blendingMode
        view.state = .active
        view.isEmphasized = true
        return view
    }

    func updateNSView(_ nsView: NSVisualEffectView, context: Context) {
        nsView.material = material
        nsView.blendingMode = blendingMode
    }
}

enum Aura {
    static let backgroundTop = Color(red: 0.075, green: 0.075, blue: 0.095)
    static let backgroundBottom = Color(red: 0.020, green: 0.022, blue: 0.030)
    static let panel = Color.white.opacity(0.070)
    static let panelStrong = Color.white.opacity(0.105)
    static let hairline = Color.white.opacity(0.115)
    static let hairlineSoft = Color.white.opacity(0.060)
    static let text = Color.white.opacity(0.925)
    static let muted = Color.white.opacity(0.560)
    static let muted2 = Color.white.opacity(0.385)
    static let accent = Color(red: 0.68, green: 0.60, blue: 0.98)
    static let accentSoft = Color(red: 0.47, green: 0.58, blue: 0.92)

    static var background: LinearGradient {
        LinearGradient(
            colors: [backgroundTop, backgroundBottom],
            startPoint: .topLeading,
            endPoint: .bottomTrailing
        )
    }

    static var subtleStroke: LinearGradient {
        LinearGradient(
            colors: [Color.white.opacity(0.18), Color.white.opacity(0.04)],
            startPoint: .top,
            endPoint: .bottom
        )
    }
}

// MARK: - Root

struct ContentView: View {
    @StateObject private var bridge = Bridge()
    @State private var input = ""
    @FocusState private var focused: Bool

    var body: some View {
        ZStack {
            BackgroundLayer()

            VStack(spacing: 0) {
                HeaderView(isReady: bridge.isReady, error: bridge.lastError)
                transcript
                Composer(
                    text: $input,
                    focused: _focused,
                    isReady: bridge.isReady,
                    isStreaming: isStreaming,
                    canSend: canSend,
                    onSubmit: submit,
                    onCancel: bridge.cancel
                )
            }
        }
        .frame(minWidth: 680, minHeight: 520)
        .preferredColorScheme(.dark)
        .onAppear {
            bridge.start()
            focused = true
        }
    }

    private var transcript: some View {
        ScrollViewReader { proxy in
            ScrollView {
                LazyVStack(alignment: .leading, spacing: 22) {
                    if bridge.turns.isEmpty {
                        EmptyTranscript(isReady: bridge.isReady)
                            .padding(.top, 56)
                    } else {
                        ForEach(bridge.turns) { turn in
                            ConversationTurn(turn: turn)
                                .id(turn.id)
                        }
                    }

                    Color.clear.frame(height: 4).id("__tail")
                }
                .frame(maxWidth: 780)
                .frame(maxWidth: .infinity)
                .padding(.horizontal, 26)
                .padding(.top, 18)
                .padding(.bottom, 16)
            }
            .scrollIndicators(.hidden)
            .onChange(of: bridge.turns.last?.answer) { _ in scroll(proxy) }
            .onChange(of: bridge.turns.last?.steps.count) { _ in scroll(proxy) }
            .onChange(of: bridge.turns.count) { _ in scroll(proxy) }
        }
    }

    private func scroll(_ proxy: ScrollViewProxy) {
        withAnimation(.easeOut(duration: 0.20)) {
            proxy.scrollTo("__tail", anchor: .bottom)
        }
    }

    private var isStreaming: Bool {
        bridge.turns.last?.streaming ?? false
    }

    private var canSend: Bool {
        bridge.isReady && !input.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
    }

    private func submit() {
        let text = input
        input = ""
        bridge.send(text)
    }
}

// MARK: - Chrome

struct BackgroundLayer: View {
    var body: some View {
        ZStack {
            Aura.background.ignoresSafeArea()
            VisualEffect(material: .hudWindow, blendingMode: .behindWindow)
                .opacity(0.45)
                .ignoresSafeArea()

            GeometryReader { geo in
                Circle()
                    .fill(Aura.accent.opacity(0.15))
                    .blur(radius: 70)
                    .frame(width: 280, height: 280)
                    .position(x: geo.size.width * 0.16, y: geo.size.height * 0.14)

                Circle()
                    .fill(Aura.accentSoft.opacity(0.10))
                    .blur(radius: 90)
                    .frame(width: 360, height: 360)
                    .position(x: geo.size.width * 0.90, y: geo.size.height * 0.88)
            }
            .ignoresSafeArea()
        }
    }
}

struct HeaderView: View {
    let isReady: Bool
    let error: String?

    var body: some View {
        HStack(spacing: 12) {
            AuraLockup()

            Spacer()

            StatusBadge(isReady: isReady, error: error)
        }
        .padding(.horizontal, 22)
        .padding(.top, 12)
        .padding(.bottom, 10)
        .background(
            Rectangle()
                .fill(.ultraThinMaterial)
                .opacity(0.46)
                .overlay(alignment: .bottom) {
                    Rectangle().fill(Aura.hairlineSoft).frame(height: 1)
                }
        )
    }
}

struct StatusBadge: View {
    let isReady: Bool
    let error: String?

    var body: some View {
        HStack(spacing: 7) {
            Circle()
                .fill(color)
                .frame(width: 7, height: 7)
                .shadow(color: color.opacity(0.45), radius: isReady ? 5 : 0)
            Text(label)
                .font(.system(size: 11, weight: .medium, design: .rounded))
        }
        .foregroundStyle(Aura.muted)
        .padding(.horizontal, 10)
        .padding(.vertical, 6)
        .background(Capsule().fill(Aura.panel))
        .overlay(Capsule().strokeBorder(Aura.hairlineSoft, lineWidth: 1))
    }

    private var label: String {
        if let error, !error.isEmpty { return "Error" }
        return isReady ? "Ready" : "Loading"
    }

    private var color: Color {
        if error != nil { return .red.opacity(0.82) }
        return isReady ? .green.opacity(0.78) : Aura.muted2
    }
}

struct AuraLockup: View {
    var body: some View {
        HStack(spacing: 9) {
            AuraRing(size: 28, lineWidth: 5)
            Text("aura")
                .font(.system(size: 22, weight: .light, design: .rounded))
                .kerning(6)
                .foregroundStyle(Color(red: 0.08, green: 0.10, blue: 0.16))
                .offset(y: -1)
        }
        .padding(.leading, 10)
        .padding(.trailing, 6)
        .padding(.vertical, 7)
        .background(
            RoundedRectangle(cornerRadius: 14, style: .continuous)
                .fill(Color.white.opacity(0.96))
        )
        .overlay(
            RoundedRectangle(cornerRadius: 14, style: .continuous)
                .strokeBorder(Color.white.opacity(0.30), lineWidth: 1)
        )
        .shadow(color: .black.opacity(0.16), radius: 10, x: 0, y: 4)
        .accessibilityLabel("Aura")
    }
}

struct AuraAvatar: View {
    var body: some View {
        ZStack {
            Circle().fill(Color.white.opacity(0.96))
            AuraRing(size: 22, lineWidth: 4)
        }
            .overlay(Circle().strokeBorder(Color.white.opacity(0.22), lineWidth: 1))
            .accessibilityLabel("Aura")
            .frame(width: 32, height: 32)
            .shadow(color: Aura.accent.opacity(0.22), radius: 10, x: 0, y: 4)
    }
}

struct AuraRing: View {
    let size: CGFloat
    let lineWidth: CGFloat

    var body: some View {
        Circle()
            .trim(from: 0.05, to: 0.88)
            .stroke(
                AngularGradient(
                    colors: [
                        Color(red: 0.17, green: 0.42, blue: 1.00),
                        Color(red: 0.45, green: 0.35, blue: 1.00),
                        Color(red: 0.82, green: 0.45, blue: 1.00),
                        Color(red: 0.17, green: 0.42, blue: 1.00)
                    ],
                    center: .center,
                    startAngle: .degrees(110),
                    endAngle: .degrees(470)
                ),
                style: StrokeStyle(lineWidth: lineWidth, lineCap: .round)
            )
            .rotationEffect(.degrees(28))
            .frame(width: size, height: size)
    }
}

// MARK: - Transcript

struct EmptyTranscript: View {
    let isReady: Bool

    var body: some View {
        VStack(spacing: 14) {
            Spacer(minLength: 44)

            VStack(spacing: 8) {
                Text("What can I help with?")
                    .font(.system(size: 26, weight: .semibold, design: .rounded))
                    .foregroundStyle(Aura.text)
                Text(isReady ? "Private, local chat with your agent." : "Loading the local model...")
                    .font(.system(size: 13, weight: .medium, design: .rounded))
                    .foregroundStyle(Aura.muted)
            }

            Spacer(minLength: 44)
        }
        .frame(maxWidth: .infinity)
    }
}

struct ConversationTurn: View {
    let turn: Turn

    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            userMessage
            AssistantMessage(turn: turn)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    private var userMessage: some View {
        HStack(alignment: .top) {
            Spacer(minLength: 84)
            Text(turn.prompt)
                .font(.system(size: 14.5, weight: .medium, design: .rounded))
                .foregroundStyle(Color.white.opacity(0.94))
                .textSelection(.enabled)
                .lineSpacing(3)
                .padding(.horizontal, 15)
                .padding(.vertical, 11)
                .background(
                    RoundedRectangle(cornerRadius: 18, style: .continuous)
                        .fill(Aura.panelStrong)
                )
                .overlay(
                    RoundedRectangle(cornerRadius: 18, style: .continuous)
                        .strokeBorder(Aura.hairlineSoft, lineWidth: 1)
                )
                .frame(maxWidth: 560, alignment: .trailing)
        }
    }
}

struct AssistantMessage: View {
    let turn: Turn
    @State private var activityExpanded = false

    var body: some View {
        HStack(alignment: .top, spacing: 11) {
            AuraAvatar()
                .frame(width: 28, height: 28)
                .padding(.top, 2)

            VStack(alignment: .leading, spacing: 10) {
                topLine

                if !turn.steps.isEmpty {
                    ActivityDisclosure(
                        steps: turn.steps,
                        expanded: $activityExpanded,
                        status: turn.status,
                        streaming: turn.streaming
                    )
                } else if turn.streaming && turn.answer.isEmpty {
                    TypingLine()
                }

                if !turn.answer.isEmpty {
                    Text(turn.answer)
                        .font(.system(size: 14.5, design: .rounded))
                        .foregroundStyle(Aura.text)
                        .lineSpacing(4)
                        .textSelection(.enabled)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .transition(.opacity)
                }

                if let error = turn.error {
                    ErrorRow(message: error)
                }
            }
            .padding(.horizontal, 15)
            .padding(.vertical, 14)
            .background(
                RoundedRectangle(cornerRadius: 18, style: .continuous)
                    .fill(.ultraThinMaterial)
                    .opacity(0.90)
            )
            .overlay(
                RoundedRectangle(cornerRadius: 18, style: .continuous)
                    .strokeBorder(Aura.subtleStroke, lineWidth: 1)
            )
            .shadow(color: .black.opacity(0.20), radius: 14, x: 0, y: 8)
            .frame(maxWidth: 680, alignment: .leading)

            Spacer(minLength: 40)
        }
    }

    private var topLine: some View {
        HStack(spacing: 8) {
            Text("Aura")
                .font(.system(size: 12.5, weight: .semibold, design: .rounded))
                .foregroundStyle(Aura.text)
            if shouldShowStatus {
                StatusPill(status: turn.status, streaming: turn.streaming)
            }
            Spacer()
        }
    }

    private var shouldShowStatus: Bool {
        guard !turn.status.isEmpty else { return false }
        return turn.steps.isEmpty && (turn.streaming || turn.status != "Done")
    }
}

struct StatusPill: View {
    let status: String
    let streaming: Bool

    var body: some View {
        HStack(spacing: 6) {
            if streaming {
                ProgressView()
                    .controlSize(.small)
                    .tint(Aura.accent)
                    .scaleEffect(0.72)
            } else {
                Circle()
                    .fill(color)
                    .frame(width: 6, height: 6)
            }
            Text(status)
                .font(.system(size: 10.5, weight: .medium, design: .rounded))
                .lineLimit(1)
        }
        .foregroundStyle(Aura.muted)
        .padding(.horizontal, 8)
        .padding(.vertical, 4)
        .background(Capsule().fill(Aura.panel))
        .overlay(Capsule().strokeBorder(Aura.hairlineSoft, lineWidth: 1))
    }

    private var color: Color {
        switch status {
        case "Done": return .green.opacity(0.8)
        case "Cancelled": return .orange.opacity(0.82)
        case "Error": return .red.opacity(0.82)
        default: return Aura.accent.opacity(0.9)
        }
    }
}

struct TypingLine: View {
    var body: some View {
        HStack(spacing: 8) {
            ProgressView()
                .controlSize(.small)
                .tint(Aura.accent)
            Text("Thinking")
                .font(.system(size: 13, weight: .medium, design: .rounded))
                .foregroundStyle(Aura.muted)
        }
        .padding(.vertical, 2)
    }
}

struct ErrorRow: View {
    let message: String

    var body: some View {
        Text(message)
            .font(.system(size: 12.5, weight: .medium, design: .rounded))
            .foregroundStyle(.red.opacity(0.86))
            .padding(.horizontal, 10)
            .padding(.vertical, 7)
            .background(
                RoundedRectangle(cornerRadius: 10, style: .continuous)
                    .fill(Color.red.opacity(0.10))
            )
    }
}

// MARK: - Activity

struct ActivityDisclosure: View {
    let steps: [Step]
    @Binding var expanded: Bool
    let status: String
    let streaming: Bool

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Button(action: { withAnimation(.easeOut(duration: 0.16)) { expanded.toggle() } }) {
                HStack(spacing: 7) {
                    Image(systemName: expanded ? "chevron.down" : "chevron.right")
                        .font(.system(size: 9, weight: .bold))
                    Text(summary)
                        .font(.system(size: 12, weight: .medium, design: .rounded))
                        .lineLimit(1)
                    Spacer(minLength: 8)
                    if streaming {
                        ProgressView()
                            .controlSize(.small)
                            .tint(Aura.accent)
                            .scaleEffect(0.70)
                    }
                }
                .foregroundStyle(Aura.muted)
                .padding(.horizontal, 10)
                .padding(.vertical, 7)
                .background(
                    RoundedRectangle(cornerRadius: 11, style: .continuous)
                        .fill(Aura.panel.opacity(0.78))
                )
                .overlay(
                    RoundedRectangle(cornerRadius: 11, style: .continuous)
                        .strokeBorder(Aura.hairlineSoft, lineWidth: 1)
                )
                .contentShape(Rectangle())
            }
            .buttonStyle(.plain)

            if expanded {
                VStack(alignment: .leading, spacing: 8) {
                    ForEach(steps) { step in
                        ActivityRow(step: step)
                    }
                }
                .padding(.leading, 4)
                .transition(.opacity.combined(with: .move(edge: .top)))
            }
        }
    }

    private var summary: String {
        if let last = steps.last {
            switch last.kind {
            case .thinking:
                return "Thinking through the request"
            case .tool:
                let name = last.tool.isEmpty ? "tool" : last.tool
                return last.result.isEmpty ? "Using \(name)" : "Used \(name)"
            case .final:
                return "Writing response"
            }
        }
        return status.isEmpty ? "Working" : status
    }
}

struct ActivityRow: View {
    let step: Step

    var body: some View {
        HStack(alignment: .top, spacing: 8) {
            Image(systemName: icon)
                .font(.system(size: 11, weight: .semibold))
                .foregroundStyle(Aura.accent.opacity(0.85))
                .frame(width: 16, height: 18)

            VStack(alignment: .leading, spacing: 4) {
                Text(title)
                    .font(.system(size: 11.5, weight: .semibold, design: .rounded))
                    .foregroundStyle(Aura.text.opacity(0.86))

                if let detail {
                    Text(detail)
                        .font(.system(size: 11.5, design: detailIsCode ? .monospaced : .rounded))
                        .foregroundStyle(Aura.muted)
                        .lineLimit(4)
                        .frame(maxWidth: .infinity, alignment: .leading)
                }
            }
        }
        .padding(.vertical, 2)
    }

    private var icon: String {
        switch step.kind {
        case .thinking: return "sparkle.magnifyingglass"
        case .tool: return "terminal"
        case .final: return "text.bubble"
        }
    }

    private var title: String {
        switch step.kind {
        case .thinking: return "Thought"
        case .tool: return step.tool.isEmpty ? "Tool" : step.tool
        case .final: return "Response"
        }
    }

    private var detail: String? {
        switch step.kind {
        case .thinking:
            return step.text.isEmpty ? nil : step.text
        case .tool:
            if !step.result.isEmpty { return step.result }
            if !step.args.isEmpty { return step.args }
            return nil
        case .final:
            return nil
        }
    }

    private var detailIsCode: Bool {
        step.kind == .tool && detail == step.args
    }
}

// MARK: - Composer

struct Composer: View {
    @Binding var text: String
    @FocusState var focused: Bool
    let isReady: Bool
    let isStreaming: Bool
    let canSend: Bool
    let onSubmit: () -> Void
    let onCancel: () -> Void

    var body: some View {
        VStack(spacing: 9) {
            HStack(alignment: .center, spacing: 10) {
                TextField(placeholder, text: $text)
                    .textFieldStyle(.plain)
                    .font(.system(size: 14.5, design: .rounded))
                    .foregroundStyle(Aura.text)
                    .focused($focused)
                    .onSubmit(onSubmit)
                    .disabled(!isReady || isStreaming)
                    .padding(.horizontal, 14)
                    .padding(.vertical, 12)

                actionButton
                    .padding(.trailing, 6)
            }
            .background(
                RoundedRectangle(cornerRadius: 18, style: .continuous)
                    .fill(.ultraThinMaterial)
                    .overlay(
                        RoundedRectangle(cornerRadius: 18, style: .continuous)
                            .fill(Aura.panel.opacity(0.72))
                    )
            )
            .overlay(
                RoundedRectangle(cornerRadius: 18, style: .continuous)
                    .strokeBorder(focused ? Aura.accent.opacity(0.42) : Aura.hairline, lineWidth: 1)
            )
            .shadow(color: focused ? Aura.accent.opacity(0.18) : .black.opacity(0.22), radius: focused ? 18 : 12, x: 0, y: 7)
            .animation(.easeOut(duration: 0.16), value: focused)

            HStack {
                Text(isReady ? "Local and private" : "Starting local model")
                    .font(.system(size: 10.5, weight: .medium, design: .rounded))
                    .foregroundStyle(Aura.muted2)
                Spacer()
                Text("Return to send")
                    .font(.system(size: 10.5, weight: .medium, design: .rounded))
                    .foregroundStyle(Aura.muted2)
            }
            .padding(.horizontal, 4)
        }
        .frame(maxWidth: 780)
        .padding(.horizontal, 26)
        .padding(.top, 8)
        .padding(.bottom, 18)
        .frame(maxWidth: .infinity)
        .background(
            LinearGradient(
                colors: [Color.clear, Aura.backgroundBottom.opacity(0.74)],
                startPoint: .top,
                endPoint: .bottom
            )
            .allowsHitTesting(false)
        )
    }

    private var placeholder: String {
        isReady ? "Message Aura" : "Loading model..."
    }

    @ViewBuilder
    private var actionButton: some View {
        if isStreaming {
            Button(action: onCancel) {
                Image(systemName: "stop.fill")
                    .font(.system(size: 10, weight: .bold))
                    .foregroundStyle(Aura.text)
                    .frame(width: 28, height: 28)
                    .background(Circle().fill(Color.white.opacity(0.14)))
            }
            .buttonStyle(.plain)
            .keyboardShortcut(".", modifiers: .command)
            .help("Stop")
        } else {
            Button(action: onSubmit) {
                Image(systemName: "arrow.up")
                    .font(.system(size: 12, weight: .bold))
                    .foregroundStyle(canSend ? .white : Aura.muted2)
                    .frame(width: 28, height: 28)
                    .background(
                        Circle().fill(canSend ? Aura.accent : Color.white.opacity(0.10))
                    )
            }
            .buttonStyle(.plain)
            .keyboardShortcut(.defaultAction)
            .disabled(!canSend)
            .help("Send")
        }
    }
}
