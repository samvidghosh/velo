import React from 'react';
import Svg, { Path, Circle, G } from 'react-native-svg';
import { Colors } from '../constants/colors';

type Corner = 'topLeft' | 'topRight' | 'bottomLeft' | 'bottomRight';

interface Props {
    corner: Corner;
    size?: number;
    opacity?: number;
}

/**
 * Delicate botanical line-art corner decoration.
 * Rendered entirely via SVG — no external image assets.
 */
export default function BotanicalDecor({ corner, size = 110, opacity = 0.55 }: Props) {
    const transforms: Record<Corner, string> = {
        topLeft: '',
        topRight: `translate(${size}, 0) scale(-1, 1)`,
        bottomLeft: `translate(0, ${size}) scale(1, -1)`,
        bottomRight: `translate(${size}, ${size}) scale(-1, -1)`,
    };

    return (
        <Svg width={size} height={size} viewBox="0 0 110 110" opacity={opacity}>
            <G transform={transforms[corner]}>
                {/* Main stem curving out from corner */}
                <Path
                    d="M 5 5 Q 5 55 55 105"
                    stroke={Colors.caramel}
                    strokeWidth="1.2"
                    fill="none"
                    strokeLinecap="round"
                />
                <Path
                    d="M 5 5 Q 55 5 105 55"
                    stroke={Colors.caramel}
                    strokeWidth="1.2"
                    fill="none"
                    strokeLinecap="round"
                />

                {/* Branch 1 — large leaf off vertical stem */}
                <Path
                    d="M 10 28 Q 28 18 38 30 Q 22 34 10 28 Z"
                    fill={Colors.success}
                    opacity="0.5"
                />
                <Path
                    d="M 10 28 Q 24 26 38 30"
                    stroke={Colors.caramel}
                    strokeWidth="0.8"
                    fill="none"
                    opacity="0.6"
                />

                {/* Branch 2 — small leaf off horizontal stem */}
                <Path
                    d="M 30 9 Q 30 28 42 32 Q 28 24 30 9 Z"
                    fill={Colors.success}
                    opacity="0.5"
                />
                <Path
                    d="M 30 9 Q 36 22 42 32"
                    stroke={Colors.caramel}
                    strokeWidth="0.8"
                    fill="none"
                    opacity="0.6"
                />

                {/* Branch 3 — medium leaf mid-stem */}
                <Path
                    d="M 18 52 Q 40 42 48 56 Q 30 56 18 52 Z"
                    fill={Colors.beige}
                    opacity="0.7"
                />

                {/* Branch 4 — horizontal medium leaf */}
                <Path
                    d="M 52 18 Q 52 40 66 48 Q 56 34 52 18 Z"
                    fill={Colors.beige}
                    opacity="0.7"
                />

                {/* Small berries / buds */}
                <Circle cx="40" cy="29" r="3" fill={Colors.caramel} opacity="0.5" />
                <Circle cx="30" cy="8" r="3" fill={Colors.caramel} opacity="0.5" />
                <Circle cx="52" cy="56" r="2.5" fill={Colors.mutedLight} opacity="0.6" />
                <Circle cx="66" cy="48" r="2.5" fill={Colors.mutedLight} opacity="0.6" />

                {/* Tiny accent dots */}
                <Circle cx="20" cy="20" r="1.5" fill={Colors.caramel} opacity="0.4" />
                <Circle cx="60" cy="10" r="1.5" fill={Colors.caramel} opacity="0.4" />
                <Circle cx="8" cy="60" r="1.5" fill={Colors.caramel} opacity="0.4" />
            </G>
        </Svg>
    );
}
