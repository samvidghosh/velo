export const FontFamily = {
    // Leave fontFamily unset so iOS and Android use their native system sans.
    serifBold: undefined,
    serifMedium: undefined,
    serifRegular: undefined,
    serifItalic: undefined,
    sansRegular: undefined,
    sansMedium: undefined,
    sansSemiBold: undefined,
} as const;

export const FontSize = {
    xs: 11,
    sm: 13,
    base: 15,
    md: 17,
    lg: 20,
    xl: 24,
    xxl: 30,
    xxxl: 38,
} as const;

export const LineHeight = {
    tight: 1.2,
    normal: 1.5,
    relaxed: 1.7,
} as const;
