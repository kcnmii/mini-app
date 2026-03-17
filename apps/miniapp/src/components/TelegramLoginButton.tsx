import { useEffect, useState, useCallback } from "react";
import { authRequest } from "../utils";

export function TelegramLoginButton() {
    const [botName, setBotName] = useState<string>("");

    useEffect(() => {
        authRequest<{ bot_name: string }>("/auth/telegram/bot-name")
            .then(res => setBotName(res.bot_name))
            .catch(() => setBotName("docminiapp_bot"));
    }, []);

    const containerRef = useCallback((node: HTMLDivElement | null) => {
        if (!node || !botName) return;
        const script = document.createElement("script");
        script.src = "https://telegram.org/js/telegram-widget.js?22";
        script.async = true;
        script.setAttribute("data-telegram-login", botName);
        script.setAttribute("data-size", "large");
        script.setAttribute("data-radius", "12");
        script.setAttribute("data-onauth", "onTelegramAuth(user)");
        script.setAttribute("data-request-access", "write");
        node.innerHTML = "";
        node.appendChild(script);
    }, [botName]);

    if (!botName) return <div style={{ height: "40px", color: "var(--text-secondary)" }}>Загрузка виджета...</div>;

    return <div ref={containerRef} />;
}
