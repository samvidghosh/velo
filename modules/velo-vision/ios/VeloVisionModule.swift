import AVFoundation
import ExpoModulesCore
import ImageIO
import Vision

private struct VeloLandmark: Codable {
  let coordinates: [Double]
  let confidence: Double
}

private struct VeloPoseFrame: Codable {
  let timestamp: Double
  let landmarks: [String: VeloLandmark]
}

private struct VeloPoseSequence: Codable {
  let schema_version: String
  let video: [String: Double]
  let frames: [VeloPoseFrame]
}

private enum VeloPoseExtractionError: LocalizedError {
  case noVideoTrack
  case readerSetupFailed
  case decodingFailed
  case noUsableFrames

  var errorDescription: String? {
    switch self {
    case .noVideoTrack: return "The selected file does not contain a video track."
    case .readerSetupFailed: return "The video could not be opened for local analysis."
    case .decodingFailed: return "The video could not be decoded. Try exporting it as MP4 or MOV."
    case .noUsableFrames: return "No body landmarks were detected. Try a brighter side-on clip with your full body in frame."
    }
  }
}

private final class VeloVisionPoseExtractor {
  private let sampleRate = 8.0
  private let maximumLongEdge = 720

  func extract(from url: URL) async throws -> VeloPoseSequence {
    let asset = AVURLAsset(url: url)
    let tracks = try await asset.loadTracks(withMediaType: .video)
    guard let track = tracks.first else { throw VeloPoseExtractionError.noVideoTrack }
    let duration = try await asset.load(.duration)
    let naturalSize = try await track.load(.naturalSize)
    let preferredTransform = try await track.load(.preferredTransform)
    let scale = min(1, CGFloat(maximumLongEdge) / max(naturalSize.width, naturalSize.height))
    let outputWidth = max(1, Int((naturalSize.width * scale).rounded()))
    let outputHeight = max(1, Int((naturalSize.height * scale).rounded()))
    let rotation = Int((atan2(preferredTransform.b, preferredTransform.a) * 180 / .pi).rounded())
    let orientation: CGImagePropertyOrientation = rotation == 90 ? .right : (rotation == -90 ? .left : (abs(rotation) == 180 ? .down : .up))
    let reader = try AVAssetReader(asset: asset)
    reader.timeRange = CMTimeRange(start: .zero, duration: duration)
    let output = AVAssetReaderTrackOutput(track: track, outputSettings: [
      kCVPixelBufferPixelFormatTypeKey as String: kCVPixelFormatType_32BGRA,
      kCVPixelBufferWidthKey as String: outputWidth,
      kCVPixelBufferHeightKey as String: outputHeight
    ])
    output.alwaysCopiesSampleData = false
    guard reader.canAdd(output) else { throw VeloPoseExtractionError.readerSetupFailed }
    reader.add(output)
    guard reader.startReading() else { throw reader.error ?? VeloPoseExtractionError.readerSetupFailed }

    let request = VNDetectHumanBodyPoseRequest()
    let sequenceHandler = VNSequenceRequestHandler()
    let joints: [(String, VNHumanBodyPoseObservation.JointName)] = [
      ("left_shoulder", .leftShoulder), ("right_shoulder", .rightShoulder),
      ("left_hip", .leftHip), ("right_hip", .rightHip),
      ("left_knee", .leftKnee), ("right_knee", .rightKnee),
      ("left_ankle", .leftAnkle), ("right_ankle", .rightAnkle)
    ]
    let interval = 1.0 / sampleRate
    var nextSampleTime = 0.0
    var frames: [VeloPoseFrame] = []

    while let sample = output.copyNextSampleBuffer() {
      let timestamp = CMTimeGetSeconds(CMSampleBufferGetPresentationTimeStamp(sample))
      guard timestamp.isFinite, timestamp + 1e-6 >= nextSampleTime else { continue }
      nextSampleTime = timestamp + interval
      guard let pixelBuffer = CMSampleBufferGetImageBuffer(sample) else { continue }
      do { try sequenceHandler.perform([request], on: pixelBuffer, orientation: orientation) }
      catch { continue }
      guard let observation = request.results?.first else { continue }
      var landmarks: [String: VeloLandmark] = [:]
      for (key, joint) in joints {
        guard let point = try? observation.recognizedPoint(joint), point.confidence > 0 else { continue }
        landmarks[key] = VeloLandmark(coordinates: [Double(point.location.x), Double(1 - point.location.y)], confidence: Double(point.confidence))
      }
      frames.append(VeloPoseFrame(timestamp: timestamp, landmarks: landmarks))
    }

    guard reader.status == .completed || reader.status == .reading else { throw reader.error ?? VeloPoseExtractionError.decodingFailed }
    guard !frames.isEmpty else { throw VeloPoseExtractionError.noUsableFrames }
    return VeloPoseSequence(schema_version: "1.0", video: [
      "duration_seconds": CMTimeGetSeconds(duration), "sample_rate_hz": sampleRate
    ], frames: frames)
  }
}

public class VeloVisionModule: Module {
  public func definition() -> ModuleDefinition {
    Name("VeloVision")
    AsyncFunction("analyzeVideo") { (uri: String) async throws -> String in
      guard let url = URL(string: uri), url.isFileURL else {
        throw NSError(domain: "VeloVision", code: 1, userInfo: [NSLocalizedDescriptionKey: "The selected video is not available as a local file."])
      }
      let sequence = try await VeloVisionPoseExtractor().extract(from: url)
      let data = try JSONEncoder().encode(sequence)
      guard let json = String(data: data, encoding: .utf8) else {
        throw NSError(domain: "VeloVision", code: 2, userInfo: [NSLocalizedDescriptionKey: "Could not serialize pose data."])
      }
      return json
    }
  }
}
