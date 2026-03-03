import React from "react";
import { AuthProvider, AuthGate } from "../feat/auth/presentation/page/Auth";
import { TimesheetPage } from "../feat/timesheet/presentation/page/TimesheetPage";
import "./styles/styles.css";

export const App: React.FC = () => {
    return (
        <AuthProvider>
            <AuthGate>
                <TimesheetPage />
            </AuthGate>
        </AuthProvider>
    );
};
