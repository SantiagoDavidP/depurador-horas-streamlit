import React from "react";

interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
    options: { value: string; label: string }[];
}

export const Select: React.FC<SelectProps> = ({ options, className = "", ...props }) => {
    return (
        <select className={`input ${className}`} {...props}>
            {options.map((opt) => (
                <option key={opt.value} value={opt.value}>
                    {opt.label}
                </option>
            ))}
        </select>
    );
};
