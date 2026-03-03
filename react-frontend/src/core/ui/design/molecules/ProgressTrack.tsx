import React from "react";

interface ProgressTrackProps {
    pct: number;
}

export const ProgressTrack: React.FC<ProgressTrackProps> = ({ pct }) => {
    return (
        <div className="progress-track">
            <div className="progress-fill" style={{ width: `${pct}%` }} />
            <div className="progress-bar-animate" />
        </div>
    );
};
