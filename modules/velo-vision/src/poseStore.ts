export type Landmark = { coordinates: [number, number]; confidence: number };
export type PoseSequence = {
  schema_version: string;
  video: { duration_seconds: number; sample_rate_hz: number };
  frames: { timestamp: number; landmarks: Record<string, Landmark> }[];
};

let latestPoseSequence: PoseSequence | null = null;

export function setLatestPoseSequence(sequence: PoseSequence) {
  latestPoseSequence = sequence;
}

export function getLatestPoseSequence() {
  return latestPoseSequence;
}

function angle(a: number[], b: number[], c: number[]) {
  const ab = [a[0] - b[0], a[1] - b[1]];
  const cb = [c[0] - b[0], c[1] - b[1]];
  const lengths = Math.hypot(...ab) * Math.hypot(...cb);
  if (!lengths) return null;
  const cosine = Math.max(-1, Math.min(1, (ab[0] * cb[0] + ab[1] * cb[1]) / lengths));
  return (180 - Math.acos(cosine) * 180 / Math.PI);
}

export function summarizePose(sequence: PoseSequence) {
  const summaries = ['left', 'right'].map(side => {
    const values = sequence.frames.flatMap(frame => {
      const hip = frame.landmarks[`${side}_hip`];
      const knee = frame.landmarks[`${side}_knee`];
      const ankle = frame.landmarks[`${side}_ankle`];
      if (!hip || !knee || !ankle || Math.min(hip.confidence, knee.confidence, ankle.confidence) < .35) return [];
      const value = angle(hip.coordinates, knee.coordinates, ankle.coordinates);
      return value === null ? [] : [value];
    });
    return { side, values, mean: values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : null };
  });
  const all = sequence.frames.flatMap(frame => Object.values(frame.landmarks).filter(point => point.confidence >= .35));
  return {
    summaries,
    visibleLandmarkFraction: sequence.frames.length ? all.length / (sequence.frames.length * 8) : 0,
    duration: sequence.video.duration_seconds,
    frameCount: sequence.frames.length,
    cadence: null as number | null,
  };
}
