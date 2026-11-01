import React, { useState } from 'react';
import {
    View,
    Text,
    TextInput,
    StyleSheet,
    TouchableOpacity,
    TextInputProps,
} from 'react-native';
import { Eye, EyeOff } from 'lucide-react-native';
import { Colors } from '../constants/colors';
import { FontFamily, FontSize } from '../constants/typography';

interface InputFieldProps extends TextInputProps {
    label: string;
    error?: string;
    secure?: boolean;
}

export default function InputField({
    label,
    error,
    secure = false,
    ...rest
}: InputFieldProps) {
    const [showPassword, setShowPassword] = useState(false);
    const isPassword = secure;

    return (
        <View style={styles.wrapper}>
            <Text style={styles.label}>{label}</Text>
            <View style={[styles.inputRow, error ? styles.inputError : styles.inputNormal]}>
                <TextInput
                    style={styles.input}
                    placeholderTextColor={Colors.mutedLight}
                    secureTextEntry={isPassword && !showPassword}
                    autoCapitalize={isPassword ? 'none' : rest.autoCapitalize}
                    autoCorrect={false}
                    {...rest}
                />
                {isPassword && (
                    <TouchableOpacity
                        onPress={() => setShowPassword(v => !v)}
                        hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
                        style={styles.eyeToggle}
                    >
                        {showPassword ? (
                            <EyeOff size={18} color={Colors.muted} />
                        ) : (
                            <Eye size={18} color={Colors.muted} />
                        )}
                    </TouchableOpacity>
                )}
            </View>
            {error ? <Text style={styles.errorText}>{error}</Text> : null}
        </View>
    );
}

const styles = StyleSheet.create({
    wrapper: {
        marginBottom: 16,
    },
    label: {
        fontSize: FontSize.sm,
        color: Colors.muted,
        fontFamily: FontFamily.sansMedium,
        marginBottom: 6,
        letterSpacing: 0.2,
    },
    inputRow: {
        flexDirection: 'row',
        alignItems: 'center',
        borderRadius: 12,
        borderWidth: 1.5,
        backgroundColor: Colors.inputBg,
        paddingHorizontal: 14,
        minHeight: 50,
    },
    inputNormal: {
        borderColor: Colors.inputBorder,
    },
    inputError: {
        borderColor: Colors.error,
    },
    input: {
        flex: 1,
        fontSize: FontSize.base,
        color: Colors.espresso,
        fontFamily: FontFamily.sansRegular,
        paddingVertical: 12,
    },
    eyeToggle: {
        paddingLeft: 8,
    },
    errorText: {
        color: Colors.error,
        fontSize: FontSize.xs,
        fontFamily: FontFamily.sansRegular,
        marginTop: 4,
        marginLeft: 2,
    },
});
