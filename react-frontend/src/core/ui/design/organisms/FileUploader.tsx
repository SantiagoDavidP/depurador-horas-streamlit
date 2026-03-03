import React from "react";
import { Typography } from "../atoms/Typography";
import { FileListItem } from "../molecules/FileListItem";

interface FileUploaderProps {
    title: string;
    files: File[];
    onFileChange: (event: React.ChangeEvent<HTMLInputElement>) => void;
    onRemoveFile: (index: number) => void;
    multiple?: boolean;
    inputRef?: React.RefObject<HTMLInputElement>;
}

export const FileUploader: React.FC<FileUploaderProps> = ({
    title,
    files,
    onFileChange,
    onRemoveFile,
    multiple = false,
    inputRef,
}) => {
    return (
        <div className="card">
            <Typography variant="h3">{title}</Typography>
            <div>
                <input
                    type="file"
                    multiple={multiple}
                    accept=".xlsx,.xls,.xlsm"
                    ref={inputRef}
                    onChange={onFileChange}
                />
                {files.length > 0 && (
                    <ul className="file-list">
                        {files.map((f, i) => (
                            <FileListItem key={i} name={f.name} onRemove={() => onRemoveFile(i)} />
                        ))}
                    </ul>
                )}
            </div>
        </div>
    );
};
