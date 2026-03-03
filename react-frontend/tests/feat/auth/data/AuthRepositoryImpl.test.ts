import { vi, describe, it, expect, beforeEach } from "vitest";
import { AuthRepositoryImpl } from "@/feat/auth/data/AuthRepositoryImpl";
import * as MsalConfig from "@/feat/auth/data/MsalConfig";

// Deep mock MsalConfig
vi.mock("@/feat/auth/data/MsalConfig", () => ({
    msalInstance: {
        getActiveAccount: vi.fn(),
        getAllAccounts: vi.fn(),
        handleRedirectPromise: vi.fn(),
        loginRedirect: vi.fn(),
        logoutRedirect: vi.fn(),
        acquireTokenSilent: vi.fn(),
        acquireTokenRedirect: vi.fn(),
    },
    loginRequest: { scopes: ["User.Read"] },
}));

describe("AuthRepositoryImpl", () => {
    let repository: AuthRepositoryImpl;

    beforeEach(() => {
        vi.clearAllMocks();
        repository = new AuthRepositoryImpl();
    });

    it("getCurrentUser should return user info", async () => {
        const mockAccount = { name: "Test User", username: "test@test.com" };
        (MsalConfig.msalInstance.getActiveAccount as any).mockReturnValue(mockAccount);

        const user = await repository.getCurrentUser();
        expect(user).not.toBeNull();
        expect(user?.name).toBe("Test User");
    });

    it.skip("getAccessToken should return token", async () => {
        const mockAccount = { name: "Test User", username: "test@test.com" };
        (MsalConfig.msalInstance.getActiveAccount as any).mockReturnValue(mockAccount);
        (MsalConfig.msalInstance.acquireTokenSilent as any).mockResolvedValue({ accessToken: "secret-token" });

        const token = await repository.getAccessToken();
        expect(token).toBe("secret-token");
    });
});
