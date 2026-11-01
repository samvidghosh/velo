import React, { useState } from 'react';
import { Alert, ImageBackground, KeyboardAvoidingView, Platform, ScrollView, StatusBar, StyleSheet, Text, TouchableOpacity, View, useWindowDimensions } from 'react-native';
import { BlurView } from 'expo-blur';
import { SafeAreaView, useSafeAreaInsets } from 'react-native-safe-area-context';
import Svg, { Path } from 'react-native-svg';
import { useRouter } from 'expo-router';
import InputField from '../components/InputField';
import Button from '../components/Button';
import VeloWordmark from '../components/VeloWordmark';
import { mockSignIn } from '../auth/mockAuth';
import PhotoScrim from '../components/PhotoScrim';

const validEmail=(s:string)=>/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(s.trim());
export default function LoginScreen(){
  const router=useRouter();const {height}=useWindowDimensions();const insets=useSafeAreaInsets(); const [email,setEmail]=useState(''); const [password,setPassword]=useState(''); const [emailError,setEmailError]=useState(''); const [passwordError,setPasswordError]=useState(''); const [serverError,setServerError]=useState(''); const [loading,setLoading]=useState(false);
  const submit=async()=>{setEmailError('');setPasswordError('');setServerError('');if(!__DEV__){let ok=true;if(!validEmail(email)){setEmailError(email.trim()?'Please enter a valid email address.':'Email is required.');ok=false}if(!password){setPasswordError('Password is required.');ok=false}if(!ok)return}setLoading(true);const result=await mockSignIn(email.trim(),password);setLoading(false);if(result.error)setServerError(result.error);else router.replace('/analysis')};
  const socialSignIn=(provider:'Apple'|'Google')=>{if(__DEV__){router.replace('/analysis');return}Alert.alert('Sign in unavailable',`${provider} sign in is not configured for this app yet.`)};
  return <ImageBackground source={require('../assets/running/velo-runner-night.jpg')} resizeMode="cover" style={styles.background}>
    <StatusBar barStyle="light-content"/><PhotoScrim variant="login"/><SafeAreaView style={styles.safe} edges={['top','bottom']}>
      <View style={[styles.brand,{top:Platform.OS==='web'?58:0}]}><VeloWordmark/></View>
      <KeyboardAvoidingView style={[styles.formArea,{top:height*.5-insets.top,transform:[{translateY:-height*.24}],maxHeight:height-180}]} behavior={Platform.OS==='ios'?'padding':'height'}>
        <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled" showsVerticalScrollIndicator={false}>
          <BlurView intensity={45} tint="dark" style={styles.card}>
            <Text style={styles.title}>Welcome back</Text><Text style={styles.subtitle}>Your running history is here when you need it.</Text>
            <InputField hideLabel label="Email address" placeholder="Email address" value={email} onChangeText={t=>{setEmail(t);setEmailError('');setServerError('')}} keyboardType="email-address" textContentType="emailAddress" autoComplete="email" autoCapitalize="none" error={emailError}/>
            <InputField hideLabel label="Password" placeholder="Password" value={password} onChangeText={t=>{setPassword(t);setPasswordError('');setServerError('')}} secure textContentType="password" autoComplete="current-password" error={passwordError}/>
            <TouchableOpacity style={styles.forgot} onPress={()=>Alert.alert('Password recovery unavailable','Connect an authentication provider to enable password recovery.')}><Text style={styles.link}>Forgot password?</Text></TouchableOpacity>
            {serverError?<Text style={styles.error}>{serverError}</Text>:null}
            <Button label="Log in" onPress={submit} loading={loading} disabled={loading} style={styles.mainButton}/>
            <View style={styles.divider}><View style={styles.line}/><Text style={styles.dividerText}>or</Text><View style={styles.line}/></View>
            <SocialButton provider="apple" label="Continue with Apple" onPress={()=>socialSignIn('Apple')}/>
            <SocialButton provider="google" label="Continue with Google" onPress={()=>socialSignIn('Google')}/>
          </BlurView>
        </ScrollView>
      </KeyboardAvoidingView>
      <View style={styles.footer}><Text style={styles.footerText}>New to Velo? </Text><Text onPress={()=>router.replace('/signup')} style={styles.footerLink}>Create account</Text></View>
    </SafeAreaView>
  </ImageBackground>
}
function SocialButton({provider,label,onPress}:{provider:'apple'|'google';label:string;onPress:()=>void}) {return <TouchableOpacity onPress={onPress} style={[styles.social,provider==='google'&&styles.google]} accessibilityRole="button"><View style={styles.socialContent}>{provider==='apple'?<Svg width={18} height={18} viewBox="0 0 24 24"><Path d="M18.71 19.5c-.83 1.24-1.71 2.45-3.05 2.47-1.34.03-1.77-.79-3.29-.79-1.53 0-2 .77-3.27.82-1.31.05-2.3-1.32-3.14-2.53C4.2 17 2.94 12.45 4.7 9.39c.87-1.52 2.43-2.48 4.12-2.51 1.28-.02 2.5.87 3.29.87.78 0 2.26-1.07 3.8-.91.65.03 2.47.26 3.64 1.98l-.09.06c-.22.14-2.2 1.28-2.18 3.81.03 3.02 2.65 4.03 2.68 4.04-.03.07-.42 1.44-1.35 2.77M13 3.5c.73-.83 1.94-1.46 2.94-1.5.13 1.17-.34 2.35-1.04 3.19-.69.85-1.83 1.51-2.95 1.42-.15-1.15.41-2.35 1.05-3.11z" fill="#fff"/></Svg>:<Text style={styles.googleG}>G</Text>}<Text style={[styles.socialText,provider==='google'&&styles.googleText]}>{label}</Text></View></TouchableOpacity>}
const styles=StyleSheet.create({background:{flex:1,backgroundColor:'#10140A'},safe:{flex:1,paddingHorizontal:16},brand:{position:'absolute',left:0,right:0,alignItems:'center',zIndex:2},formArea:{position:'absolute',left:16,right:16},scroll:{flexGrow:0},card:{overflow:'hidden',borderRadius:30,borderWidth:1,borderColor:'rgba(255,255,255,.42)',paddingHorizontal:20,paddingTop:24,paddingBottom:20,backgroundColor:'rgba(14,18,21,.7)'},title:{color:'#F5F7FA',fontSize:30,lineHeight:33,fontWeight:'600',letterSpacing:-1.2,marginHorizontal:0},subtitle:{color:'rgba(255,255,255,.88)',fontSize:15,lineHeight:22,marginHorizontal:0,marginTop:8,marginBottom:18},forgot:{alignSelf:'flex-end',minHeight:44,justifyContent:'center',paddingHorizontal:2,marginTop:-4,marginBottom:5},link:{color:'rgba(255,255,255,.92)',fontSize:14,fontWeight:'500'},error:{color:'#ff9990',fontSize:13,textAlign:'center',marginBottom:10},mainButton:{width:'100%',height:50,marginTop:10,marginBottom:0},divider:{height:30,flexDirection:'row',alignItems:'center',gap:12,marginTop:10,marginBottom:3},line:{height:1,flex:1,backgroundColor:'rgba(255,255,255,.32)'},dividerText:{color:'rgba(255,255,255,.84)',fontSize:14},social:{height:50,borderRadius:25,borderWidth:1,borderColor:'rgba(255,255,255,.38)',backgroundColor:'rgba(255,255,255,.11)',alignItems:'center',justifyContent:'center',marginTop:10},socialContent:{flexDirection:'row',alignItems:'center',justifyContent:'center',gap:9},socialText:{color:'#F5F7FA',fontSize:16,fontWeight:'600'},google:{backgroundColor:'#f8f8f7',borderColor:'rgba(255,255,255,.8)'},googleText:{color:'#17191b'},googleG:{fontSize:17,fontWeight:'700',color:'#4285F4'},footer:{position:'absolute',bottom:Platform.OS==='web'?34:2,left:0,right:0,minHeight:44,flexDirection:'row',alignItems:'center',justifyContent:'center'},footerText:{color:'rgba(255,255,255,.92)',fontSize:14},footerLink:{color:'#fff',fontSize:14,fontWeight:'600'}});
