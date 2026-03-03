import React from "react";

interface ErrorsTableProps {
    errors?: Record<string, unknown>[];
    errorColWidths: number[];
    onResizeStart: (index: number, event: React.MouseEvent) => void;
}

export const ErrorsTable: React.FC<ErrorsTableProps> = ({
    errors,
    errorColWidths,
    onResizeStart,
}) => {
    if (!errors || errors.length === 0) {
        return <div className="status-card">Sin errores detectados.</div>;
    }
    const headers = ["Fecha", "Tipo", "Descripción", "Valor"];
    return (
        <div className="table-wrap">
            <table className="table table-errors">
                <colgroup>
                    {headers.map((_, idx) => (
                        <col key={idx} style={{ width: errorColWidths[idx] || 140 }} />
                    ))}
                </colgroup>
                <tbody>
                    <tr className="table-header-row">
                        {headers.map((label, idx) => (
                            <th key={label} scope="col" className="resizable-cell">
                                <div className="cell-resize">
                                    <span className="cell-content">{label}</span>
                                    <span
                                        className="col-resizer"
                                        onMouseDown={(event) => onResizeStart(idx, event)}
                                    />
                                </div>
                            </th>
                        ))}
                    </tr>
                    {errors.map((row, idx) => {
                        const values = [
                            String(row["fecha"] ?? ""),
                            String(row["tipo_error"] ?? ""),
                            String(row["descripcion"] ?? ""),
                            String(row["valor_original"] ?? ""),
                        ];
                        return (
                            <tr key={idx}>
                                {values.map((value, colIdx) => (
                                    <td key={colIdx} className="resizable-cell">
                                        <div className="cell-resize">
                                            <span className="cell-content">{value}</span>
                                            <span
                                                className="col-resizer"
                                                onMouseDown={(event) =>
                                                    onResizeStart(colIdx, event)
                                                }
                                            />
                                        </div>
                                    </td>
                                ))}
                            </tr>
                        );
                    })}
                </tbody>
            </table>
        </div>
    );
};
