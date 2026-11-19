// 사진 속 얼굴·사람 위치를 JSON 으로 출력 (macOS Vision). 사용: faces <이미지>
// 좌표는 왼쪽 위 기준 0~1 비율: {"faces":[[x,y,w,h]...], "people":[[x,y,w,h]...]}
import Foundation
import Vision
import AppKit

let path = CommandLine.arguments[1]
guard let img = NSImage(contentsOfFile: path),
      let cg = img.cgImage(forProposedRect: nil, context: nil, hints: nil) else {
    print("{\"error\":\"이미지 열기 실패\"}"); exit(1)
}
let faceReq = VNDetectFaceRectanglesRequest()
let humanReq = VNDetectHumanRectanglesRequest()
try? VNImageRequestHandler(cgImage: cg, options: [:]).perform([faceReq, humanReq])
func boxes(_ r: [VNDetectedObjectObservation]?) -> [[Double]] {
    (r ?? []).map { b in let x = b.boundingBox
        return [Double(x.minX), Double(1 - x.maxY), Double(x.width), Double(x.height)] }
}
let out: [String: Any] = ["faces": boxes(faceReq.results), "people": boxes(humanReq.results)]
print(String(data: try! JSONSerialization.data(withJSONObject: out), encoding: .utf8)!)
