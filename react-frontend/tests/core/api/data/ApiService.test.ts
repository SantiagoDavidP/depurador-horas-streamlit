import { vi, describe, it, expect, beforeEach } from "vitest";
import * as api from "@/core/api/data/ApiService";

// Mock AuthRepository
vi.mock("@/feat/auth/data/AuthRepositoryImpl", () => {
    return {
        AuthRepositoryImpl: vi.fn().mockImplementation(function () {
            return {
                getAccessToken: vi.fn().mockResolvedValue("mock-token")
            };
        })
    };
});

describe("ApiService", () => {
    beforeEach(() => {
        vi.clearAllMocks();
        // Mock global fetch
        const fetchMock = vi.fn();
        vi.stubGlobal('fetch', fetchMock);
    });

    it("getProfiles should return profiles array", async () => {
        const mockProfiles = { profiles: [{ client_id: "1", client_name: "Test" }] };
        (fetch as any).mockResolvedValue({
            ok: true,
            json: () => Promise.resolve(mockProfiles)
        });

        const result = await api.getProfiles();
        expect(result).toEqual(mockProfiles.profiles);
    });

    it("getProfiles should throw error on failure", async () => {
        (fetch as any).mockResolvedValue({
            ok: false,
            status: 500,
            text: () => Promise.resolve(JSON.stringify({ detail: "Server Error" })),
            json: () => Promise.resolve({ detail: "Server Error" })
        });

        await expect(api.getProfiles()).rejects.toThrow("Server Error");
    });

    it("getMe should return user info", async () => {
        const mockUser = { user: { name: "Test User" } };
        (fetch as any).mockResolvedValue({
            ok: true,
            json: () => Promise.resolve(mockUser)
        });

        const result = await api.getMe();
        expect(result).toEqual(mockUser.user);
    });

    it("analyzeBatch should send FormData", async () => {
        (fetch as any).mockResolvedValue({
            ok: true,
            json: () => Promise.resolve({ auto_profile_id: "p1" })
        });

        const files = [new File([""], "test.xlsx")];
        const result = await api.analyzeBatch(files);
        expect(result.auto_profile_id).toBe("p1");
    });

    it("processBatch should send request and return progress info", async () => {
        const mockRes = { batch_id: "b1", results: [] };
        (fetch as any).mockResolvedValue({
            ok: true,
            json: () => Promise.resolve(mockRes)
        });

        const files = [new File([""], "f1")];
        const payload = { profile_id: "1" };
        const result = await api.processBatch(files, payload);
        expect(result.batch_id).toBe("b1");
    });

    it("consolidateBatch should return download info", async () => {
        const mockRes = { filename: "c.xlsx" };
        (fetch as any).mockResolvedValue({
            ok: true,
            json: () => Promise.resolve(mockRes)
        });

        const result = await api.consolidateBatch({ batch_id: "b1" });
        expect(result.filename).toBe("c.xlsx");
    });

    it("buildBaninterZip should return download info", async () => {
        const mockRes = { download_id: "d1", filename: "z.zip" };
        (fetch as any).mockResolvedValue({
            ok: true,
            json: () => Promise.resolve(mockRes)
        });

        const result = await api.buildBaninterZip({ batchId: "b1" });
        expect(result.download_id).toBe("d1");
    });

    it("downloadFile should return blob", async () => {
        const mockBlob = new Blob(["test"]);
        (fetch as any).mockResolvedValue({
            ok: true,
            blob: () => Promise.resolve(mockBlob)
        });

        const result = await api.downloadFile("123");
        expect(result).toBe(mockBlob);
    });
    it("consolidateBatch should throw on error", async () => {
        (fetch as any).mockResolvedValue({
            ok: false,
            text: () => Promise.resolve("Consolidate error"),
        });
        await expect(api.consolidateBatch({ batch_id: "1" })).rejects.toThrow("Consolidate error");
    });

    it("buildBaninterZip should throw on error", async () => {
        (fetch as any).mockResolvedValue({
            ok: false,
            text: () => Promise.resolve("Zip error"),
        });
        await expect(api.buildBaninterZip({ batchId: "1" })).rejects.toThrow("Zip error");
    });
});
