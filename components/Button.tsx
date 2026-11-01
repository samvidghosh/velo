import React from 'react';
import {
    TouchableOpacity,
    Text,
    StyleSheet,
    ActivityIndicator,
    StyleProp,
    ViewStyle,
    TextStyle,
} from 'react-native';
import { Colors } from '../constants/colors';
import { FontFamily, FontSize } from '../constants/typography';

export type ButtonVariant = 'primary' | 'secondary';

interface ButtonProps {
    label: string;
    onPress: () => void;
    variant?: ButtonVariant;
    loading?: boolean;
    disabled?: boolean;
    style?: StyleProp<ViewStyle>;
    textStyle?: StyleProp<TextStyle>;
}

export default function Button({
    label,
    onPress,
    variant = 'primary',
    loading = false,
    disabled = false,
    style,
    textStyle,
}: ButtonProps) {
    const isPrimary = variant === 'primary';
    const isDisabled = disabled || loading;

    return (
        <TouchableOpacity
            onPress={onPress}
            disabled={isDisabled}
            activeOpacity={0.78}
            style={[
                styles.base,
                isPrimary ? styles.primary : styles.secondary,
                isDisabled && styles.disabled,
                style,
            ]}
        >
            {loading ? (
                <ActivityIndicator
                    color={isPrimary ? Colors.veloCanvas : Colors.espresso}
                    size="small"
                />
            ) : (
                <Text
                    style={[
                        styles.label,
                        isPrimary ? styles.labelPrimary : styles.labelSecondary,
                        textStyle,
                    ]}
                >
                    {label}
                </Text>
            )}
        </TouchableOpacity>
    );
}

const styles = StyleSheet.create({
    base: {
        height: 52,
        borderRadius: 30,
        alignItems: 'center',
        justifyContent: 'center',
        paddingHorizontal: 24,
    },
    primary: {
        backgroundColor: Colors.caramel,
        shadowColor: Colors.caramel,
        shadowOffset: { width: 0, height: 4 },
        shadowOpacity: 0.28,
        shadowRadius: 8,
        elevation: 4,
    },
    secondary: {
        backgroundColor: Colors.white,
        borderWidth: 1.5,
        borderColor: Colors.inputBorder,
        shadowColor: Colors.espresso,
        shadowOffset: { width: 0, height: 2 },
        shadowOpacity: 0.07,
        shadowRadius: 6,
        elevation: 2,
    },
    disabled: {
        opacity: 0.55,
    },
    label: {
        fontSize: FontSize.base,
        letterSpacing: 0.3,
    },
    labelPrimary: {
        color: Colors.veloCanvas,
        fontFamily: FontFamily.sansSemiBold,
    },
    labelSecondary: {
        color: Colors.espresso,
        fontFamily: FontFamily.sansMedium,
    },
});
