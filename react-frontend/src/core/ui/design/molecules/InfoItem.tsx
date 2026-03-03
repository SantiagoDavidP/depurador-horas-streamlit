import React from "react";
import { Typography } from "../atoms/Typography";

interface InfoItemProps {
    label: string;
    value: string;
}

export const InfoItem: React.FC<InfoItemProps> = ({ label, value }) => {
    return (
        <div className="info-item">
            <Typography variant="label" className="info-label">{label}</Typography>
            <div className="info-value">{value}</div>
        </div>
    );
};
