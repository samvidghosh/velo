import React, { useState } from 'react';
import {
    View,
    Text,
    StyleSheet,
    TouchableOpacity,
    KeyboardAvoidingView,
    Platform,
    ScrollView,
    SafeAreaView,
    Alert,
} from 'react-native';
import { useRouter } from 'expo-router';
import { ArrowLeft } from 'lucide-react-native';
import { Colors } from '../constants/colors';
import { FontFamily, FontSize } from '../constants/typography';
import Button from '../components/Button';
import InputField from '../components/InputField';
import SocialAuthButton from '../components/SocialAuthButton';
import BotanicalDecor from '../components/BotanicalDecor';
import { mockSignIn } from '../auth/mockAuth';

function isValidEmail(email: string) {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim());
}

export default function LoginScreen() {
    const router = useRouter();

    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [emailError, setEmailError] = useState('');
    const [passwordError, setPasswordError] = useState('');
    const [serverError, setServerError] = useState('');
    const [loading, setLoading] = useState(false);

    const validate = () => {
        let valid = true;
        setEmailError('');
        setPasswordError('');
        setServerError('');

        if (!email.trim()) {
            setEmailError('Email is required.');
            valid = false;
        } else if (!isValidEmail(email)) {
            setEmailError('Please enter a valid email address.');
            valid = false;
        }
        if (!password) {
            setPasswordError('Password is required.');
            valid = false;
        }
        return valid;
    };

    const handleSignIn = async () => {
        if (!validate()) return;
        setLoading(true);
        const result = await mockSignIn(email.trim(), password);
        setLoading(false);
        if (result.error) {
            setServerError(result.error);
        } else {
            // TODO: Navigate to home screen after real auth
            alert(`Welcome back, ${result.user?.name}! (Mock auth successful)`);
        }
    };

    return (
        <SafeAreaView style={styles.safe}>
            {/* Botanical header decorations */}
            <View style={styles.topLeft} pointerEvents="none">
                <BotanicalDecor corner="topLeft" size={90} opacity={0.4} />
            </View>
            <View style={styles.topRight} pointerEvents="none">
                <BotanicalDecor corner="topRight" size={90} opacity={0.4} />
            </View>

            {/* Back arrow + wordmark header */}
            <View style={styles.header}>
                <TouchableOpacity onPress={() => router.back()} style={styles.backBtn} hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}>
                    <ArrowLeft size={22} color={Colors.espresso} />
                </TouchableOpacity>
                <Text style={styles.wordmark}>velo</Text>
                <View style={{ width: 38 }} />
            </View>

            <KeyboardAvoidingView
                behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
                style={styles.flex}
            >
                <ScrollView
                    contentContainerStyle={styles.scrollContent}
                    keyboardShouldPersistTaps="handled"
                    showsVerticalScrollIndicator={false}
                >
                    {/* Form panel */}
                    <View style={styles.panel}>
                        <Text style={styles.heading}>Welcome Back</Text>
                        <Text style={styles.subtitle}>Ready for your next session?</Text>

                        <View style={styles.form}>
                            <InputField
                                label="Email"
                                placeholder="Enter your email"
                                value={email}
                                onChangeText={t => { setEmail(t); setEmailError(''); setServerError(''); }}
                                keyboardType="email-address"
                                textContentType="emailAddress"
                                autoComplete="email"
                                autoCapitalize="none"
                                error={emailError}
                            />
                            <InputField
                                label="Password"
                                placeholder="Enter your password"
                                value={password}
                                onChangeText={t => { setPassword(t); setPasswordError(''); setServerError(''); }}
                                secure
                                textContentType="password"
                                autoComplete="current-password"
                                error={passwordError}
                            />

                            {/* Forgot password */}
            <TouchableOpacity style={styles.forgotWrap} onPress={() => Alert.alert('Password recovery unavailable', 'Connect an authentication provider to enable password recovery.')}>
                                <Text style={styles.forgotText}>Forgot Password?</Text>
                            </TouchableOpacity>

                            {/* Server error */}
                            {serverError ? <Text style={styles.serverError}>{serverError}</Text> : null}

                            <Button
                                label="Sign In"
                                onPress={handleSignIn}
                                loading={loading}
                                disabled={loading}
                                style={styles.mainBtn}
                            />

                            {/* Social auth */}
                            <View style={styles.dividerRow}>
                                <View style={styles.dividerLine} />
                                <Text style={styles.dividerText}>Or sign in with</Text>
                                <View style={styles.dividerLine} />
                            </View>

                            <View style={styles.socialRow}>
                                <SocialAuthButton provider="google" onPress={() => Alert.alert('Sign in unavailable', 'Google sign in is not configured for this app yet.')} />
                                <SocialAuthButton provider="apple" onPress={() => Alert.alert('Sign in unavailable', 'Apple sign in is not configured for this app yet.')} />
                            </View>

                            {/* Sign up link */}
                            <View style={styles.footerRow}>
                                <Text style={styles.footerText}>New to Velo? </Text>
                                <TouchableOpacity onPress={() => router.replace('/signup')}>
                                    <Text style={styles.footerLink}>Sign Up</Text>
                                </TouchableOpacity>
                            </View>
                        </View>
                    </View>
                </ScrollView>
            </KeyboardAvoidingView>
        </SafeAreaView>
    );
}

const styles = StyleSheet.create({
    safe: { flex: 1, backgroundColor: Colors.cream },
    flex: { flex: 1 },

    topLeft: { position: 'absolute', top: 0, left: 0, zIndex: 0 },
    topRight: { position: 'absolute', top: 0, right: 0, zIndex: 0 },

    header: {
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'space-between',
        paddingHorizontal: 20,
        paddingTop: 12,
        paddingBottom: 8,
        zIndex: 1,
    },
    backBtn: {
        width: 38,
        height: 38,
        alignItems: 'center',
        justifyContent: 'center',
    },
    wordmark: {
        fontFamily: FontFamily.serifBold,
        fontSize: FontSize.xl,
        color: Colors.espresso,
        letterSpacing: 5,
    },

    scrollContent: {
        flexGrow: 1,
        paddingHorizontal: 16,
        paddingBottom: 32,
    },

    panel: {
        backgroundColor: Colors.white,
        borderRadius: 28,
        paddingHorizontal: 24,
        paddingTop: 32,
        paddingBottom: 28,
        marginTop: 12,
        shadowColor: Colors.espresso,
        shadowOffset: { width: 0, height: 6 },
        shadowOpacity: 0.08,
        shadowRadius: 20,
        elevation: 6,
    },
    heading: {
        fontFamily: FontFamily.serifBold,
        fontSize: FontSize.xxl,
        color: Colors.espresso,
        marginBottom: 6,
    },
    subtitle: {
        fontFamily: FontFamily.sansRegular,
        fontSize: FontSize.sm,
        color: Colors.muted,
        marginBottom: 28,
        lineHeight: FontSize.sm * 1.5,
    },

    form: {},

    forgotWrap: { alignSelf: 'flex-end', marginTop: -6, marginBottom: 20 },
    forgotText: {
        fontFamily: FontFamily.sansMedium,
        fontSize: FontSize.sm,
        color: Colors.caramel,
    },

    serverError: {
        fontFamily: FontFamily.sansRegular,
        fontSize: FontSize.sm,
        color: Colors.error,
        textAlign: 'center',
        marginBottom: 12,
    },

    mainBtn: { width: '100%', marginBottom: 24 },

    dividerRow: {
        flexDirection: 'row',
        alignItems: 'center',
        marginBottom: 20,
    },
    dividerLine: {
        flex: 1,
        height: 1,
        backgroundColor: Colors.beige,
    },
    dividerText: {
        fontFamily: FontFamily.sansRegular,
        fontSize: FontSize.xs,
        color: Colors.mutedLight,
        marginHorizontal: 12,
    },

    socialRow: {
        flexDirection: 'row',
        justifyContent: 'center',
        gap: 16,
        marginBottom: 28,
    },

    footerRow: {
        flexDirection: 'row',
        justifyContent: 'center',
        alignItems: 'center',
    },
    footerText: {
        fontFamily: FontFamily.sansRegular,
        fontSize: FontSize.sm,
        color: Colors.muted,
    },
    footerLink: {
        fontFamily: FontFamily.sansSemiBold,
        fontSize: FontSize.sm,
        color: Colors.caramel,
    },
});
