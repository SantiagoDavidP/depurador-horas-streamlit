import React from "react";
import { Typography } from "../atoms/Typography";
import { InfoItem } from "../molecules/InfoItem";
import { ThemeSwitch } from "../molecules/ThemeSwitch";

interface SidebarProps {
    theme: "light" | "dark";
    onThemeToggle: (isDark: boolean) => void;
    processingMode: "Individual" | "Por lotes";
    onModeChange: (mode: "Individual" | "Por lotes") => void;
    volumeLabel: string;
    statusLabel: string;
    userInfo?: { name?: string; preferred_username?: string };
    children?: React.ReactNode;
}

export const MainLayout: React.FC<{
    sidebar: SidebarProps;
    children: React.ReactNode;
    headerTitle: string;
}> = ({ sidebar, children, headerTitle }) => {
    return (
        <div className={`app ${sidebar.theme === "dark" ? "theme-dark" : ""}`}>
            <aside className="sidebar">
                <div className="brand">
                    <div className="brand-logo-wrap">
                        <img src="/logobit.png" className="brand-logo" alt="Business IT" />
                    </div>
                    <div className="brand-text">
                        <Typography variant="eyebrow" className="brand-subtitle">Timesheet Intelligence</Typography>
                    </div>
                </div>
                <div className="brand-divider" />

                <div className="sidebar-section">
                    <Typography variant="h3">Apariencia</Typography>
                    <ThemeSwitch
                        theme={sidebar.theme}
                        onToggle={sidebar.onThemeToggle}
                    />
                </div>

                <div className="sidebar-section">
                    <Typography variant="h3" style={{ marginBottom: 8 }}>Configuración</Typography>
                    <Typography variant="label">Modo</Typography>
                    <div className="flex">
                        <label>
                            <input
                                type="radio"
                                name="mode"
                                checked={sidebar.processingMode === "Individual"}
                                onChange={() => sidebar.onModeChange("Individual")}
                            />
                            Individual
                        </label>
                        <label style={{ marginLeft: 16 }}>
                            <input
                                type="radio"
                                name="mode"
                                checked={sidebar.processingMode === "Por lotes"}
                                onChange={() => sidebar.onModeChange("Por lotes")}
                            />
                            Por lotes
                        </label>
                    </div>
                </div>

                <div className="sidebar-section">
                    <Typography variant="h3" style={{ marginBottom: 8 }}>Estado</Typography>
                    <div className="info-grid">
                        <InfoItem label="Volumen" value={sidebar.volumeLabel} />
                        <InfoItem label="Carga" value={sidebar.statusLabel} />
                    </div>
                </div>

                {sidebar.children}

                {sidebar.userInfo && (
                    <div className="sidebar-section" style={{ marginTop: "auto" }}>
                        <div className="info-value" style={{ fontSize: 13, opacity: 0.7 }}>
                            {String(sidebar.userInfo.name || sidebar.userInfo.preferred_username || "")}
                        </div>
                    </div>
                )}
            </aside>

            <main className="main-content main">
                <header className="header">
                    <Typography variant="gradient">{headerTitle}</Typography>
                    <div className="flex" style={{ gap: 12 }}>
                        {/* Header Actions */}
                    </div>
                </header>

                {children}
            </main>
        </div>
    );
};
