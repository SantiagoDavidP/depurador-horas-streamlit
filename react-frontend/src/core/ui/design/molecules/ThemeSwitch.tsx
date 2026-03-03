import React from "react";
import { Typography } from "../atoms/Typography";

interface ThemeSwitchProps {
    theme: "light" | "dark";
    onToggle: (isDark: boolean) => void;
}

export const ThemeSwitch: React.FC<ThemeSwitchProps> = ({ theme, onToggle }) => {
    const isDark = theme === "dark";

    return (
        <div className="theme-switch-container">
            <div
                className={`theme-switch ${isDark ? "active" : ""}`}
                onClick={() => onToggle(!isDark)}
            >
                <span className="theme-switch-text theme-switch-text-light">Tema Claro</span>
                <span className="theme-switch-text theme-switch-text-dark">Tema Oscuro</span>
                <div className="theme-switch-handle">
                    {isDark ? (
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="theme-icon">
                            <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
                        </svg>
                    ) : (
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="theme-icon">
                            <circle cx="12" cy="12" r="5" />
                            <line x1="12" y1="1" x2="12" y2="3" />
                            <line x1="12" y1="21" x2="12" y2="23" />
                            <line x1="4.22" y1="4.22" x2="5.64" y2="5.64" />
                            <line x1="18.36" y1="18.36" x2="19.78" y2="19.78" />
                            <line x1="1" y1="12" x2="3" y2="12" />
                            <line x1="21" y1="12" x2="23" y2="12" />
                            <line x1="4.22" y1="19.78" x2="5.64" y2="18.36" />
                            <line x1="18.36" y1="5.64" x2="19.78" y2="4.22" />
                        </svg>
                    )}
                </div>
            </div>
        </div>
    );
};
