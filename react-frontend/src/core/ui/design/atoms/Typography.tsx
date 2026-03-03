import React from "react";

interface TypographyProps {
    children: React.ReactNode;
    variant: "h1" | "h2" | "h3" | "h4" | "label" | "small" | "eyebrow" | "gradient";
    className?: string;
    style?: React.CSSProperties;
}

export const Typography: React.FC<TypographyProps> = ({ children, variant, className = "", style }) => {
    switch (variant) {
        case "h1":
            return <h1 className={className} style={style}>{children}</h1>;
        case "h2":
            return <h2 className={className} style={style}>{children}</h2>;
        case "h3":
            return <h3 className={className} style={style}>{children}</h3>;
        case "h4":
            return <h4 className={className} style={style}>{children}</h4>;
        case "label":
            return <div className={`label ${className}`} style={style}>{children}</div>;
        case "small":
            return <p className={`small ${className}`} style={style}>{children}</p>;
        case "eyebrow":
            return <div className={`header-eyebrow ${className}`} style={style}>{children}</div>;
        case "gradient":
            return <h1 className={`gradient-title ${className}`} style={style}>{children}</h1>;
        default:
            return <span className={className} style={style}>{children}</span>;
    }
};
