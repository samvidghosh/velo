import React from 'react';
import { ImageBackground, StatusBar, StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import VeloWordmark from '../components/VeloWordmark';
import PhotoScrim from '../components/PhotoScrim';

const lime = '#C4F52A';

export default function WelcomeScreen() {
  const router = useRouter();
  return <ImageBackground source={require('../assets/running/velo-runner-night.jpg')} resizeMode="cover" style={styles.image}>
    <StatusBar barStyle="light-content"/><PhotoScrim/><SafeAreaView style={styles.safe} edges={['top','bottom']}>
      <VeloWordmark />
      <View style={styles.copy}>
        <Text style={styles.heading}>Know your stride.{'\n'}Build stronger miles.</Text>
        <Text style={styles.subtitle}>Understand how you move. Get a gait analysis and strength work shaped around you.</Text>
      </View>
      <View style={styles.actions}>
        <TouchableOpacity accessibilityRole="button" style={styles.primary} onPress={()=>router.push('/signup')}><Text style={styles.primaryText}>Sign up</Text></TouchableOpacity>
        <TouchableOpacity accessibilityRole="button" style={styles.secondary} onPress={()=>router.push('/login')}><Text style={styles.secondaryText}>Log in</Text></TouchableOpacity>
      </View>
    </SafeAreaView>
  </ImageBackground>;
}

const styles=StyleSheet.create({image:{flex:1,backgroundColor:'#10140A'},safe:{flex:1,paddingHorizontal:24,justifyContent:'space-between'},copy:{marginBottom:0},heading:{fontSize:36,fontWeight:'700',letterSpacing:-1.7,lineHeight:37.5,color:'#F5F7FA',marginBottom:10},subtitle:{fontSize:16,lineHeight:23,color:'rgba(245,247,250,.9)',maxWidth:300},actions:{flexDirection:'row',gap:10,marginHorizontal:-4},primary:{flex:1,height:50,borderRadius:28,backgroundColor:lime,alignItems:'center',justifyContent:'center',shadowColor:lime,shadowOpacity:.2,shadowRadius:18},primaryText:{color:'#101708',fontSize:16,fontWeight:'600'},secondary:{flex:1.13,height:50,borderRadius:28,borderWidth:1,borderColor:'rgba(242,248,255,.52)',backgroundColor:'rgba(13,23,33,.34)',alignItems:'center',justifyContent:'center'},secondaryText:{color:'#F5F7FA',fontSize:16,fontWeight:'600'}});
