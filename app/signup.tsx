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
import { ArrowLeft, Check } from 'lucide-react-native';
import { Colors } from '../constants/colors';
import { FontFamily, FontSize } from '../constants/typography';
import Button from '../components/Button';
import InputField from '../components/InputField';
import SocialAuthButton from '../components/SocialAuthButton';
import BotanicalDecor from '../components/BotanicalDecor';
import { mockSignUp } from '../auth/mockAuth';

function isValidEmail(email: string) {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim());
}

export default function SignUpScreen() {
    const router = useRouter();

    const [name, setName] = useState('');
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [step, setStep] = useState<1 | 2>(1);
    const [agreed, setAgreed] = useState(false);

    const [nameError, setNameError] = useState('');
    const [emailError, setEmailError] = useState('');
    const [passwordError, setPasswordError] = useState('');
    const [agreeError, setAgreeError] = useState('');
    const [serverError, setServerError] = useState('');
    const [loading, setLoading] = useState(false);

    const clearErrors = () => {
        setNameError('');
        setEmailError('');
        setPasswordError('');
        setAgreeError('');
        setServerError('');
    };

    const validate = () => {
        clearErrors();
        let valid = true;

        if (step === 2 && !name.trim()) { setNameError('Name is required.'); valid = false; }
        if (step === 1 && !email.trim()) {
            setEmailError('Email is required.'); valid = false;
        } else if (step === 1 && !isValidEmail(email)) {
            setEmailError('Please enter a valid email address.'); valid = false;
        }
        if (step === 2 && !password) {
            setPasswordError('Password is required.'); valid = false;
        } else if (step === 2 && password.length < 6) {
            setPasswordError('Password must be at least 6 characters.'); valid = false;
        }
        if (step === 1 && !agreed) { setAgreeError('Please agree to the Terms and Conditions.'); valid = false; }
        if (step === 2 && password !== confirmPassword) { setPasswordError('Passwords do not match.'); valid = false; }

        return valid;
    };

    const handleCreateAccount = async () => {
        if (!validate()) return;
        if (step === 1) { setStep(2); return; }
        setLoading(true);
        const result = await mockSignUp(name.trim(), email.trim(), password);
        setLoading(false);
        if (result.error) {
            setServerError(result.error);
        } else {
            router.replace('/onboarding' as never);
        }
    };

    return (
        <SafeAreaView style={styles.safe}>
            {/* Botanical header */}
            <View style={styles.topLeft} pointerEvents="none">
                <BotanicalDecor corner="topLeft" size={90} opacity={0.4} />
            </View>
            <View style={styles.topRight} pointerEvents="none">
                <BotanicalDecor corner="topRight" size={90} opacity={0.4} />
            </View>

            {/* Header row */}
            <View style={styles.header}>
                <TouchableOpacity onPress={() => step === 2 ? setStep(1) : router.back()} style={styles.backBtn} hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}>
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
                        <Text style={styles.heading}>{step === 1 ? 'Sign up' : 'Finish signing up'}</Text>
                        <Text style={styles.subtitle}>{step === 1 ? 'Create your Velo account with your email.' : `Complete your account for ${email}.`}</Text>

                        <View style={styles.form}>
                            {step === 2 ? <InputField
                                label="First name"
                                placeholder="Enter your first name"
                                value={name}
                                onChangeText={t => { setName(t); setNameError(''); }}
                                autoCapitalize="words"
                                error={nameError}
                            /> : null}
                            {step === 1 ? <InputField
                                label="Email"
                                placeholder="Enter your email"
                                value={email}
                                onChangeText={t => { setEmail(t); setEmailError(''); setServerError(''); }}
                                keyboardType="email-address"
                                textContentType="emailAddress"
                                autoComplete="email"
                                autoCapitalize="none"
                                error={emailError}
                            /> : null}
                            {step === 2 ? <InputField
                                label="Password"
                                placeholder="Create a password"
                                value={password}
                                onChangeText={t => { setPassword(t); setPasswordError(''); }}
                                secure
                                textContentType="newPassword"
                                autoComplete="new-password"
                                error={passwordError}
                            /> : null}
                            {step === 2 ? <InputField
                                label="Repeat password"
                                placeholder="Repeat your password"
                                value={confirmPassword}
                                onChangeText={setConfirmPassword}
                                secure
                                textContentType="newPassword"
                                autoComplete="new-password"
                            /> : null}
                            {/* Terms checkbox */}
                            {step === 1 ? <TouchableOpacity
                                onPress={() => { setAgreed(v => !v); setAgreeError(''); }}
                                activeOpacity={0.7}
                                style={styles.checkboxRow}
                            >
                                <View style={[styles.checkbox, agreed && styles.checkboxChecked]}>
                                    {agreed && <Check size={12} color={Colors.white} strokeWidth={3} />}
                                </View>
                                <Text style={styles.checkboxLabel}>
                                    I agree to the{' '}
                                    <Text onPress={() => Alert.alert('Terms unavailable', 'The Terms URL has not been configured yet.')} style={styles.termsLink}>Terms</Text>{' '}and{' '}
                                    <Text onPress={() => Alert.alert('Privacy unavailable', 'The Privacy Policy URL has not been configured yet.')} style={styles.termsLink}>Privacy Policy</Text>.
                                </Text>
                            </TouchableOpacity> : null}
                            {agreeError ? <Text style={styles.agreeError}>{agreeError}</Text> : null}

                            {/* Server error */}
                            {serverError ? <Text style={styles.serverError}>{serverError}</Text> : null}

                            <Button
                                label={step === 1 ? 'Continue' : 'Create account'}
                                onPress={handleCreateAccount}
                                loading={loading}
                                disabled={loading || (step === 1 && (!isValidEmail(email) || !agreed))}
                                style={styles.mainBtn}
                            />

                            {/* Social auth */}
                            {step === 1 ? <View style={styles.dividerRow}>
                                <View style={styles.dividerLine} />
                                <Text style={styles.dividerText}>Or sign up with</Text>
                                <View style={styles.dividerLine} />
                            </View> : null}

                            {step === 1 ? <View style={styles.socialRow}>
                                <SocialAuthButton provider="google" onPress={() => Alert.alert('Sign up unavailable', 'Google sign in is not configured for this app yet.')} />
                                <SocialAuthButton provider="apple" onPress={() => Alert.alert('Sign up unavailable', 'Apple sign in is not configured for this app yet.')} />
                            </View> : null}

                            {/* Sign in link */}
                            <View style={styles.footerRow}>
                                <Text style={styles.footerText}>Already have an account? </Text>
                                <TouchableOpacity onPress={() => router.replace('/login')}>
                                    <Text style={styles.footerLink}>Sign In</Text>
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

    checkboxRow: {
        flexDirection: 'row',
        alignItems: 'center',
        marginBottom: 6,
        marginTop: 4,
    },
    checkbox: {
        width: 20,
        height: 20,
        borderRadius: 5,
        borderWidth: 1.5,
        borderColor: Colors.inputBorder,
        backgroundColor: Colors.inputBg,
        alignItems: 'center',
        justifyContent: 'center',
        marginRight: 10,
    },
    checkboxChecked: {
        backgroundColor: Colors.caramel,
        borderColor: Colors.caramel,
    },
    checkboxLabel: {
        fontFamily: FontFamily.sansRegular,
        fontSize: FontSize.sm,
        color: Colors.muted,
        flex: 1,
        lineHeight: FontSize.sm * 1.5,
    },
    termsLink: {
        color: Colors.caramel,
        fontFamily: FontFamily.sansMedium,
    },

    agreeError: {
        fontFamily: FontFamily.sansRegular,
        fontSize: FontSize.xs,
        color: Colors.error,
        marginBottom: 14,
        marginLeft: 2,
    },

    serverError: {
        fontFamily: FontFamily.sansRegular,
        fontSize: FontSize.sm,
        color: Colors.error,
        textAlign: 'center',
        marginBottom: 12,
    },

    mainBtn: { width: '100%', marginTop: 16, marginBottom: 24 },

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
