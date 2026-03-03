import React from "react";

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
    variant?: "primary" | "outline" | "text" | "primary-big";
    fullWidth?: boolean;
}

export const Button: React.FC<ButtonProps> = ({
    children,
    variant = "primary",
    fullWidth = false,
    className = "",
    ...props
}) => {
    const baseClass = "button";
    const variantClass = variant === "primary" ? "primary" :
        variant === "outline" ? "outline" :
            variant === "text" ? "button-text" :
                variant === "primary-big" ? "primary big" : "";
    const fullWidthClass = fullWidth ? "full" : "";

    return (
        <button
            className={`${baseClass} ${variantClass} ${fullWidthClass} ${className}`}
            {...props}
        >
            {children}
        </button>
    );
};
