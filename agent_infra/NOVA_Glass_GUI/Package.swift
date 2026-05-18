// swift-tools-version: 6.0

import PackageDescription

let package = Package(
    name: "NOVAGlassGUI",
    platforms: [
        .macOS(.v15)
    ],
    products: [
        .executable(name: "NOVAGlassGUI", targets: ["NOVAGlassGUI"])
    ],
    targets: [
        .executableTarget(
            name: "NOVAGlassGUI",
            path: "Sources/NOVAGlassGUI"
        )
    ]
)
