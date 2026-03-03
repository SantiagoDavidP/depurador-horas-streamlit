import React from "react";
import { Button } from "../atoms/Button";

interface FileListItemProps {
    name: string;
    onRemove: () => void;
}

export const FileListItem: React.FC<FileListItemProps> = ({ name, onRemove }) => {
    return (
        <li className="flex-between">
            <span>{name}</span>
            <Button variant="text" onClick={onRemove}>✕</Button>
        </li>
    );
};
