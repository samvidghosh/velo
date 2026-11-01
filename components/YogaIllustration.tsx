import React from 'react';
import Svg, {
    Path, Circle, Ellipse,
} from 'react-native-svg';
import { Colors } from '../constants/colors';

interface Props {
    width?: number;
    height?: number;
}

/**
 * Soft editorial SVG illustration of a woman in a yoga warrior pose.
 * Styled with the Velo warm cream/beige/caramel/sage palette.
 */
export default function YogaIllustration({ width = 280, height = 280 }: Props) {
    const w = width;
    const h = height;

    return (
        <Svg
            width={w}
            height={h}
            viewBox="0 0 280 280"
        >
            {/* Background soft circle */}
            <Circle cx="140" cy="145" r="105" fill={Colors.beigeLight} opacity="0.5" />
            <Circle cx="140" cy="145" r="80" fill={Colors.beige} opacity="0.3" />

            {/* Ground / mat */}
            <Ellipse cx="140" cy="228" rx="90" ry="8" fill={Colors.beige} opacity="0.6" />

            {/* === BODY (Warrior II pose — arms extended) === */}

            {/* Back leg */}
            <Path
                d="M 108 190 L 88 228"
                stroke={Colors.espresso}
                strokeWidth="7"
                strokeLinecap="round"
            />
            {/* Back foot */}
            <Path
                d="M 88 228 L 73 228"
                stroke={Colors.espresso}
                strokeWidth="6"
                strokeLinecap="round"
            />

            {/* Front leg */}
            <Path
                d="M 158 190 L 168 228"
                stroke={Colors.espresso}
                strokeWidth="7"
                strokeLinecap="round"
            />
            {/* Front foot */}
            <Path
                d="M 168 228 L 185 228"
                stroke={Colors.espresso}
                strokeWidth="6"
                strokeLinecap="round"
            />

            {/* Torso */}
            <Path
                d="M 108 190 Q 133 195 158 190"
                stroke={Colors.espresso}
                strokeWidth="7"
                strokeLinecap="round"
                fill="none"
            />
            <Path
                d="M 133 190 L 133 148"
                stroke={Colors.espresso}
                strokeWidth="6.5"
                strokeLinecap="round"
            />

            {/* Left arm (extended back-left) */}
            <Path
                d="M 133 158 L 82 148"
                stroke={Colors.espresso}
                strokeWidth="5.5"
                strokeLinecap="round"
            />
            {/* Left hand */}
            <Circle cx="79" cy="147" r="5" fill={Colors.caramel} opacity="0.8" />

            {/* Right arm (extended forward-right) */}
            <Path
                d="M 133 158 L 192 148"
                stroke={Colors.espresso}
                strokeWidth="5.5"
                strokeLinecap="round"
            />
            {/* Right hand */}
            <Circle cx="195" cy="147" r="5" fill={Colors.caramel} opacity="0.8" />

            {/* Neck */}
            <Path
                d="M 133 148 L 133 138"
                stroke={Colors.espresso}
                strokeWidth="5"
                strokeLinecap="round"
            />

            {/* Head */}
            <Circle cx="133" cy="126" r="17" fill={Colors.caramel} opacity="0.85" />

            {/* Hair */}
            <Path
                d="M 119 120 Q 120 105 133 108 Q 148 105 148 120"
                stroke={Colors.espresso}
                strokeWidth="3"
                fill={Colors.espresso}
                opacity="0.7"
            />
            {/* Bun */}
            <Circle cx="144" cy="112" r="6" fill={Colors.espresso} opacity="0.6" />

            {/* Face details */}
            <Circle cx="128" cy="126" r="2" fill={Colors.espresso} opacity="0.5" />
            <Circle cx="138" cy="126" r="2" fill={Colors.espresso} opacity="0.5" />
            {/* Smile */}
            <Path
                d="M 128 133 Q 133 137 138 133"
                stroke={Colors.espresso}
                strokeWidth="1.5"
                strokeLinecap="round"
                fill="none"
                opacity="0.5"
            />

            {/* Clothing — leggings fill */}
            <Path
                d="M 108 190 Q 133 200 158 190 L 168 228 L 185 228 L 175 192 Q 158 185 140 188 Q 122 185 108 192 L 88 228 L 73 228 Z"
                fill={Colors.caramel}
                opacity="0.55"
            />

            {/* Top */}
            <Path
                d="M 118 148 Q 133 154 148 148 L 155 175 Q 133 180 111 175 Z"
                fill={Colors.muted}
                opacity="0.5"
            />

            {/* Decorative small leaves around */}
            <Path
                d="M 55 80 Q 60 65 75 72 Q 62 78 55 80 Z"
                fill={Colors.success}
                opacity="0.35"
            />
            <Path
                d="M 62 95 Q 50 85 55 70 Q 60 90 62 95 Z"
                fill={Colors.success}
                opacity="0.25"
            />
            <Path
                d="M 215 90 Q 220 74 235 80 Q 218 84 215 90 Z"
                fill={Colors.success}
                opacity="0.35"
            />
            <Path
                d="M 218 105 Q 230 90 238 95 Q 222 100 218 105 Z"
                fill={Colors.success}
                opacity="0.25"
            />

            {/* Subtle sparkle dots */}
            <Circle cx="68" cy="120" r="3" fill={Colors.caramel} opacity="0.3" />
            <Circle cx="210" cy="115" r="3" fill={Colors.caramel} opacity="0.3" />
            <Circle cx="100" cy="70" r="2" fill={Colors.mutedLight} opacity="0.4" />
            <Circle cx="180" cy="75" r="2" fill={Colors.mutedLight} opacity="0.4" />
        </Svg>
    );
}
