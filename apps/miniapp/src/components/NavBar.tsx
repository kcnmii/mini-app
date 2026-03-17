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
    actionType?: "icon" | "circle";
}

export function NavBar({ title, onBack, onAction, actionIcon, tgUser, tgName, showProfile, actionType = "icon" }: NavBarProps) {
    return (
        <div className="nav-bar">
            <div className="nav-bar-inner">
                <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                    {onBack && (
                        <button className="nav-bar-btn" onClick={onBack} style={{ marginRight: "4px" }}>
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
                                <span style={{ fontSize: "17px", fontWeight: 600, lineHeight: tgUser?.username ? "20px" : "normal" }}>{tgName}</span>
                                {tgUser?.username && <span style={{ fontSize: "13px", color: "var(--text-secondary)", lineHeight: "16px" }}>@{tgUser.username}</span>}
                            </div>
                        </>
                    )}

                    {title && <h1 className="nav-bar-title">{title}</h1>}
                </div>

                {onAction && actionIcon && (
                    <button className={actionType === "circle" ? "nav-bar-btn-circle" : "nav-bar-btn"} onClick={onAction}>
                        <Icon name={actionIcon} />
                    </button>
                )}
            </div>
        </div>
    );
}
