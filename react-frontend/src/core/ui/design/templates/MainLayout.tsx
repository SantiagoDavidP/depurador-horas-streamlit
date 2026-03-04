import React from "react";
import { Typography } from "../atoms/Typography";
import { ThemeSwitch } from "../molecules/ThemeSwitch";

interface SidebarProps {
    theme: "light" | "dark";
    onThemeToggle: (isDark: boolean) => void;
    processingMode: "Individual" | "Por lotes";
    onModeChange: (mode: "Individual" | "Por lotes") => void;
    userInfo?: { name?: string; preferred_username?: string; displayName?: string; mail?: string; userPrincipalName?: string };
    children?: React.ReactNode;
}

export const MainLayout: React.FC<{
    sidebar: SidebarProps;
    children: React.ReactNode;
    volumeLabel: string;
    statusLabel: string;
    aiEnabled: boolean;
}> = ({ sidebar, children, volumeLabel, statusLabel, aiEnabled }) => {
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
                        <label className="flex">
                            <input
                                type="radio"
                                name="mode"
                                checked={sidebar.processingMode === "Individual"}
                                onChange={() => sidebar.onModeChange("Individual")}
                            />
                            Individual
                        </label>
                        <label className="flex" style={{ marginLeft: 16 }}>
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

                {sidebar.children}

                {sidebar.userInfo && (
                    <div className="sidebar-section" style={{ marginTop: "auto" }}>
                        <div className="brand-divider" style={{ marginBottom: 12 }} />
                        <Typography variant="h3">Usuario</Typography>
                        <div className="info-value" style={{ fontWeight: 600 }}>
                            {sidebar.userInfo.displayName || sidebar.userInfo.name || "Usuario"}
                        </div>
                        <div className="small" style={{ opacity: 0.7 }}>
                            {sidebar.userInfo.mail || sidebar.userInfo.userPrincipalName || ""}
                        </div>
                    </div>
                )}
            </aside>

            <main className="main-content main">
                <header className="header">
                    <div className="header-brand">
                        <div className="header-accent" aria-hidden="true" />
                        <div>
                            <div className="header-eyebrow">Business IT · Nova Analytics</div>
                            <h1 className="gradient-title">Depurador de Horas</h1>
                            <p className="header-subtitle">Valida y depura registros de timesheet automáticamente</p>
                        </div>
                    </div>
                    <div className="header-status">
                        <div className="status-pill">
                            <span className="status-label-inline">Modo</span>
                            <span className="status-value-inline">{sidebar.processingMode}</span>
                        </div>
                        <div className="status-pill">
                            <span className="status-label-inline">IA</span>
                            <span className="status-value-inline">
                                <span className={`status-dot ${aiEnabled ? "on" : "off"}`} />
                                {aiEnabled ? "Activa" : "Inactiva"}
                            </span>
                        </div>
                        <div className="status-pill">
                            <span className="status-label-inline">Carga</span>
                            <span className="status-value-inline">
                                {volumeLabel} · {statusLabel}
                            </span>
                        </div>
                    </div>
                </header>

                {children}
            </main>
        </div>
    );
};

