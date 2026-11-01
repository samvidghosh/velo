// Isolated native reference implementation. This file is intentionally outside
// Expo's generated ios/ directory and is not compiled or bridged in this build.
// Validate it in a local Expo module/config plugin on macOS before integration.
import AVFoundation
import ImageIO
import Vision

struct VeloLandmark: Codable {
    let coordinates: [Double]
    let confidence: Double
}

struct VeloPoseFrame: Codable {
    let timestamp: Double
    let landmarks: [String: VeloLandmark]
}

struct VeloPoseSequence: Codable {
    let schemaVersion: String
    let video: [String: String]
    let frames: [VeloPoseFrame]
}

enum VeloPoseExtractionError: Error {
    case noVideoTrack
    case readerSetupFailed
    case decodingFailed
    case noUsableFrames
}

/// Samples AVFoundation-decoded frames at a bounded cadence and returns Vision
/// 2D landmarks. Coordinates are converted to normalized image coordinates
/// (origin at top-left) for `engine.running.schema`.
final class VeloVisionPoseExtractor {
    private let sampleRate: Double
    private let maximumLongEdge: Int

    init(sampleRate: Double = 10, maximumLongEdge: Int = 960) {
        self.sampleRate = max(1, sampleRate)
        self.maximumLongEdge = max(320, maximumLongEdge)
    }

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
        let imageOrientation: CGImagePropertyOrientation = rotation == 90 ? .right : (rotation == -90 ? .left : (abs(rotation) == 180 ? .down : .up))
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
        let names: [(String, VNHumanBodyPoseObservation.JointName)] = [
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
            guard timestamp.isFinite else { continue }
            guard timestamp + 1e-6 >= nextSampleTime else { continue }
            nextSampleTime = timestamp + interval
            guard let pixelBuffer = CMSampleBufferGetImageBuffer(sample) else { continue }

            do {
                try sequenceHandler.perform([request], on: pixelBuffer, orientation: imageOrientation)
            } catch {
                // A failed frame is omitted; a sparse sequence is not repaired
                // into apparently observed measurements.
                continue
            }
            guard let observation = request.results?.first else { continue }
            var landmarks: [String: VeloLandmark] = [:]
            for (key, joint) in names {
                guard let point = try? observation.recognizedPoint(joint), point.confidence > 0 else { continue }
                // Vision uses a bottom-left origin; the Python contract uses top-left.
                landmarks[key] = VeloLandmark(
                    coordinates: [Double(point.location.x), Double(1 - point.location.y)],
                    confidence: Double(point.confidence)
                )
            }
            frames.append(VeloPoseFrame(timestamp: timestamp, landmarks: landmarks))
        }

        guard reader.status == .completed || reader.status == .reading else {
            throw reader.error ?? VeloPoseExtractionError.decodingFailed
        }
        guard !frames.isEmpty else { throw VeloPoseExtractionError.noUsableFrames }
        return VeloPoseSequence(
            schemaVersion: "1.0",
            video: ["duration_seconds": String(CMTimeGetSeconds(duration)), "sample_rate_hz": String(sampleRate)],
            frames: frames
        )
    }
}
