import React from "react";

interface ToggleProps extends React.InputHTMLAttributes<HTMLInputElement> {
    label?: string;
}

export const Toggle: React.FC<ToggleProps> = ({ label, className = "", ...props }) => {
    return (
        <div className={`toggle ${className}`}>
            <input type="checkbox" {...props} />
            {label && <span>{label}</span>}
        </div>
    );
};
