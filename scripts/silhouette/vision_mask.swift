// 用 macOS 自带的 Vision 框架把每张图里的前景（人或主体）抠成灰度蒙版。需要 macOS 14 或更新版本。
// 用法：swift scripts/silhouette/vision_mask.swift 输入帧目录 输出蒙版目录
// 输出：和输入同名的 PNG，白 = 前景，黑 = 背景。一张图里有多个前景实例时全部合并。
import CoreImage
import Foundation
import Vision

let args = CommandLine.arguments
guard args.count >= 3 else {
    FileHandle.standardError.write("用法：swift vision_mask.swift 输入帧目录 输出蒙版目录\n".data(using: .utf8)!)
    exit(2)
}
guard #available(macOS 14.0, *) else {
    FileHandle.standardError.write("需要 macOS 14 或更新版本\n".data(using: .utf8)!)
    exit(3)
}

let inDir = URL(fileURLWithPath: args[1])
let outDir = URL(fileURLWithPath: args[2])
try FileManager.default.createDirectory(at: outDir, withIntermediateDirectories: true)
let exts: Set<String> = ["png", "jpg", "jpeg", "tif", "tiff", "heic"]
let files = try FileManager.default.contentsOfDirectory(at: inDir, includingPropertiesForKeys: nil)
    .filter { exts.contains($0.pathExtension.lowercased()) }
    .sorted { $0.lastPathComponent < $1.lastPathComponent }
if files.isEmpty {
    FileHandle.standardError.write("输入目录里没有图片\n".data(using: .utf8)!)
    exit(2)
}

let ctx = CIContext()
let gray = CGColorSpaceCreateDeviceGray()
var done = 0
for f in files {
    guard let image = CIImage(contentsOf: f) else { continue }
    let out = outDir.appendingPathComponent(f.deletingPathExtension().lastPathComponent + ".png")
    let handler = VNImageRequestHandler(ciImage: image, options: [:])
    let request = VNGenerateForegroundInstanceMaskRequest()
    var mask = CIImage(color: .black).cropped(to: image.extent)
    do {
        try handler.perform([request])
        if let obs = request.results?.first {
            let buf = try obs.generateScaledMaskForImage(forInstances: obs.allInstances, from: handler)
            mask = CIImage(cvPixelBuffer: buf)
        }
    } catch {
        FileHandle.standardError.write("\(f.lastPathComponent)：\(error.localizedDescription)，按空蒙版处理\n".data(using: .utf8)!)
    }
    try ctx.writePNGRepresentation(of: mask, to: out, format: .L8, colorSpace: gray)
    done += 1
}
print("写出 \(done) 张蒙版 → \(outDir.path)")
