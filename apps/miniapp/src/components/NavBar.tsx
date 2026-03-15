import React from "react";
import { Icon } from "./Common";
import { getAvatarColor } from "../utils";

interface NavBarProps {
    title?: string;
    onBack?: () => void;
    onAction?: () => void;
    actionIcon?: string;
    tgUser?: any;
    tgName?: string;
    showProfile?: boolean;
}

export function NavBar({ title, onBack, onAction, actionIcon, tgUser, tgName, showProfile }: NavBarProps) {
    return (
        <div className="nav-bar">
            <div className="nav-bar-inner" style={showProfile ? { justifyContent: "flex-start", gap: "12px" } : {}}>
                {onBack && (
                    <button className="nav-bar-btn" onClick={onBack}>
                        <Icon name="arrow_back" />
                    </button>
                )}

                {showProfile && tgName && (
                    <>
                        <div className="user-avatar" style={{
                            background: tgUser?.photo_url ? "transparent" : getAvatarColor(tgName),
                            color: "white", fontSize: "18px", fontWeight: 700
                        }}>
                            {tgUser?.photo_url ? (
                                <img src={tgUser.photo_url} alt="avatar" style={{ width: "100%", height: "100%", borderRadius: "50%", objectFit: "cover" }} />
                            ) : (
                                tgName.charAt(0).toUpperCase()
                            )}
                        </div>
                        <div style={{ display: "flex", flexDirection: "column", justifyContent: "center" }}>
                            <span style={{ fontSize: "20px", fontWeight: 600, lineHeight: tgUser?.username ? "23px" : "normal" }}>{tgName}</span>
                            {tgUser?.username && <span style={{ fontSize: "15px", color: "var(--text-secondary)", lineHeight: "18px" }}>@{tgUser.username}</span>}
                        </div>
                    </>
                )}

                {title && <h1 className="nav-bar-title">{title}</h1>}

                {onAction && actionIcon && (
                    <button className="nav-bar-btn" onClick={onAction}>
                        <Icon name={actionIcon} />
                    </button>
                )}
            </div>
        </div>
    );
}
