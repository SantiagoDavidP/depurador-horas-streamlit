import { renderHook, act } from "@testing-library/react";
import { useAuthViewModel } from "@/feat/auth/presentation/view_model/AuthViewModel";
import { AuthRepositoryImpl } from "@/feat/auth/data/AuthRepositoryImpl";
import { vi, describe, it, expect, beforeEach } from "vitest";

const { mockAuthRepository } = vi.hoisted(() => ({
    mockAuthRepository: {
        getCurrentUser: vi.fn().mockResolvedValue({ name: "Logged User" }),
        login: vi.fn().mockResolvedValue(undefined),
        logout: vi.fn().mockResolvedValue(undefined),
        getAccessToken: vi.fn().mockResolvedValue("token"),
    }
}));

vi.mock("@/feat/auth/data/AuthRepositoryImpl", () => {
    return {
        AuthRepositoryImpl: vi.fn().mockImplementation(function () {
            return mockAuthRepository;
        }),
    };
});

describe("AuthViewModel", () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it("should load user on mount", async () => {
        const { result } = renderHook(() => useAuthViewModel());

        await act(async () => {
            await Promise.resolve();
        });

        expect(result.current.user).toEqual({ name: "Logged User" });
        expect(result.current.loading).toBe(false);
        expect(result.current.isAuthenticated).toBe(true);
    });

    it("should call login on repository", async () => {
        const { result } = renderHook(() => useAuthViewModel());

        await act(async () => {
            await result.current.login();
        });

        expect(mockAuthRepository.login).toHaveBeenCalled();
    });

    it("should call logout on repository", async () => {
        const { result } = renderHook(() => useAuthViewModel());

        await act(async () => {
            await result.current.logout();
        });

        expect(mockAuthRepository.logout).toHaveBeenCalled();
    });
});
