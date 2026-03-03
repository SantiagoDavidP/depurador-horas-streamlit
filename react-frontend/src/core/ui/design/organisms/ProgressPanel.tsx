import React from "react";
import { Typography } from "../atoms/Typography";
import { ProgressTrack } from "../molecules/ProgressTrack";

interface ProgressPanelProps {
    title: string;
    detail: string;
    seconds: number;
    pct: number;
    currentLabel?: string;
    currentIndex?: number;
    total?: number;
    noPadding?: boolean;
}

export const ProgressPanel: React.FC<ProgressPanelProps> = ({
    title,
    detail,
    seconds,
    pct,
    currentLabel,
    currentIndex,
    total,
    noPadding = false,
}) => {
    const formatDuration = (secs: number) => {
        if (!secs || secs < 0) return "0:00";
        const mins = Math.floor(secs / 60);
        const s = secs % 60;
        return `${mins}:${s.toString().padStart(2, "0")}`;
    };

    return (
        <div className={`progress-panel ${noPadding ? "progress-panel-no-padding" : ""}`}>
            <div className={noPadding ? "card-text-content" : "progress-head"}>
                {noPadding ? (
                    <div className="progress-head" style={{ marginBottom: 0 }}>
                        <div>
                            <Typography variant="h4" className="progress-title">{title}</Typography>
                            <div className="progress-subtitle">{detail}</div>
                        </div>
                        <div className="progress-time">Tiempo: {formatDuration(seconds)}</div>
                    </div>
                ) : (
                    <>
                        <div>
                            <Typography variant="h4" className="progress-title">{title}</Typography>
                            <div className="progress-subtitle">{detail}</div>
                        </div>
                        <div className="progress-time">Tiempo: {formatDuration(seconds)}</div>
                    </>
                )}
            </div>

            {currentLabel && typeof currentIndex === "number" && total ? (
                <div className={noPadding ? "card-text-content" : "progress-current"} style={noPadding ? { paddingTop: 0, paddingBottom: 10 } : {}}>
                    Procesando: <strong>{currentLabel}</strong> ({currentIndex + 1}/{total})
                </div>
            ) : null}

            <ProgressTrack pct={pct} />

            <div className={noPadding ? "card-text-content" : "progress-caption"} style={noPadding ? { paddingTop: 10 } : {}}>
                Progreso estimado: {pct}%
            </div>
        </div>
    );
};
