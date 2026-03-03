import React from "react";
import { Typography } from "../atoms/Typography";

interface MetricCardProps {
    label: string;
    value: string | number;
}

export const MetricCard: React.FC<MetricCardProps> = ({ label, value }) => {
    return (
        <div className="metric-card">
            <Typography variant="label" className="metric-label">{label}</Typography>
            <div className="metric-value">{value}</div>
        </div>
    );
};
