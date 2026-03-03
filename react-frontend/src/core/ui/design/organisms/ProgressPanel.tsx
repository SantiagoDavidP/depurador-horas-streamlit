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
}

export const ProgressPanel: React.FC<ProgressPanelProps> = ({
    title,
    detail,
    seconds,
    pct,
    currentLabel,
    currentIndex,
    total,
}) => {
    const formatDuration = (secs: number) => {
        if (!secs || secs < 0) return "0:00";
        const mins = Math.floor(secs / 60);
        const s = secs % 60;
        return `${mins}:${s.toString().padStart(2, "0")}`;
    };

    return (
        <div className="progress-panel">
            <div className="progress-head">
                <div>
                    <Typography variant="h4" className="progress-title">{title}</Typography>
                    <div className="progress-subtitle">{detail}</div>
                </div>
                <div className="progress-time">Tiempo: {formatDuration(seconds)}</div>
            </div>
            {currentLabel && typeof currentIndex === "number" && total ? (
                <div className="progress-current">
                    Procesando: <strong>{currentLabel}</strong> ({currentIndex + 1}/{total})
                </div>
            ) : null}
            <ProgressTrack pct={pct} />
            <div className="progress-caption">Progreso estimado: {pct}%</div>
        </div>
    );
};
