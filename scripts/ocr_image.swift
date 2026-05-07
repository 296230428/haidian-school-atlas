import Foundation
import Vision
import CoreGraphics
import ImageIO

if CommandLine.arguments.count < 2 {
    fputs("usage: swift ocr_image.swift <image>\n", stderr)
    exit(2)
}

let path = CommandLine.arguments[1]
let url = URL(fileURLWithPath: path)
guard let source = CGImageSourceCreateWithURL(url as CFURL, nil),
      let image = CGImageSourceCreateImageAtIndex(source, 0, nil) else {
    fputs("failed to load image\n", stderr)
    exit(1)
}

let request = VNRecognizeTextRequest()
request.recognitionLevel = .accurate
request.usesLanguageCorrection = true
request.recognitionLanguages = ["zh-Hans", "en-US"]
request.minimumTextHeight = 0.008

let handler = VNImageRequestHandler(cgImage: image, options: [:])
try handler.perform([request])

let lines = (request.results ?? []).compactMap { observation -> (CGFloat, CGFloat, String)? in
    guard let candidate = observation.topCandidates(1).first else { return nil }
    return (observation.boundingBox.midY, observation.boundingBox.minX, candidate.string)
}
.sorted { a, b in
    if abs(a.0 - b.0) > 0.01 {
        return a.0 > b.0
    }
    return a.1 < b.1
}
.map { $0.2 }

print(lines.joined(separator: "\n"))
