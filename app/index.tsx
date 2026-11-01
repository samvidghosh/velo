import React from 'react';
import { ImageBackground, SafeAreaView, StatusBar, StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import { useRouter } from 'expo-router';
import { Colors } from '../constants/colors';

export default function WelcomeScreen() {
  const router=useRouter();
  return <ImageBackground source={require('../assets/running/velo-runner-night.jpg')} resizeMode="cover" style={styles.image}>
    <StatusBar barStyle="light-content"/><View style={styles.scrim}/><SafeAreaView style={styles.safe}>
      <Text style={styles.wordmark}>velo</Text>
      <View style={styles.copy}><Text style={styles.heading}>Know your stride.{"\n"}Build stronger miles.</Text><Text style={styles.subtitle}>Understand how you move. Get a running-form analysis shaped around you.</Text></View>
      <View style={styles.actions}><TouchableOpacity style={styles.primary} onPress={()=>router.push('/signup')}><Text style={styles.primaryText}>Sign up</Text></TouchableOpacity><TouchableOpacity style={styles.secondary} onPress={()=>router.push('/login')}><Text style={styles.secondaryText}>Log in</Text></TouchableOpacity><TouchableOpacity style={styles.preview} onPress={()=>router.push('/onboarding' as never)}><Text style={styles.previewText}>Preview onboarding</Text></TouchableOpacity></View>
    </SafeAreaView>
  </ImageBackground>;
}

const styles=StyleSheet.create({image:{flex:1,backgroundColor:Colors.veloCanvas},scrim:{...StyleSheet.absoluteFill,backgroundColor:'rgba(10,15,9,0.45)'},safe:{flex:1,paddingHorizontal:24,paddingTop:14,paddingBottom:18,justifyContent:'space-between'},wordmark:{fontSize:29,fontWeight:'700',letterSpacing:5,color:Colors.veloText},copy:{marginBottom:26},heading:{fontSize:36,fontWeight:'700',lineHeight:42,color:Colors.veloText,marginBottom:14},subtitle:{fontSize:16,lineHeight:24,color:'#e1e5da',maxWidth:330},actions:{gap:11},primary:{height:52,borderRadius:28,backgroundColor:Colors.veloLime,alignItems:'center',justifyContent:'center'},primaryText:{color:Colors.veloCanvas,fontSize:16,fontWeight:'700'},secondary:{height:52,borderRadius:28,borderWidth:1,borderColor:'rgba(255,255,255,0.65)',backgroundColor:'rgba(255,255,255,0.08)',alignItems:'center',justifyContent:'center'},secondaryText:{color:Colors.veloText,fontSize:16,fontWeight:'600'},preview:{height:44,alignItems:'center',justifyContent:'center'},previewText:{color:'#dce3d3',fontSize:13,textDecorationLine:'underline'}});
