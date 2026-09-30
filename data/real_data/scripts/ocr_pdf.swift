import Foundation
import PDFKit
import Vision

struct PageResult: Codable {
    let page: Int
    let text: String
    let line_count: Int
}

guard CommandLine.arguments.count > 1 else {
    fputs("Usage: ocr_pdf <pdf_path>\n", stderr)
    exit(1)
}

let pdfPath = CommandLine.arguments[1]
guard let doc = PDFDocument(url: URL(fileURLWithPath: pdfPath)) else {
    fputs("Cannot open PDF: \(pdfPath)\n", stderr)
    exit(1)
}

class ImageRenderer {
    let page: PDFPage
    let rect: CGRect
    init(page: PDFPage, rect: CGRect) {
        self.page = page
        self.rect = rect
    }
    func render() -> CGImage? {
        let scale: CGFloat = 2.0
        let width = Int(rect.width * scale)
        let height = Int(rect.height * scale)
        let colorSpace = CGColorSpaceCreateDeviceRGB()
        let bitmapInfo = CGImageAlphaInfo.premultipliedLast.rawValue
        guard let context = CGContext(data: nil, width: width, height: height, bitsPerComponent: 8, bytesPerRow: 0, space: colorSpace, bitmapInfo: bitmapInfo) else {
            return nil
        }
        context.interpolationQuality = .high
        context.setFillColor(CGColor(red: 1, green: 1, blue: 1, alpha: 1))
        context.fill(CGRect(x: 0, y: 0, width: width, height: height))
        context.scaleBy(x: scale, y: scale)
        page.draw(with: .mediaBox, to: context)
        return context.makeImage()
    }
}

var results: [PageResult] = []
let maxPages = min(doc.pageCount, 15) // Process up to first 15 pages for efficiency

for pageIndex in 0..<maxPages {
    guard let page = doc.page(at: pageIndex) else { continue }
    let pageRect = page.bounds(for: .mediaBox)
    let renderer = ImageRenderer(page: page, rect: pageRect)
    if let cgImage = renderer.render() {
        let requestHandler = VNImageRequestHandler(cgImage: cgImage, options: [:])
        var pageLines: [String] = []
        let request = VNRecognizeTextRequest { (req, err) in
            guard let observations = req.results as? [VNRecognizedTextObservation] else { return }
            for obs in observations {
                if let candidate = obs.topCandidates(1).first {
                    pageLines.append(candidate.string)
                }
            }
        }
        request.recognitionLevel = .accurate
        request.usesLanguageCorrection = true
        try? requestHandler.perform([request])
        let fullPageText = pageLines.joined(separator: "\n")
        results.append(PageResult(page: pageIndex + 1, text: fullPageText, line_count: pageLines.count))
    }
}

if let jsonData = try? JSONEncoder().encode(results),
   let jsonString = String(data: jsonData, encoding: .utf8) {
    print(jsonString)
} else {
    print("[]")
}
