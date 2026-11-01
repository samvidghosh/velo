import React, { useState } from 'react';
import { Alert, SafeAreaView, StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import { useRouter } from 'expo-router';
import * as DocumentPicker from 'expo-document-picker';
import { VideoView, useVideoPlayer } from 'expo-video';
import { Colors } from '../constants/colors';

export default function AnalysisScreen() {
  const router = useRouter();
  const [video, setVideo] = useState<DocumentPicker.DocumentPickerAsset | null>(null);
  const player = useVideoPlayer(video?.uri ?? null);
  const selectVideo = async () => {
    const result = await DocumentPicker.getDocumentAsync({ type: ['video/quicktime', 'video/mp4', 'video/*'], copyToCacheDirectory: false, multiple: false });
    if (!result.canceled) setVideo(result.assets[0] ?? null);
  };
  const startAnalysis = () => Alert.alert('Analysis unavailable', 'This build can review your video, but the on-device Apple Vision pose extractor has not yet been integrated. Your video is not uploaded.');
  const size = video?.size ? `${(video.size / (1024 * 1024)).toFixed(1)} MB` : null;
  return <SafeAreaView style={styles.safe}>
    <View style={styles.header}><TouchableOpacity onPress={() => router.back()} accessibilityRole="button"><Text style={styles.back}>‹  Back</Text></TouchableOpacity><Text style={styles.brand}>velo</Text><View style={{width:48}} /></View>
    <View style={styles.body}>
      <Text style={styles.eyebrow}>RUNNING ANALYSIS</Text>
      <Text style={styles.title}>Review your run.</Text>
      <Text style={styles.copy}>Choose a 15–30 second side-on running clip in good light. Keep your full body and feet in frame.</Text>
      {video ? <View style={styles.preview}>
        <VideoView player={player} style={styles.video} nativeControls contentFit="contain" />
        <Text style={styles.filename} numberOfLines={1}>{video.name}</Text>
        {size ? <Text style={styles.meta}>{size}</Text> : null}
        <TouchableOpacity style={styles.change} onPress={selectVideo}><Text style={styles.changeText}>Choose a different video</Text></TouchableOpacity>
      </View> : <TouchableOpacity style={styles.picker} onPress={selectVideo} accessibilityRole="button"><Text style={styles.plus}>＋</Text><Text style={styles.pickTitle}>Select a running video</Text><Text style={styles.pickHint}>MP4 or MOV · video stays on your device</Text></TouchableOpacity>}
      <View style={styles.info}><Text style={styles.infoTitle}>What to expect</Text><Text style={styles.infoText}>Velo will estimate projected joint angles and gait timing from visible landmarks. A camera view cannot establish true 3D angles or exact foot contact.</Text></View>
    </View>
    <View style={styles.footer}><TouchableOpacity disabled={!video} onPress={startAnalysis} style={[styles.button,!video&&styles.disabled]}><Text style={styles.buttonText}>Start analysis</Text></TouchableOpacity><Text style={styles.disclaimer}>Apple Vision analysis is not available in this build yet.</Text></View>
  </SafeAreaView>;
}

const styles=StyleSheet.create({safe:{flex:1,backgroundColor:Colors.veloCanvas},header:{height:64,paddingHorizontal:20,flexDirection:'row',alignItems:'center',justifyContent:'space-between'},back:{color:'#dce4d0',fontSize:16,minWidth:60},brand:{color:Colors.veloText,fontSize:24,fontWeight:'700',letterSpacing:4},body:{flex:1,paddingHorizontal:22,paddingTop:20},eyebrow:{color:Colors.veloLime,fontSize:12,fontWeight:'700',letterSpacing:2,marginBottom:12},title:{color:Colors.veloText,fontSize:32,fontWeight:'700',marginBottom:9},copy:{color:'#cbd1c3',fontSize:15,lineHeight:22,marginBottom:24},picker:{height:214,backgroundColor:'#1c2516',borderColor:'#65704e',borderWidth:1,borderStyle:'dashed',borderRadius:20,alignItems:'center',justifyContent:'center'},plus:{fontSize:34,color:Colors.veloLime,marginBottom:5},pickTitle:{fontSize:16,fontWeight:'700',color:Colors.veloText},pickHint:{fontSize:12,color:'#adb8a0',marginTop:7},preview:{backgroundColor:'#1c2516',borderRadius:20,padding:12},video:{height:220,width:'100%',backgroundColor:'#090d07',borderRadius:12},filename:{color:Colors.veloText,fontSize:14,fontWeight:'600',marginTop:12},meta:{color:'#aeb8a3',fontSize:12,marginTop:4},change:{minHeight:44,justifyContent:'center',alignSelf:'flex-start'},changeText:{color:Colors.veloLime,fontSize:14,fontWeight:'600'},info:{padding:16,marginTop:18,borderRadius:16,backgroundColor:'#1a2414'},infoTitle:{color:Colors.veloText,fontSize:14,fontWeight:'700',marginBottom:7},infoText:{color:'#c5cfb9',fontSize:13,lineHeight:20},footer:{paddingHorizontal:22,paddingBottom:14,paddingTop:10,alignItems:'center'},button:{height:52,width:'100%',borderRadius:27,backgroundColor:Colors.veloLime,alignItems:'center',justifyContent:'center'},disabled:{opacity:.45},buttonText:{color:Colors.veloCanvas,fontWeight:'700',fontSize:16},disclaimer:{color:'#adb4a5',fontSize:11,marginTop:10}});
