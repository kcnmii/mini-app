import { useState, useEffect, useMemo, useCallback, useRef } from "react";
import { getTelegramWebApp, authRequest, setAuthToken, getAuthToken, DEFAULT_TEST_CHAT_ID } from "../utils";

export function useAuth(setStatus: (s: string) => void, onAuthenticated: () => Promise<void>) {
    const webApp = useMemo(getTelegramWebApp, []);
    const [isAppReady, setIsAppReady] = useState(false);
    const [authUser, setAuthUser] = useState<any>(null);
    const [chatId, setChatId] = useState(DEFAULT_TEST_CHAT_ID);

    const onAuthRef = useRef(onAuthenticated);
    onAuthRef.current = onAuthenticated;

    const isAuthenticated = !!getAuthToken();

    useEffect(() => {
        (window as any).onTelegramAuth = async (user: any) => {
            try {
                const authData = await authRequest<{ access_token: string; user: any }>("/auth/telegram/widget", {
                    method: "POST", headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(user),
                });
                setAuthUser(authData.user);
                setAuthToken(authData.access_token);
                setChatId(String(authData.user.id));
                await onAuthRef.current();
                setIsAppReady(true);
            } catch {
                setStatus("Ошибка авторизации");
                setIsAppReady(true);
            }
        };
    }, [setStatus]);

    useEffect(() => {
        if (webApp) {
            webApp.ready?.();
            webApp.expand?.();
        }

        async function initAuth() {
            if (webApp?.initData) {
                try {
                    const authData = await authRequest<{ access_token: string; user: any }>("/auth/telegram/init", {
                        method: "POST", headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ init_data: webApp.initData }),
                    });
                    setAuthUser(authData.user);
                    setAuthToken(authData.access_token);
                    setChatId(String(authData.user.id));
                    await onAuthRef.current();
                    setIsAppReady(true);
                } catch {
                    setStatus("Ошибка авторизации");
                    setIsAppReady(true);
                }
            } else {
                setIsAppReady(true);
            }
        }

        initAuth();
    }, [webApp, setStatus]);

    const logout = useCallback(() => {
        setAuthToken("");
        setAuthUser(null);
        window.location.reload();
    }, []);

    return { isAppReady, setIsAppReady, authUser, setAuthUser, chatId, setChatId, isAuthenticated, webApp, logout };
}
