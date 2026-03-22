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
    leftAction?: React.ReactNode;
    titleCenter?: boolean;
}

export function NavBar({ title, onBack, onAction, actionIcon, tgUser, tgName, showProfile, actionType = "circle", leftAction, titleCenter }: NavBarProps) {
    return (
        <div className="nav-bar">
            <div className="nav-bar-inner">
                <div style={{ display: "flex", alignItems: "center", gap: "12px", minWidth: "80px" }}>
                    {onBack && (
                        <button className="nav-bar-btn" onClick={onBack} style={{ marginRight: "4px" }}>
                            <Icon name="arrow_back" />
                        </button>
                    )}

                    {leftAction}

                    {!titleCenter && showProfile && tgName && (
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

                    {!titleCenter && title && <h1 className="nav-bar-title">{title}</h1>}
                </div>

                {titleCenter && title && <span className="nav-bar-title-center" style={{ fontSize: "17px", fontWeight: 600 }}>{title}</span>}

                <div className="nav-bar-right" style={{ minWidth: "80px", justifyContent: "flex-end" }}>
                    {onAction && actionIcon && (
                        <button 
                            className={actionType === "circle" ? "nav-bar-btn-circle" : "nav-bar-btn"} 
                            onClick={onAction}
                            style={actionIcon === "delete" ? { color: "var(--ios-red)", borderColor: "rgba(255, 59, 48, 0.2)" } : {}}
                        >
                            <Icon name={actionIcon} />
                        </button>
                    )}
                </div>
            </div>
        </div>
    );
}
