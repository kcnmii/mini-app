import { useEffect, useMemo, useState, useCallback, useRef } from "react";
import type { TabKey, Client, CatalogItem, DocumentItem, InvoiceForm, DocumentRecord, ClientDraft, ItemDraft, SupplierProfileData, ClientBankAccount, ClientContact, InvoiceRecord, DashboardSummary, ClientBalance } from "./types";
import { API_BASE_URL, DEFAULT_TEST_CHAT_ID, emptyProfile, makeInitialInvoice, getTelegramWebApp, request, authRequest, setAuthToken, getAuthToken, parseMoney, formatMoney, buildInvoicePatch, getAvatarColor } from "./utils";

import { Icon, Toggle } from "./components/Common";
import { TelegramLoginButton } from "./components/TelegramLoginButton";
import { DateFilterView } from "./views/DateFilterView";
import { BankPickerView } from "./views/BankPickerView";
import { HomeView } from "./views/HomeView";
import { InvoicesListView } from "./views/InvoicesListView";
import { ClientsView } from "./views/ClientsView";
import { ItemsView } from "./views/ItemsView";
import { ProfileView } from "./views/ProfileView";
import { AddBankAccountView } from "./views/AddBankAccountView";
import { EditRequisitesView } from "./views/EditRequisitesView";
import { AddItemView } from "./views/AddItemView";
import { AddClientView } from "./views/AddClientView";
import { AddClientBankAccountView } from "./views/AddClientBankAccountView";
import { AddClientContactView } from "./views/AddClientContactView";
import { InvoiceFormView } from "./views/InvoiceFormView";
import { ViewDocumentView } from "./views/ViewDocumentView";
import { ImportSuccessView } from "./views/ImportSuccessView";

import { useAuth } from "./hooks/useAuth";
import { useSharedState } from "./hooks/useSharedState";
import { useProfile } from "./hooks/useProfile";
import { useClients } from "./hooks/useClients";
import { useCatalog } from "./hooks/useCatalog";
import { useInvoices } from "./hooks/useInvoices";
import { useDocuments } from "./hooks/useDocuments";
import { useBanks } from "./hooks/useBanks";

/* ═══════════════════ MAIN APP ═══════════════════ */
export function App() {
  const [tab, setTab] = useState<TabKey>("home");
  const [invoiceStatusFilter, setInvoiceStatusFilter] = useState<string>("all");
  const [clientSearch, setClientSearch] = useState("");
  const [itemSearch, setItemSearch] = useState("");
  const [docSearch, setDocSearch] = useState("");
  const [dateFilter, setDateFilter] = useState<{ type: "today" | "week" | "month" | "all" | "custom", from?: string, to?: string }>({ type: "month" });

  const { status, setStatus, busy, setBusy, subView, setSubView, prevSubView, isBinLoading, setIsBinLoading } = useSharedState();

  const fileInputRef = useRef<HTMLInputElement>(null);

  const { profile, setProfile, profileDraft, setProfileDraft, refreshProfileImages, saveProfile, deleteRequisites, deleteBankAccount } = useProfile(setStatus, setBusy, (i) => invHook.setInvoice(i), setSubView);

  const invHook = useInvoices(setStatus, setBusy, profile, setSubView);

  const {
    clients, setClients, clientDraft, setClientDraft, selectedCatalogClient, setSelectedCatalogClient, clientBalance, setClientBalance,
    clientBaDraft, setClientBaDraft, clientContactDraft, setClientContactDraft, editingBaIndex, editingContactIndex,
    openAddClientBa, saveClientBa, openAddClientContact, saveClientContact,
    createClient, deleteClient, loadClientBalance
  } = useClients(setStatus, setBusy, setSubView);

  const { items, setItems, itemDraft, setItemDraft, selectedCatalogItem, setSelectedCatalogItem, createItem, deleteItem } = useCatalog(setStatus, setBusy, setSubView);

  const { documents, setDocuments, loadAndPreviewOldDocument } = useDocuments(setStatus, setBusy, profile, setSubView);

  const { bankAccounts, setBankAccounts, selectedBankAccountId, setSelectedBankAccountId, handleFileUpload, importResult, setImportResult } = useBanks(setStatus, setBusy, setSubView);

  const { setInvoice, setDashboardSummary, setInvoiceRecords } = invHook;

  const loadData = useCallback(async () => {
    try {
      let query = "";
      if (dateFilter.type !== "month" || dateFilter.from || dateFilter.to) {
        const params = new URLSearchParams();
        let from: string | undefined = dateFilter.from;
        let to: string | undefined = dateFilter.to;
        if (dateFilter.type === "today") {
          const d = new Date(); d.setHours(0, 0, 0, 0); from = d.toISOString();
        } else if (dateFilter.type === "week") {
          const d = new Date(); d.setDate(d.getDate() - d.getDay() + (d.getDay() === 0 ? -6 : 1)); d.setHours(0, 0, 0, 0); from = d.toISOString();
        } else if (dateFilter.type === "month") {
          const d = new Date(); d.setDate(1); d.setHours(0, 0, 0, 0); from = d.toISOString();
        } else if (dateFilter.type === "all") {
          params.set("all_time", "true");
        }
        if (from) params.set("from_date", from);
        if (to) params.set("to_date", to);
        query = "?" + params.toString();
      }

      const [c, i, d, p, summary, invRecs, ba] = await Promise.all([
        request<Client[]>("/clients"), request<CatalogItem[]>("/catalog/items"),
        request<DocumentRecord[]>("/documents/recent"), request<SupplierProfileData>("/profile"),
        request<DashboardSummary>(`/dashboard/summary${query}`).catch(() => ({ awaiting: 0, overdue: 0, paid_this_month: 0, invoices_count: 0, overdue_count: 0 })),
        request<InvoiceRecord[]>("/invoices").catch(() => []),
        request<{ id: number; bank_name: string; account_number: string; bic: string; currency: string; is_default: boolean }[]>("/banks/accounts").catch(() => []),
      ]);
      setClients(c); setItems(i); setDocuments(d); setProfile(p); setProfileDraft(p);
      setInvoice(makeInitialInvoice(p));
      setDashboardSummary(summary);
      setInvoiceRecords(invRecs);
      setBankAccounts(ba);
    } catch (e) {
      setTimeout(() => setStatus("Ошибка: сервер недоступен"), 500);
    }
  }, [dateFilter, setClients, setItems, setDocuments, setProfile, setProfileDraft, setInvoice, setDashboardSummary, setInvoiceRecords, setBankAccounts, setStatus]);

  const { isAppReady, setIsAppReady, authUser, setAuthUser, chatId, setChatId, isAuthenticated, webApp, logout } = useAuth(setStatus, loadData);

  useEffect(() => {
    if (!!getAuthToken()) {
      loadData();
    }
  }, [dateFilter]);

  const handleAddBankAccount = async (acc: { account_number: string; bank_name: string; bic: string; kbe: string; is_default: boolean }) => {
    setBusy("save");
    try {
      if (acc.is_default) {
        // Update profile too
        const updatedProfile = { ...profile, company_iic: acc.account_number, company_bic: acc.bic, beneficiary_bank: acc.bank_name, company_kbe: acc.kbe };
        await request<SupplierProfileData>("/profile", { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(updatedProfile) });
        setProfile(updatedProfile);
        setProfileDraft(updatedProfile);
        setInvoice(makeInitialInvoice(updatedProfile));
      }
      
      await request("/banks/accounts", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ account_number: acc.account_number, bank_name: acc.bank_name, currency: "KZT" })
      });
      
      setStatus("Счет успешно добавлен");
      setSubView(null);
      await loadData();
    } catch (e) {
      setStatus(e instanceof Error ? e.message : "Ошибка");
    } finally {
      setBusy("idle");
    }
  };

  const handleDeleteBankAccount = async (id: number) => {
    const acc = bankAccounts.find(ba => ba.id === id);
    if (!acc) return;
    if (!window.confirm("Удалить этот счет?")) return;
    
    setBusy("save");
    try {
      await request(`/banks/accounts/${id}`, { method: "DELETE" });
      setBankAccounts(prev => prev.filter(ba => ba.id !== id));
      
      if (acc.account_number === profile.company_iic) {
          const cleared = { ...profile, company_iic: "", company_bic: "", beneficiary_bank: "", company_kbe: "" };
          await request<SupplierProfileData>("/profile", { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(cleared) });
          setProfile(cleared);
          setProfileDraft(cleared);
          setInvoice(makeInitialInvoice(cleared));
      }
      setStatus("Счет удален");
    } catch {
      setStatus("Ошибка при удалении счета");
    } finally {
      setBusy("idle");
    }
  };

  const tabIcons: Record<TabKey, string> = { home: "home", invoices: "description", clients: "group", items: "inventory_2", profile: "person" };

  const tabLabels: Record<TabKey, string> = { home: "Главная", invoices: "Документы", clients: "Клиенты", items: "Каталог", profile: "Профиль" };

  const loginView = (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", height: "100vh", gap: "24px", padding: "32px" }}>
      <div style={{ fontSize: "48px" }}><Icon name="description" /></div>
      <h1 style={{ fontSize: "22px", fontWeight: 700, textAlign: "center", margin: 0 }}>Doc Mini App</h1>
      <p style={{ color: "var(--text-secondary)", textAlign: "center", fontSize: "15px", margin: 0, maxWidth: "280px" }}>Войдите через Telegram, чтобы управлять документами, клиентами и каталогом.</p>
      <TelegramLoginButton />
    </div>
  );

  const tgUser = authUser || webApp?.initDataUnsafe?.user;
  const tgName = [tgUser?.first_name, tgUser?.last_name].filter(Boolean).join(" ") || "Пользователь";

  let subViewContent: React.ReactNode = null;
  if (subView === "invoiceForm") {
    subViewContent = (
      <InvoiceFormView
        invoice={invHook.invoice}
        setInvoice={invHook.setInvoice}
        setSubView={setSubView}
        selectedDocId={invHook.selectedDocId}
        selectedInvoiceId={invHook.selectedInvoiceId}
        saveInvoice={() => invHook.saveInvoice(loadData, setDocuments)}
        busy={busy}
        invoiceClientSearch={invHook.invoiceClientSearch}
        setInvoiceClientSearch={invHook.setInvoiceClientSearch}
        filteredClients={clients.filter((c) => !invHook.invoiceClientSearch || c.name.toLowerCase().includes(invHook.invoiceClientSearch.toLowerCase()) || c.bin_iin.includes(invHook.invoiceClientSearch))}
        selectClient={invHook.selectClient}
        bankAccounts={bankAccounts}
        changeQuantity={invHook.changeQuantity}
        removeRow={invHook.removeRow}
        deleteInvoice={() => invHook.deleteInvoice(setDocuments)}
        profile={profile}
        sendInvoice={() => invHook.sendInvoice(chatId)}
        animationType={prevSubView === "addItem" ? "none" : (invHook.selectedDocId || invHook.selectedInvoiceId) ? "left" : "up"}
        openAddItem={() => {
            setSelectedCatalogItem(null);
            setItemDraft({ name: "", unit: "", price: "", sku: "" } as any);
            setSubView("addItem");
        }}
      />
    );
  } else if (subView === "viewDocument") {
    subViewContent = (
      <ViewDocumentView
        setSubView={setSubView}
        selectedInvoice={invHook.invoiceRecords.find(inv => inv.id === invHook.selectedInvoiceId)}
        selectedDoc={documents.find(d => d.id === invHook.selectedDocId)}
        isPdfLoading={invHook.isPdfLoading}
        previewPages={invHook.previewPages}
        markInvoicePaid={(id) => invHook.markInvoicePaid(id, loadData)}
        markInvoiceSent={(id) => invHook.markInvoiceSent(id, loadData)}
        sendInvoice={() => invHook.sendInvoice(chatId)}
        busy={busy}
      />
    );
  } else if (subView === "addClient") {
    subViewContent = (
      <AddClientView
        tab={tab} setSubView={setSubView} selectedCatalogClient={selectedCatalogClient} setSelectedCatalogClient={setSelectedCatalogClient}
        createClient={() => createClient(tab, invHook.selectClient)} clientBalance={clientBalance} clientDraft={clientDraft as any} setClientDraft={setClientDraft as any}
        setIsBinLoading={setIsBinLoading} isBinLoading={isBinLoading} setStatus={setStatus} clients={clients} openAddClientBa={openAddClientBa} openAddClientContact={openAddClientContact}
        deleteClient={() => deleteClient()} busy={busy}
        animationType={(prevSubView === "addClientBankAccount" || prevSubView === "addClientContact") ? "none" : selectedCatalogClient ? "left" : "up"}
      />
    );
  } else if (subView === "addClientBankAccount") {
    subViewContent = (
      <AddClientBankAccountView
        setSubView={setSubView} clientBaDraft={clientBaDraft} setClientBaDraft={setClientBaDraft} saveClientBa={saveClientBa}
        editingBaIndex={editingBaIndex} setClientDraft={setClientDraft as any}
      />
    );
  } else if (subView === "addClientContact") {
    subViewContent = (
      <AddClientContactView
        setSubView={setSubView} clientContactDraft={clientContactDraft} setClientContactDraft={setClientContactDraft} saveClientContact={saveClientContact}
        editingContactIndex={editingContactIndex} setClientDraft={setClientDraft as any}
      />
    );
  } else if (subView === "editRequisites") {
    subViewContent = (
      <EditRequisitesView
        profile={profile} profileDraft={profileDraft as any} setProfileDraft={setProfileDraft as any} setSubView={setSubView}
        saveProfile={saveProfile} deleteRequisites={() => deleteRequisites()} busy={busy}
        isBinLoading={isBinLoading} setIsBinLoading={setIsBinLoading} setStatus={setStatus}
      />
    );
  } else if (subView === "addBankAccount") {
    subViewContent = (
      <AddBankAccountView
        setSubView={setSubView}
        onAddAccount={handleAddBankAccount}
        busy={busy}
        prevSubView={prevSubView}
      />
    );
  } else if (subView === "addItem") {
    subViewContent = (
      <AddItemView
        itemDraft={itemDraft as any} setItemDraft={setItemDraft as any} items={items} selectedCatalogItem={selectedCatalogItem}
        setSelectedCatalogItem={setSelectedCatalogItem} setSubView={setSubView} createItem={() => createItem(tab, invHook.addRow)} deleteItem={() => deleteItem()}
        busy={busy} tab={tab}
        animationType={selectedCatalogItem ? "left" : "up"}
      />
    );
  } else if (subView === "importSuccess") {
    subViewContent = (
      <ImportSuccessView
        result={importResult}
        onClose={() => setSubView(null)}
        onRefresh={loadData}
      />
    );
  }

  if (subView === ("dateFilter" as any)) subViewContent = <DateFilterView dateFilter={dateFilter as any} setDateFilter={setDateFilter as any} onClose={() => setSubView(null)} />;
  if (subView === ("bankPicker" as any)) subViewContent = (
    <BankPickerView
      bankAccounts={bankAccounts} selectedBankAccountId={selectedBankAccountId} setSelectedBankAccountId={setSelectedBankAccountId}
      onClose={() => setSubView(null)} onAddAccount={() => { setProfileDraft(profile); setSubView("addBankAccount"); }}
    />
  );

  return (
    <main className="app-shell">
      <div className={`status-banner${status ? " visible" : ""}`}>{status}</div>
      {!isAppReady ? (
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", height: "100vh", gap: "16px" }}>
          <div style={{ width: 40, height: 40, border: "3px solid var(--tg-theme-button-color, #007AFF)", borderTopColor: "transparent", borderRadius: "50%", animation: "spin 1s linear infinite" }} />
          <div style={{ color: "var(--text-secondary)", fontSize: "15px" }}>Загрузка...</div>
          <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
        </div>
      ) : !isAuthenticated ? (
        loginView
      ) : subViewContent ? (
        subViewContent
      ) : (
        <>
          {tab === "home" && (
            <HomeView
              bankAccounts={bankAccounts}
              selectedBankAccountId={selectedBankAccountId}
              profile={profile}
              dashboardSummary={invHook.dashboardSummary}
              invoiceRecords={invHook.invoiceRecords}
              documents={documents}
              fileInputRef={fileInputRef}
              setProfileDraft={setProfileDraft}
              setSubView={setSubView}
              setTab={setTab}
              openNewInvoice={() => invHook.openNewInvoice()}
              handleFileUpload={(e) => handleFileUpload(e, profile.company_iic || "", loadData)}
              loadAndPreviewNewInvoice={(id) => invHook.loadAndPreviewNewInvoice(id)}
              loadAndPreviewOldDocument={(id) => loadAndPreviewOldDocument(id, invHook.setInvoice, invHook.setInvoiceClientSearch)}
            />
          )}
          {tab === "invoices" && (
            <InvoicesListView
              invoiceRecords={invHook.invoiceRecords}
              documents={documents}
              docSearch={docSearch}
              setDocSearch={setDocSearch}
              invoiceStatusFilter={invoiceStatusFilter}
              setInvoiceStatusFilter={setInvoiceStatusFilter}
              openNewInvoice={() => invHook.openNewInvoice()}
              loadAndPreviewNewInvoice={(id) => invHook.loadAndPreviewNewInvoice(id)}
              loadAndPreviewOldDocument={(id) => loadAndPreviewOldDocument(id, invHook.setInvoice, invHook.setInvoiceClientSearch)}
            />
          )}
          {tab === "clients" && (
            <ClientsView
              clients={clients}
              clientSearch={clientSearch}
              setClientSearch={setClientSearch}
              setSubView={setSubView}
              setSelectedCatalogClient={setSelectedCatalogClient}
              setClientDraft={setClientDraft}
              loadClientBalance={loadClientBalance}
            />
          )}
          {tab === "items" && (
            <ItemsView
              items={items}
              itemSearch={itemSearch}
              setItemSearch={setItemSearch}
              setSubView={setSubView}
              setSelectedCatalogItem={setSelectedCatalogItem}
              setItemDraft={setItemDraft}
            />
          )}
          {tab === "profile" && (
            <ProfileView
              tgUser={tgUser}
              tgName={tgName}
              profile={profile}
              bankAccounts={bankAccounts}
              webAppInitData={!!webApp?.initData}
              setProfileDraft={setProfileDraft}
              setSubView={setSubView}
              setStatus={setStatus}
              refreshProfileImages={refreshProfileImages}
              deleteBankAccount={handleDeleteBankAccount}
              onLogout={logout}
            />
          )}
        </>
      )}
      {isAuthenticated && !subViewContent && (
        <nav className="tab-bar">
          <div className="tab-bar-inner">
            {(["home", "invoices", "clients", "items", "profile"] as TabKey[]).map((t) => (
              <button key={t} className={`tab-btn${t === tab ? " active" : ""}`} onClick={() => setTab(t)}>
                <Icon name={tabIcons[t]} filled={t === tab} />
                <span>{tabLabels[t]}</span>
              </button>
            ))}
          </div>
        </nav>
      )}
    </main>
  );
}
