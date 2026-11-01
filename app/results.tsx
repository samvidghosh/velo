import React from 'react';
import { SafeAreaView, ScrollView, StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import { useRouter } from 'expo-router';
import { Colors } from '../constants/colors';
import { getLatestPoseSequence, summarizePose } from '../modules/velo-vision/src/poseStore';

export default function ResultsScreen() {
  const router = useRouter();
  const sequence = getLatestPoseSequence();
  if (!sequence) {
    return <SafeAreaView style={styles.safe}><Text style={styles.title}>No analysis found</Text><TouchableOpacity onPress={() => router.replace('/analysis')}><Text style={styles.action}>Choose a video</Text></TouchableOpacity></SafeAreaView>;
  }
  const summary = summarizePose(sequence);
  return <SafeAreaView style={styles.safe}>
    <View style={styles.header}><TouchableOpacity onPress={() => router.back()}><Text style={styles.back}>‹  Back</Text></TouchableOpacity><Text style={styles.brand}>velo</Text><View style={{ width: 48 }} /></View>
    <ScrollView contentContainerStyle={styles.content}>
      <Text style={styles.eyebrow}>RUNNING ANALYSIS</Text>
      <Text style={styles.title}>Your run, in view.</Text>
      <Text style={styles.copy}>Apple Vision processed this clip on your device. These are projected 2D estimates.</Text>
      <View style={styles.stats}><View style={styles.stat}><Text style={styles.statValue}>{summary.frameCount}</Text><Text style={styles.statLabel}>POSE FRAMES</Text></View><View style={styles.stat}><Text style={styles.statValue}>{summary.duration.toFixed(1)}s</Text><Text style={styles.statLabel}>CLIP LENGTH</Text></View><View style={styles.stat}><Text style={styles.statValue}>{Math.round(summary.visibleLandmarkFraction * 100)}%</Text><Text style={styles.statLabel}>LANDMARKS</Text></View></View>
      <Text style={styles.section}>Projected knee flexion</Text>
      {summary.summaries.map(item => <View key={item.side} style={styles.card}><View style={styles.row}><Text style={styles.metricName}>{item.side === 'left' ? 'Left' : 'Right'} knee</Text><Text style={styles.metricValue}>{item.mean === null ? 'Unavailable' : `${item.mean.toFixed(0)}° mean`}</Text></View><Text style={styles.detail}>{item.values.length} usable frame measurements</Text></View>)}
      <View style={styles.note}><Text style={styles.noteTitle}>How to read this</Text><Text style={styles.noteText}>A single camera view cannot measure true 3D joint angles or confirm foot contact. Visibility and camera position affect these estimates. This app does not diagnose injury or grade your form.</Text></View>
      <TouchableOpacity style={styles.button} onPress={() => router.replace('/analysis')}><Text style={styles.buttonText}>Analyze another run</Text></TouchableOpacity>
    </ScrollView>
  </SafeAreaView>;
}

const styles = StyleSheet.create({ safe: { flex: 1, backgroundColor: Colors.veloCanvas }, header: { height: 64, paddingHorizontal: 20, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }, back: { color: '#dce4d0', fontSize: 16, minWidth: 60 }, brand: { color: Colors.veloText, fontSize: 24, fontWeight: '700', letterSpacing: 4 }, content: { paddingHorizontal: 22, paddingTop: 20, paddingBottom: 30 }, eyebrow: { color: Colors.veloLime, fontSize: 12, fontWeight: '700', letterSpacing: 2, marginBottom: 12 }, title: { color: Colors.veloText, fontSize: 32, fontWeight: '700', marginBottom: 9 }, copy: { color: '#cbd1c3', fontSize: 15, lineHeight: 22, marginBottom: 24 }, stats: { flexDirection: 'row', gap: 10, marginBottom: 28 }, stat: { flex: 1, padding: 13, borderRadius: 15, backgroundColor: '#1a2414' }, statValue: { color: Colors.veloLime, fontSize: 21, fontWeight: '700' }, statLabel: { color: '#aeb8a3', fontSize: 9, letterSpacing: 1, marginTop: 5 }, section: { color: Colors.veloText, fontSize: 18, fontWeight: '700', marginBottom: 12 }, card: { padding: 16, borderRadius: 16, backgroundColor: '#1c2516', marginBottom: 10 }, row: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }, metricName: { color: Colors.veloText, fontSize: 15, fontWeight: '600' }, metricValue: { color: Colors.veloLime, fontSize: 15, fontWeight: '700' }, detail: { color: '#aeb8a3', fontSize: 12, marginTop: 7 }, note: { padding: 16, marginTop: 14, borderRadius: 16, backgroundColor: '#1a2414' }, noteTitle: { color: Colors.veloText, fontSize: 14, fontWeight: '700', marginBottom: 7 }, noteText: { color: '#c5cfb9', fontSize: 13, lineHeight: 20 }, button: { height: 52, marginTop: 22, borderRadius: 27, backgroundColor: Colors.veloLime, alignItems: 'center', justifyContent: 'center' }, buttonText: { color: Colors.veloCanvas, fontWeight: '700', fontSize: 16 }, action: { color: Colors.veloLime, padding: 20 } });
