import React, { useState } from 'react';
import { ImageBackground, SafeAreaView, StatusBar, StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import { useRouter } from 'expo-router';
import { Colors } from '../constants/colors';

const slides = [
  { title: 'Understand how\nyou move.', body: 'Velo turns your running video into a clear picture of your form, then helps you build strength with exercises made for you.', image: require('../assets/running/runner-gait-reference.png'), action: 'Let’s start' },
  { title: 'How will you use Velo?', body: 'Choose the path that best describes you.', choices: ['Runner · for my own training', 'Coach · for my athletes', 'Medical professional · for movement support'] },
  { title: 'Choose your path', body: 'What would you like to focus on?', choices: ['Improve fitness and performance', 'Learn about my running form', 'Reduce my injury risk'] },
  { title: 'Lab-quality analysis.', body: 'Ever wondered what a full analysis of your running form can reveal?', image: require('../assets/running/velo-lab-treadmill.png') },
  { title: 'Game time!', body: 'How much do you think a running analysis in a laboratory costs?', choices: ['₹2,500', '₹5,000', '₹15,000'], quiz: true },
  { title: 'Anytime, anywhere.', body: 'Whether on a treadmill, track, or road, check your form with Velo.', image: require('../assets/running/velo-anytime-road.png') },
  { title: 'Personalized analysis.', body: 'Velo personalizes your analysis by scanning your running form.\n\nTell us more about you.' },
  { title: 'How would you identify yourself?', body: 'Choose an option if you’d like to personalize your experience.', choices: ['Man', 'Woman', 'Non-binary', 'Prefer not to say'] },
  { title: 'How would you rate your level in running?', body: 'You can change this later.', choices: ['Beginner', 'Intermediate', 'Advanced', 'Elite'] },
];

export default function OnboardingScreen() {
  const router = useRouter();
  const [step, setStep] = useState(0);
  const [answers, setAnswers] = useState<Record<number, string>>({});
  const [quizRevealed, setQuizRevealed] = useState(false);
  const slide = slides[step];
  const advance = () => {
    if (step === slides.length - 1) router.replace('/analysis' as never);
    else setStep(v => v + 1);
  };
  const skip = () => { setAnswers(v => { const n={...v}; delete n[step]; return n; }); advance(); };
  return <SafeAreaView style={styles.safe}><StatusBar barStyle="light-content" />
    <View style={styles.progress}><View style={[styles.progressFill,{width:`${((step+1)/slides.length)*100}%`}]} /></View>
    {slide.image ? <ImageBackground source={slide.image} resizeMode="cover" style={StyleSheet.absoluteFill} /> : null}
    <View style={[StyleSheet.absoluteFill, styles.scrim]} />
    <View style={styles.header}><Text style={styles.wordmark}>velo</Text><Text style={styles.step}>{step+1} / {slides.length}</Text></View>
    <View style={styles.content}>
      <Text style={styles.title}>{slide.title}</Text><Text style={styles.body}>{slide.body}</Text>
      {slide.choices?.map(choice => {
        const selected=answers[step]===choice;
        const correct=slide.quiz && quizRevealed && choice==='₹15,000';
        const incorrect=slide.quiz && quizRevealed && selected && !correct;
        return <TouchableOpacity key={choice} accessibilityRole="radio" accessibilityState={{selected}} style={[styles.option,selected&&styles.selected,correct&&styles.correct,incorrect&&styles.incorrect]} onPress={()=>{setAnswers(v=>({...v,[step]:choice})); if(slide.quiz)setQuizRevealed(true);}}><Text style={styles.optionText}>{choice}</Text></TouchableOpacity>;
      })}
      {slide.quiz&&quizRevealed?<Text style={styles.quizNote}>Prices vary by provider and testing depth. ₹15,000 is the reference answer for a comprehensive biomechanical profile.</Text>:null}
    </View>
    <View style={styles.footer}>
      {step===0?<TouchableOpacity onPress={advance} style={styles.primary}><Text style={styles.primaryText}>{slide.action}</Text></TouchableOpacity>:<>
        <TouchableOpacity onPress={()=>{if(step>0)setStep(v=>v-1);else router.back();}} style={styles.back}><Text style={styles.backText}>Back</Text></TouchableOpacity>
        {(step===1||step===2||step===4)?<TouchableOpacity onPress={skip} style={styles.skip}><Text style={styles.skipText}>Skip</Text></TouchableOpacity>:null}
        <TouchableOpacity disabled={!!slide.choices&&!answers[step]&&!slide.quiz} onPress={advance} style={[styles.primary,!!slide.choices&&!answers[step]&&!slide.quiz&&styles.disabled]}><Text style={styles.primaryText}>{step===slides.length-1?'Continue':'Next'}</Text></TouchableOpacity>
      </>}
    </View>
  </SafeAreaView>;
}

const styles=StyleSheet.create({safe:{flex:1,backgroundColor:Colors.veloCanvas},progress:{position:'absolute',top:0,left:0,right:0,height:3,zIndex:2,backgroundColor:'#4b553b'},progressFill:{height:3,backgroundColor:Colors.veloLime},scrim:{backgroundColor:'rgba(9,15,8,0.55)'},header:{paddingHorizontal:24,paddingTop:20,flexDirection:'row',justifyContent:'space-between',alignItems:'center'},wordmark:{fontSize:27,fontWeight:'700',letterSpacing:4,color:Colors.veloText},step:{color:'#d1d6c8',fontSize:13},content:{flex:1,justifyContent:'center',paddingHorizontal:24},title:{color:Colors.veloText,fontSize:32,fontWeight:'700',lineHeight:39,marginBottom:14},body:{color:'#e0e3db',fontSize:16,lineHeight:24,marginBottom:24},option:{minHeight:54,borderRadius:16,borderColor:'rgba(255,255,255,0.28)',borderWidth:1,paddingHorizontal:17,justifyContent:'center',marginBottom:10,backgroundColor:'rgba(18,29,16,0.78)'},selected:{borderColor:Colors.veloLime,backgroundColor:'rgba(196,245,42,0.15)'},correct:{borderColor:'#9de19c'},incorrect:{borderColor:'#ff6b61'},optionText:{color:Colors.veloText,fontSize:15,fontWeight:'600'},quizNote:{color:'#e7edda',fontSize:13,lineHeight:19,marginTop:8},footer:{minHeight:88,paddingHorizontal:20,paddingBottom:14,flexDirection:'row',alignItems:'center',justifyContent:'center',gap:10},primary:{height:52,minWidth:128,flex:1,maxWidth:250,borderRadius:28,backgroundColor:Colors.veloLime,alignItems:'center',justifyContent:'center'},primaryText:{color:Colors.veloCanvas,fontSize:16,fontWeight:'700'},back:{height:52,minWidth:88,paddingHorizontal:18,borderRadius:28,borderWidth:1,borderColor:'rgba(255,255,255,0.35)',alignItems:'center',justifyContent:'center'},backText:{color:Colors.veloText,fontSize:16,fontWeight:'600'},skip:{height:48,paddingHorizontal:8,justifyContent:'center'},skipText:{color:'#d6ddca',fontSize:14},disabled:{opacity:.4}});
