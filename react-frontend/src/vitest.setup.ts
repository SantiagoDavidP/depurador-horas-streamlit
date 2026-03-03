import "@testing-library/jest-dom";
import { vi } from "vitest";

// Mock Plotly since it doesn't work in JSDOM
vi.mock("react-plotly.js", () => ({
    default: () => null
}));

// Mock MSAL
vi.mock("@azure/msal-react", () => ({
    MsalProvider: ({ children }: any) => children,
    useMsal: () => ({
        instance: {
            getAllAccounts: () => [],
            loginPopup: vi.fn(),
            logoutPopup: vi.fn(),
        },
        accounts: [],
        inProgress: "none",
    }),
    useIsAuthenticated: () => false,
}));
