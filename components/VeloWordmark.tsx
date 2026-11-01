import React from 'react';
import { StyleSheet, Text, View } from 'react-native';
import Svg, { Defs, LinearGradient, Stop, Rect } from 'react-native-svg';

export default function VeloWordmark() {
  return <View style={styles.brand}>
    <Svg width={24} height={24} viewBox="0 0 24 24" style={styles.mark}>
      <Defs><LinearGradient id="veloMark" x1="0" y1="0" x2="1" y2="1"><Stop offset="0" stopColor="#142333"/><Stop offset="0.55" stopColor="#34511B"/><Stop offset="1" stopColor="#C4F52A"/></LinearGradient></Defs>
      <Rect x="0" y="0" width="24" height="24" rx="8" fill="url(#veloMark)" />
    </Svg>
    <Text style={styles.brandText}>velo</Text>
  </View>;
}

const styles=StyleSheet.create({brand:{alignSelf:'center',flexDirection:'row',alignItems:'center',gap:7},mark:{shadowColor:'#C4F52A',shadowOpacity:.25,shadowRadius:12},brandText:{fontSize:17,fontWeight:'600',letterSpacing:-.6,color:'#F5F7FA'}});
