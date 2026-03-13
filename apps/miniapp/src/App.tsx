import { useEffect, useMemo, useState, useCallback } from "react";
import type { TabKey, Client, CatalogItem, DocumentItem, InvoiceForm, DocumentRecord, ClientDraft, ItemDraft, SupplierProfileData } from "./types";
import { API_BASE_URL, DEFAULT_TEST_CHAT_ID, emptyProfile, makeInitialInvoice, getTelegramWebApp, request, parseMoney, formatMoney, buildInvoicePatch } from "./utils";

/* ─── Icon helper ─── */
function Icon({ name, filled, className }: { name: string; filled?: boolean; className?: string }) {
  return <span className={`material-symbols-outlined${filled ? " filled" : ""}${className ? ` ${className}` : ""}`}>{name}</span>;
}

/* ─── iOS Toggle ─── */
function Toggle({ checked, onChange, disabled }: { checked: boolean; onChange: (v: boolean) => void; disabled?: boolean }) {
  return (
    <button type="button" className={`ios-switch-track${checked ? " on" : ""}`} disabled={disabled} onClick={() => onChange(!checked)}>
      <span className="ios-switch-knob" />
    </button>
  );
}

/* ─── Image Upload ─── */
function ImageUploadRow({ label, hint, imageType, onStatusChange }: { label: string; hint: string; imageType: "logo" | "signature" | "stamp"; onStatusChange: (msg: string) => void }) {
  const [preview, setPreview] = useState<string>("");
  const loadPreview = useCallback(async () => {
    try {
      const res = await request<{ has_image: boolean; data: string }>(`/profile/${imageType}/preview`);
      setPreview(res.has_image ? res.data : "");
    } catch { setPreview(""); }
  }, [imageType]);
  useEffect(() => { loadPreview(); }, [loadPreview]);

  async function handleUpload(file: File) {
    try {
      const fd = new FormData(); fd.append("file", file);
      await fetch(`${API_BASE_URL}/profile/${imageType}`, { method: "POST", body: fd });
      await loadPreview();
      onStatusChange(`${label} загружен`);
    } catch { onStatusChange(`Ошибка загрузки: ${label}`); }
  }

  return (
    <label className="upload-row">
      <div className="upload-row-info">
        <span className="upload-row-title">{label}</span>
        <span className="upload-row-hint">{hint}</span>
      </div>
      <div className="upload-row-action">
        {preview ? (
          <div className="upload-preview-thumb"><img src={preview} alt={label} /></div>
        ) : (
          <Icon name="cloud_upload" />
        )}
      </div>
      <input type="file" className="hidden-input" accept="image/png,image/jpeg,image/webp"
        onChange={(e) => { const f = e.target.files?.[0]; if (f) handleUpload(f); }} />
    </label>
  );
}

/* ═══════════════════ MAIN APP ═══════════════════ */
export function App() {
  const webApp = useMemo(getTelegramWebApp, []);
  const [tab, setTab] = useState<TabKey>("home");
  const [chatId, setChatId] = useState(DEFAULT_TEST_CHAT_ID);
  const [invoice, setInvoice] = useState<InvoiceForm>(makeInitialInvoice());
  const [documents, setDocuments] = useState<DocumentRecord[]>([]);
  const [clients, setClients] = useState<Client[]>([]);
  const [items, setItems] = useState<CatalogItem[]>([]);
  const [profile, setProfile] = useState<SupplierProfileData>(emptyProfile);
  const [profileDraft, setProfileDraft] = useState<SupplierProfileData>(emptyProfile);
  const [clientDraft, setClientDraft] = useState<ClientDraft>({ name: "", bin_iin: "", contact_name: "", phone: "" });
  const [itemDraft, setItemDraft] = useState<ItemDraft>({ name: "", unit: "шт.", price: "", sku: "" });
  const [status, setStatus] = useState("");
  const [busy, setBusy] = useState<"idle" | "save" | "send" | "pdf">("idle");
  const [clientSearch, setClientSearch] = useState("");
  const [itemSearch, setItemSearch] = useState("");
  const [invoiceClientSearch, setInvoiceClientSearch] = useState("");
  const [docSearch, setDocSearch] = useState("");
  // subView: null = show tab content, others = full-page sub-views
  const [subView, setSubView] = useState<null | "invoiceForm" | "addClient" | "addItem" | "editRequisites" | "addBankAccount" | "viewDocument">(null);
  const [selectedDocId, setSelectedDocId] = useState<number | null>(null);
  const [selectedCatalogItem, setSelectedCatalogItem] = useState<CatalogItem | null>(null);
  const [selectedCatalogClient, setSelectedCatalogClient] = useState<Client | null>(null);

  function openNewInvoice() {
    setInvoice(makeInitialInvoice(profile));
    setInvoiceClientSearch("");
    setSubView("invoiceForm");
    setSelectedDocId(null);
  }

  async function loadAndPreviewInvoice(id: number) {
    setBusy("save");
    try {
      const doc = await request<DocumentRecord & { payload_json?: string }>(`/documents/${id}`);
      setSelectedDocId(id);
      setSubView("invoiceForm");

      // Load invoice data for editing
      if (doc.payload_json) {
        try {
          const payload = JSON.parse(doc.payload_json);
          setInvoice(payload);
          setInvoiceClientSearch(payload.CLIENT_NAME || "");
        } catch (e) {
          console.error("Parse error", e);
        }
      } else if ((doc as any).reconstructed_items) {
        const items = (doc as any).reconstructed_items.map((it: any, idx: number) => ({
          number: idx + 1,
          name: it.name,
          quantity: it.quantity,
          unit: it.unit,
          price: it.price,
          total: it.total,
          code: it.code || ""
        }));
        const reconstructed = makeInitialInvoice(profile);
        reconstructed.CLIENT_NAME = doc.client_name;
        reconstructed.TOTAL_SUM = doc.total_sum;
        reconstructed.items = items;
        const numMatch = doc.title.match(/(?:№|N)\s*([^\s]+)/);
        if (numMatch) reconstructed.INVOICE_NUMBER = numMatch[1];
        setInvoice(reconstructed);
        setInvoiceClientSearch(doc.client_name);
      }
    } catch (e) {
      setStatus("Ошибка загрузки");
    } finally {
      setBusy("idle");
    }
  }

  // Status banner auto-hide
  useEffect(() => {
    if (!status) return;
    const t = setTimeout(() => setStatus(""), 3000);
    return () => clearTimeout(t);
  }, [status]);

  async function loadData() {
    const [c, i, d, p] = await Promise.all([
      request<Client[]>("/clients"), request<CatalogItem[]>("/catalog/items"),
      request<DocumentRecord[]>("/documents/recent"), request<SupplierProfileData>("/profile"),
    ]);
    setClients(c); setItems(i); setDocuments(d); setProfile(p); setProfileDraft(p);
    setInvoice(makeInitialInvoice(p));
  }

  useEffect(() => { webApp?.ready?.(); webApp?.expand?.(); loadData().catch(() => setStatus("Не удалось загрузить данные")); }, [webApp]);

  useEffect(() => {
    if (!webApp?.initData) return;
    request<{ user: { id: number; first_name?: string } }>("/auth/telegram/init", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ init_data: webApp.initData }),
    }).then((data) => setChatId(String(data.user.id))).catch(() => { });
  }, [webApp]);

  function updateItem(index: number, key: keyof DocumentItem, value: string) {
    setInvoice((c) => {
      const ni = c.items.map((it, ii) => ii === index ? { ...it, [key]: value } : it);
      return { ...c, ...buildInvoicePatch(ni) };
    });
  }
  function addRow(item?: CatalogItem) {
    setInvoice((c) => {
      const ni = [...c.items, { number: c.items.length + 1, name: item?.name ?? "", quantity: "1", unit: item?.unit ?? "шт.", price: item ? String(item.price) : "", total: item ? formatMoney(item.price) : "0", code: item?.sku ?? "" }];
      return { ...c, ...buildInvoicePatch(ni) };
    });
  }
  function removeRow(index: number) {
    setInvoice((c) => {
      const ni = c.items.filter((_, ii) => ii !== index);
      return { ...c, ...buildInvoicePatch(ni) };
    });
  }
  function changeQuantity(index: number, delta: number) {
    setInvoice((c) => {
      const ni = c.items.map((it, ii) => {
        if (ii !== index) return it;
        const nq = Math.max(1, (parseFloat(it.quantity) || 0) + delta);
        return { ...it, quantity: String(nq) };
      });
      return { ...c, ...buildInvoicePatch(ni) };
    });
  }
  function selectClient(client: Client) {
    setInvoice((c) => ({ ...c, CLIENT_NAME: client.name, CLIENT_IIN: client.bin_iin, CLIENT_ADDRESS: client.phone }));
    setInvoiceClientSearch(client.name);
    setStatus(`Клиент: ${client.name}`);
  }

  async function createClient() {
    if (!clientDraft.name.trim()) return;
    setBusy("save");
    try {
      const isModified = selectedCatalogClient && (
        selectedCatalogClient.name !== clientDraft.name ||
        selectedCatalogClient.bin_iin !== clientDraft.bin_iin ||
        (selectedCatalogClient.phone || "") !== (clientDraft.phone || "")
      );

      if (isModified && selectedCatalogClient) {
        const updated = await request<Client>(`/clients/${selectedCatalogClient.id}`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(clientDraft)
        });
        setClients((c) => c.map(cl => cl.id === updated.id ? updated : cl));
        setSelectedCatalogClient(updated);
        setStatus("Клиент обновлен");
        return;
      }

      const existingByBin = clients.find(cl => cl.bin_iin === clientDraft.bin_iin && cl.bin_iin !== "");
      let finalClient: Client;

      if (!existingByBin) {
        finalClient = await request<Client>("/clients", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(clientDraft) });
        setClients((c) => [finalClient, ...c]);
        setStatus("Клиент сохранен");
      } else {
        finalClient = existingByBin;
        setStatus("Клиент добавлен");
      }

      setClientDraft({ name: "", bin_iin: "", contact_name: "", phone: "" });
      setSelectedCatalogClient(null);

      if (tab === "home") {
        selectClient(finalClient);
      }

      setSubView(tab === "home" ? "invoiceForm" : null);
    } catch (e) {
      setStatus(e instanceof Error ? e.message : "Ошибка");
    } finally { setBusy("idle"); }
  }
  async function createItem() {
    if (!itemDraft.name.trim()) return;
    setBusy("save");
    try {
      const draftNameMatch = itemDraft.name.trim().toLowerCase();
      let existingItem = items.find((it) => it.name.trim().toLowerCase() === draftNameMatch);

      const isModified = selectedCatalogItem && (
        selectedCatalogItem.name !== itemDraft.name ||
        selectedCatalogItem.unit !== itemDraft.unit ||
        parseMoney(String(selectedCatalogItem.price)) !== parseMoney(itemDraft.price) ||
        (selectedCatalogItem.sku || "") !== (itemDraft.sku || "")
      );

      if (isModified && selectedCatalogItem) {
        // Update existing
        const updated = await request<CatalogItem>(`/catalog/items/${selectedCatalogItem.id}`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ name: itemDraft.name, unit: itemDraft.unit, price: parseMoney(itemDraft.price), sku: itemDraft.sku })
        });
        setItems((c) => c.map(i => i.id === updated.id ? updated : i));
        setSelectedCatalogItem(updated);
        setStatus("Товар обновлен");
        return; // Stay on screen to let user click "Ready"
      }

      if (!existingItem) {
        existingItem = await request<CatalogItem>("/catalog/items", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ name: itemDraft.name, unit: itemDraft.unit, price: parseMoney(itemDraft.price), sku: itemDraft.sku })
        });
        setItems((c) => [existingItem!, ...c]);
        setStatus("Товар сохранен");
      } else {
        setStatus("Товар добавлен");
      }

      if (tab === "home") {
        addRow(existingItem);
      }

      setItemDraft({ name: "", unit: "шт.", price: "", sku: "" });
      setSelectedCatalogItem(null);
      setSubView(tab === "home" ? "invoiceForm" : null);
    } catch (e) {
      setStatus(e instanceof Error ? e.message : "Ошибка");
    } finally { setBusy("idle"); }
  }
  async function saveInvoice() {
    setBusy("save");
    setStatus("Сохранение...");
    try {
      const s = await request<DocumentRecord>("/documents/invoice", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ payload: invoice }) });
      setDocuments((c) => [s, ...c].slice(0, 10));
      setStatus("Счет сохранен");
      setSubView(null);
      setSelectedDocId(null);
    } catch (e) { setStatus(e instanceof Error ? e.message : "Ошибка"); } finally { setBusy("idle"); }
  }
  async function deleteInvoice() {
    if (!selectedDocId) return;
    if (!confirm("Вы уверены, что хотите удалить этот документ?")) return;
    setBusy("save");
    try {
      await request(`/documents/${selectedDocId}`, { method: "DELETE" });
      setDocuments((c) => c.filter(d => d.id !== selectedDocId));
      setStatus("Документ удален");
      setSubView(null);
      setSelectedDocId(null);
    } catch (e) {
      setStatus(e instanceof Error ? e.message : "Ошибка при удалении");
    } finally { setBusy("idle"); }
  }
  async function deleteClient() {
    if (!selectedCatalogClient) return;
    if (!confirm("Вы уверены, что хотите удалить этого клиента?")) return;
    setBusy("save");
    try {
      await request(`/clients/${selectedCatalogClient.id}`, { method: "DELETE" });
      setClients((c) => c.filter(cl => cl.id !== selectedCatalogClient.id));
      setStatus("Клиент удален");
      setSubView(null);
      setSelectedCatalogClient(null);
      setClientDraft({ name: "", bin_iin: "", contact_name: "", phone: "" });
    } catch (e) {
      setStatus(e instanceof Error ? e.message : "Ошибка при удалении");
    } finally { setBusy("idle"); }
  }
  async function deleteItem() {
    if (!selectedCatalogItem) return;
    if (!confirm("Вы уверены, что хотите удалить этот товар/услугу?")) return;
    setBusy("save");
    try {
      await request(`/catalog/items/${selectedCatalogItem.id}`, { method: "DELETE" });
      setItems((c) => c.filter(i => i.id !== selectedCatalogItem.id));
      setStatus("Товар удален");
      setSubView(null);
      setSelectedCatalogItem(null);
      setItemDraft({ name: "", unit: "шт.", price: "", sku: "" });
    } catch (e) {
      setStatus(e instanceof Error ? e.message : "Ошибка при удалении");
    } finally { setBusy("idle"); }
  }
  async function generatePdf() {
    setBusy("pdf");
    try {
      const r = await fetch(`${API_BASE_URL}/render/invoice/pdf`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(invoice) });
      if (!r.ok) throw new Error(await r.text());
      const b = await r.blob(); window.open(URL.createObjectURL(b), "_blank"); setStatus("PDF сгенерирован");
    } catch (e) { setStatus(e instanceof Error ? e.message : "Ошибка PDF"); } finally { setBusy("idle"); }
  }
  async function sendInvoice() {
    setBusy("send");
    try {
      await request("/telegram/send-invoice", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ chat_id: Number(chatId), payload: invoice }) });
      setStatus("Отправлено в Telegram");
    } catch (e) { setStatus(e instanceof Error ? e.message : "Ошибка отправки"); } finally { setBusy("idle"); }
  }
  async function saveProfile() {
    setBusy("save");
    try {
      const s = await request<SupplierProfileData>("/profile", { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(profileDraft) });
      setProfile(s); setProfileDraft(s); setInvoice(makeInitialInvoice(s)); setStatus("Профиль сохранён");
    } catch (e) { setStatus(e instanceof Error ? e.message : "Ошибка"); } finally { setBusy("idle"); }
  }
  async function deleteRequisites() {
    if (!confirm("Вы уверены, что хотите удалить реквизиты?")) return;
    const cleared = { ...profile, company_iin: "", company_name: "", supplier_address: "", executor_name: "", position: "", phone: "", email: "" };
    setBusy("save");
    try {
      const s = await request<SupplierProfileData>("/profile", { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(cleared) });
      setProfile(s); setProfileDraft(s); setInvoice(makeInitialInvoice(s)); setStatus("Реквизиты удалены");
      setSubView(null);
    } catch (e) { setStatus(e instanceof Error ? e.message : "Ошибка"); } finally { setBusy("idle"); }
  }
  async function deleteBankAccount() {
    if (!confirm("Вы уверены, что хотите удалить банковский счет?")) return;
    const cleared = { ...profile, company_iic: "", company_bic: "", beneficiary_bank: "" };
    setBusy("save");
    try {
      const s = await request<SupplierProfileData>("/profile", { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(cleared) });
      setProfile(s); setProfileDraft(s); setInvoice(makeInitialInvoice(s)); setStatus("Счет удален");
      setSubView(null);
    } catch (e) { setStatus(e instanceof Error ? e.message : "Ошибка"); } finally { setBusy("idle"); }
  }

  /* ═══ RENDER: HOME TAB ═══ */
  const tgUser = webApp?.initDataUnsafe?.user;
  const tgName = [tgUser?.first_name, tgUser?.last_name].filter(Boolean).join(" ") || "Пользователь";

  const homeView = (
    <>
      <div className="nav-bar">
        <div className="nav-bar-inner" style={{ justifyContent: "flex-start", gap: "12px" }}>
          <div className="user-avatar">
            {tgUser?.photo_url ? (
              <img src={tgUser.photo_url} alt="avatar" style={{ width: "100%", height: "100%", borderRadius: "50%", objectFit: "cover" }} />
            ) : (
              <Icon name="person" />
            )}
          </div>
          <div style={{ display: "flex", flexDirection: "column", justifyContent: "center" }}>
            <span style={{ fontSize: "20px", fontWeight: 600, lineHeight: tgUser?.username ? "23px" : "normal" }}>{tgName}</span>
            {tgUser?.username && <span style={{ fontSize: "15px", color: "var(--text-secondary)", lineHeight: "18px" }}>@{tgUser.username}</span>}
          </div>
        </div>
      </div>
      <div className="content-area">
        <div className="glass-dashboard">
          <div className="glass-content">
            <div className="glass-hero-icon"><Icon name="description" /></div>
            <h3>Создайте новый документ</h3>
            <p>Оформление счета для ваших клиентов в пару кликов</p>
            <button className="glass-hero-btn" onClick={openNewInvoice}>
              <Icon name="add" /> Новый документ
            </button>
          </div>
        </div>
        {documents.length > 0 ? (
          <>
            <div className="section-header-row" style={{ padding: "24px 32px 12px", marginBottom: "8px" }}>
              <h2 style={{ textTransform: "none", fontSize: "20px", fontWeight: 600, color: "var(--text)", letterSpacing: "normal" }}>Последние</h2>
              <button className="view-all-btn-pill" onClick={() => setTab("invoices")}>
                Все <Icon name="chevron_right" />
              </button>
            </div>
            <div className="recent-docs-card" style={{ marginTop: 0 }}>
              <div className="ios-group no-border">
                {documents.slice(0, 25).map((doc) => (
                  <div className="doc-row clickable" key={doc.id} onClick={() => loadAndPreviewInvoice(doc.id)}>
                    <div className="doc-row-left">
                      <div className="doc-row-title">{doc.title.replace(/^Счет\s*(№|N)?\s*/i, "")} {doc.client_name}</div>
                      <div className="doc-row-meta">
                        <span className="doc-row-date">{new Date(doc.created_at).toLocaleDateString("ru-RU", { day: "numeric", month: "short", year: "numeric" })}</span>
                      </div>
                    </div>
                    <div className="ios-row-right"><Icon name="chevron_right" /></div>
                  </div>
                ))}
              </div>
            </div>
          </>
        ) : (
          <div className="empty-state" style={{ marginTop: 24 }}>
            <div className="empty-state-icon"><Icon name="description" /></div>
            <div className="empty-state-title">Нет документов</div>
            <div className="empty-state-text">Создайте свой первый документ прямо сейчас</div>
          </div>
        )}
        <div className="spacer-24" />
      </div>
    </>
  );

  /* ═══ RENDER: INVOICES TAB — Documents List (Все документы) ═══ */
  const filteredDocs = documents.filter((d) => {
    if (docSearch && !d.title.toLowerCase().includes(docSearch.toLowerCase()) && !d.client_name.toLowerCase().includes(docSearch.toLowerCase())) return false;
    // For now all docs are drafts since we don't have status field
    // if (docFilter === "paid") return d.status === "paid";
    // if (docFilter === "draft") return d.status === "draft";
    return true;
  });
  const invoicesListView = (
    <>
      <div className="nav-bar">
        <div className="nav-bar-inner">
          <h1 className="nav-bar-title">Документы</h1>
          <button className="nav-bar-btn" onClick={openNewInvoice}><Icon name="add" /></button>
        </div>
      </div>
      <div className="search-bar">
        <div className="search-input-wrap">
          <Icon name="search" />
          <input placeholder="Поиск..." value={docSearch} onChange={(e) => setDocSearch(e.target.value)} />
        </div>
      </div>
      <div className="spacer-8" />
      <div className="spacer-8" />
      <div className="content-area">
        {filteredDocs.length === 0 ? (
          <div className="empty-state full-height">
            <div className="empty-state-icon"><Icon name="article" /></div>
            <div className="empty-state-title">Список пуст</div>
            <div className="empty-state-text">По вашему запросу не найдено ни одного документа</div>
          </div>
        ) : (
          <>
            <div className="spacer-8" />
            <div className="ios-group">
              {filteredDocs.map((doc) => (
                <div className="doc-row clickable" key={doc.id} onClick={() => loadAndPreviewInvoice(doc.id)}>
                  <div className="doc-row-left">
                    <div className="doc-row-title">{doc.title.replace(/^Счет\s*(№|N)?\s*/i, "")} {doc.client_name}</div>
                    <div className="doc-row-meta">
                      <span className="doc-row-date">{new Date(doc.created_at).toLocaleDateString("ru-RU", { day: "numeric", month: "short", year: "numeric" })}</span>
                    </div>
                  </div>
                  <div className="ios-row-right"><Icon name="chevron_right" /></div>
                </div>
              ))}
            </div>
            <div className="spacer-24" />
          </>
        )}
      </div>
    </>
  );

  /* ═══ RENDER: INVOICE FORM (sub-view) ═══ */
  const filteredClients = clients.filter((c) => !invoiceClientSearch || c.name.toLowerCase().includes(invoiceClientSearch.toLowerCase()) || c.bin_iin.includes(invoiceClientSearch));
  const invoiceFormView = (
    <>
      <div className="nav-bar">
        <div className="nav-bar-detail">
          <button className="nav-bar-btn-circle" onClick={() => setSubView(null)}>
            <Icon name="close" />
          </button>
          <span className="nav-bar-title-center">{selectedDocId ? `Счет ${invoice.INVOICE_NUMBER}` : "Новый счет"}</span>
          <div className="nav-bar-right">
            <button className="nav-bar-btn-circle" onClick={saveInvoice} disabled={busy !== "idle"}>
              <Icon name="check" />
            </button>
          </div>
        </div>
      </div>
      <div className="content-area has-footer">
        <div className="section-title" style={{ paddingTop: 8 }}>Дата счета</div>
        <div className="ios-group">
          <div className="form-field">
            <input
              type="date"
              className="native-date-input"
              value={invoice.INVOICE_DATE.includes('.') ? invoice.INVOICE_DATE.split('.').reverse().join('-') : invoice.INVOICE_DATE}
              onChange={(e) => {
                const val = e.target.value;
                const [y, m, d] = val.split('-');
                setInvoice((c) => ({ ...c, INVOICE_DATE: (y && m && d) ? `${d}.${m}.${y}` : val }));
              }}
            />
          </div>
        </div>
        <div className="section-title">Клиент</div>
        <div className="ios-group">
          <div className="form-field">
            <span className="form-field-icon"><Icon name="search" /></span>
            <input placeholder="Поиск по имени или БИН" value={invoiceClientSearch} onChange={(e) => setInvoiceClientSearch(e.target.value)} onClick={() => { if (invoiceClientSearch === invoice.CLIENT_NAME) setInvoiceClientSearch("") }} />
          </div>
          {(invoiceClientSearch && invoiceClientSearch !== invoice.CLIENT_NAME) && filteredClients.length > 0 && (
            <>
              {filteredClients.slice(0, 4).map((cl) => (
                <div className="ios-row" key={cl.id} onClick={() => selectClient(cl)} style={{ cursor: "pointer" }}>
                  <div className="ios-row-content">
                    <div className="ios-row-title">{cl.name}</div>
                    <div className="ios-row-subtitle">{cl.bin_iin}</div>
                  </div>
                </div>
              ))}
            </>
          )}
        </div>
        <div className="section-title">Позиции</div>
        {invoice.items.length > 0 && (
          <div className="ios-group">
            {invoice.items.map((it, idx) => (
              <div className="ios-row item-row" key={`inv-${it.number}-${idx}`}>
                <div className="ios-row-content">
                  <div className="ios-row-title">{it.name || "Без названия"}</div>
                  <div className="ios-row-subtitle">
                    {formatMoney(parseMoney(it.price))} ₸ × {it.quantity} {it.unit}
                  </div>
                </div>
                <div className="ios-row-right" style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <div className="qty-selector">
                    <button className="qty-btn" onClick={(e) => { e.stopPropagation(); changeQuantity(idx, -1); }}><Icon name="remove" /></button>
                    <span className="qty-value">{it.quantity}</span>
                    <button className="qty-btn" onClick={(e) => { e.stopPropagation(); changeQuantity(idx, 1); }}><Icon name="add" /></button>
                  </div>
                  <span onClick={(e) => { e.stopPropagation(); removeRow(idx); }} className="item-delete-btn">
                    <Icon name="delete" />
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
        <div style={{ padding: "12px 16px 16px" }}>
          <button className="dashed-add-btn" onClick={() => setSubView("addItem")}>
            <Icon name="add_circle" /> Добавить позицию
          </button>
        </div>
        <div className="section-title">Настройки документа</div>
        <div className="ios-group">
          <div className="toggle-row">
            <div className="toggle-row-left"><Icon name="approval" /><span className="toggle-row-label">Печать</span></div>
            <Toggle checked={invoice.INCLUDE_STAMP} disabled={!profile.stamp_path} onChange={(v) => setInvoice((c) => ({ ...c, INCLUDE_STAMP: v }))} />
          </div>
          <div className="toggle-row">
            <div className="toggle-row-left"><Icon name="draw" /><span className="toggle-row-label">Подпись</span></div>
            <Toggle checked={invoice.INCLUDE_SIGNATURE} disabled={!profile.signature_path} onChange={(v) => setInvoice((c) => ({ ...c, INCLUDE_SIGNATURE: v }))} />
          </div>
          <div className="toggle-row">
            <div className="toggle-row-left"><Icon name="image" /><span className="toggle-row-label">Логотип</span></div>
            <Toggle checked={invoice.INCLUDE_LOGO} disabled={!profile.logo_path} onChange={(v) => setInvoice((c) => ({ ...c, INCLUDE_LOGO: v }))} />
          </div>
        </div>
        {selectedDocId && (
          <div style={{ padding: "0 16px" }}>
            <button className="destructive-btn" onClick={deleteInvoice} disabled={busy !== "idle"}>
              <Icon name="delete" /> Удалить документ
            </button>
          </div>
        )}
        <div className="spacer-24" />
      </div>
      <div className="invoice-footer">
        <div className="invoice-footer-inner">
          <div className="invoice-total-row">
            <span className="invoice-total-label">Общая сумма</span>
            <span className="invoice-total-value">{invoice.TOTAL_SUM} ₸</span>
          </div>
          <button className="invoice-send-btn" disabled={busy !== "idle"} onClick={sendInvoice}>
            <Icon name="send" />{busy === "send" ? "Отправка..." : "Отправить"}
          </button>
        </div>
      </div>
    </>
  );

  /* ═══ RENDER: CLIENTS TAB ═══ */
  const filteredClientsList = clients.filter((c) => !clientSearch || c.name.toLowerCase().includes(clientSearch.toLowerCase()) || c.bin_iin.includes(clientSearch));
  const clientsView = (
    <>
      <div className="nav-bar">
        <div className="nav-bar-inner">
          <h1 className="nav-bar-title">Клиенты</h1>
          <button className="nav-bar-btn" onClick={() => setSubView("addClient")}><Icon name="add" /></button>
        </div>
      </div>
      <div className="search-bar">
        <div className="search-input-wrap"><Icon name="search" /><input placeholder="Поиск..." value={clientSearch} onChange={(e) => setClientSearch(e.target.value)} /></div>
      </div>
      <div className="content-area">
        {filteredClientsList.length === 0 ? (
          <div className="empty-state full-height">
            <div className="empty-state-icon"><Icon name="group" /></div>
            <div className="empty-state-title">База клиентов пуста</div>
            <div className="empty-state-text">Добавьте клиентов, чтобы быстрее оформлять документы</div>
          </div>
        ) : (
          <>
            <div className="spacer-8" />
            <div className="ios-group">
              {filteredClientsList.map((cl) => (
                <div className="ios-row clickable" key={cl.id} onClick={() => {
                  setClientDraft({ name: cl.name, bin_iin: cl.bin_iin, phone: cl.phone || "", contact_name: cl.contact_name || "" });
                  setSelectedCatalogClient(cl);
                  setSubView("addClient");
                }}>
                  <div className="ios-row-content">
                    <div className="ios-row-title">{cl.name}</div>
                    <div className="ios-row-subtitle">{cl.bin_iin ? `${cl.bin_iin.length === 12 ? "БИН" : "ИИН"} ${cl.bin_iin}` : "Без БИН/ИИН"}</div>
                  </div>
                  <div className="ios-row-right"><Icon name="chevron_right" /></div>
                </div>
              ))}
            </div>
            <div className="spacer-24" />
          </>
        )}
      </div>
    </>
  );

  /* ═══ RENDER: ITEMS TAB ═══ */
  const filteredItemsList = items.filter((i) => !itemSearch || i.name.toLowerCase().includes(itemSearch.toLowerCase()));
  const itemsView = (
    <>
      <div className="nav-bar">
        <div className="nav-bar-inner">
          <h1 className="nav-bar-title">Каталог</h1>
          <button className="nav-bar-btn" onClick={() => setSubView("addItem")}><Icon name="add" /></button>
        </div>
      </div>
      <div className="search-bar">
        <div className="search-input-wrap"><Icon name="search" /><input placeholder="Поиск..." value={itemSearch} onChange={(e) => setItemSearch(e.target.value)} /></div>
      </div>
      <div className="content-area">
        {filteredItemsList.length === 0 ? (
          <div className="empty-state full-height">
            <div className="empty-state-icon"><Icon name="inventory_2" /></div>
            <div className="empty-state-title">Каталог пуст</div>
            <div className="empty-state-text">Добавьте товары или услуги для автоматического расчета</div>
          </div>
        ) : (
          <>
            <div className="spacer-8" />
            <div className="ios-group">
              {filteredItemsList.map((it) => (
                <div className="ios-row clickable" key={it.id} onClick={() => {
                  setItemDraft({ name: it.name, unit: it.unit, price: String(it.price), sku: it.sku || "" });
                  setSelectedCatalogItem(it);
                  setSubView("addItem");
                }}>
                  <div className="ios-row-content">
                    <div className="ios-row-title">{it.name}</div>
                    <div className="ios-row-subtitle">{formatMoney(it.price)} ₸</div>
                  </div>
                  <div className="ios-row-right"><Icon name="chevron_right" /></div>
                </div>
              ))}
            </div>
            <div className="spacer-24" />
          </>
        )}
      </div>
    </>
  );

  /* ═══ RENDER: PROFILE TAB ═══ */
  const profileView = (
    <>
      <div className="nav-bar">
        <div className="nav-bar-inner"><h1 className="nav-bar-title">Профиль</h1><div /></div>
      </div>
      <div className="content-area">
        <div className="section-title" style={{ paddingTop: 8 }}>Реквизиты</div>
        {profile.company_name ? (
          <div className="ios-group">
            <div className="ios-row" style={{ justifyContent: "space-between", alignItems: "flex-start" }}>
              <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                <span style={{ fontSize: 15, fontWeight: 600 }}>{profile.company_name}</span>
                <span style={{ fontSize: 13, color: "var(--text-secondary)" }}>БИН: {profile.company_iin}</span>
                <span style={{ fontSize: 13, color: "var(--text-secondary)" }}>Директор: {profile.executor_name}</span>
              </div>
              <button className="requisites-card-edit" onClick={() => { setProfileDraft(profile); setSubView("editRequisites"); }}><Icon name="edit" /></button>
            </div>
          </div>
        ) : (
          <div style={{ padding: "0 16px", marginBottom: 20 }}>
            <button className="dashed-add-btn" onClick={() => { setProfileDraft(profile); setSubView("editRequisites"); }}>
              <Icon name="add_circle" /> Добавить реквизиты
            </button>
          </div>
        )}
        <div className="section-title">Банковские счета</div>
        {profile.company_iic ? (
          <>
            <div className="ios-group">
              <div className="ios-row" style={{ justifyContent: "space-between", alignItems: "flex-start" }}>
                <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                  <span style={{ fontSize: 15, fontWeight: 600 }}>{profile.company_iic}</span>
                  <span style={{ fontSize: 13, color: "var(--text-secondary)" }}>Банк: {profile.beneficiary_bank}</span>
                  <div><span className="badge badge-blue">Основной</span></div>
                </div>
                <button className="requisites-card-edit" onClick={() => { setProfileDraft(profile); setSubView("addBankAccount"); }}><Icon name="edit" /></button>
              </div>
            </div>
            <div style={{ padding: "12px 16px 0" }}>
              <button className="dashed-add-btn" onClick={() => { setProfileDraft(profile); setSubView("addBankAccount"); }}><Icon name="add_circle" /> Добавить счет</button>
            </div>
          </>
        ) : (
          <div style={{ padding: "0 16px", marginBottom: 20 }}>
            <button className="dashed-add-btn" onClick={() => { setProfileDraft(profile); setSubView("addBankAccount"); }}><Icon name="add_circle" /> Добавить счет</button>
          </div>
        )}
        <div className="section-title">Оформление документов</div>
        <div className="ios-group">
          <ImageUploadRow label="Логотип" hint="PNG или JPG, макс. 2МБ" imageType="logo" onStatusChange={setStatus} />
          <ImageUploadRow label="Подпись" hint="На прозрачном фоне" imageType="signature" onStatusChange={setStatus} />
          <ImageUploadRow label="Печать" hint="Круглая печать организации" imageType="stamp" onStatusChange={setStatus} />
        </div>
        <div className="section-title">Общие настройки</div>
        <div className="ios-group">
          <div className="settings-row">
            <div className="settings-row-left">
              <div className="settings-icon red"><Icon name="notifications" filled /></div>
              <span className="settings-row-label">Уведомления</span>
            </div>
            <Toggle checked={true} onChange={() => { }} />
          </div>
          <div className="settings-row">
            <div className="settings-row-left">
              <div className="settings-icon blue"><Icon name="language" /></div>
              <span className="settings-row-label">Язык</span>
            </div>
            <div className="settings-row-right"><span>Русский</span><Icon name="chevron_right" /></div>
          </div>
          <div className="settings-row">
            <div className="settings-row-left">
              <div className="settings-icon dark"><Icon name="dark_mode" /></div>
              <span className="settings-row-label">Оформление</span>
            </div>
            <div className="settings-row-right"><span>Системное</span><Icon name="chevron_right" /></div>
          </div>
        </div>
        <div className="version-text">Версия приложения 1.0.0</div>
      </div>
    </>
  );

  /* ═══ FULL-PAGE SUB-VIEWS (replace modals) ═══ */

  /* Add Client — full page (like ux/code.html pattern) */
  const addClientView = (
    <>
      <header className="nav-bar">
        <div className="nav-bar-detail">
          <button className="nav-bar-btn-circle" onClick={() => { setSubView(tab === "home" ? "invoiceForm" : null); setSelectedCatalogClient(null); }}>
            <Icon name="close" />
          </button>
          <span className="nav-bar-title-center">{selectedCatalogClient ? "Клиент" : "Новый клиент"}</span>
          <button className="nav-bar-btn-circle" onClick={createClient}>
            <Icon name="check" />
          </button>
        </div>
      </header>
      <div className="content-area">
        <div className="ios-group" style={{ marginTop: 16 }}>
          <div className="form-field">
            <input
              placeholder="БИН/ИИН"
              value={clientDraft.bin_iin}
              onChange={(e) => {
                const val = e.target.value;
                setClientDraft((c) => ({ ...c, bin_iin: val }));
                const found = clients.find(cl => cl.bin_iin === val.trim() && val.trim() !== "");
                if (found) {
                  setClientDraft({ name: found.name, bin_iin: found.bin_iin, phone: found.phone || "", contact_name: found.contact_name || "" });
                  setSelectedCatalogClient(found);
                }
              }}
            />
          </div>
          {clientDraft.bin_iin && !clients.find(cl => cl.bin_iin === clientDraft.bin_iin.trim()) && clients.filter(cl => cl.bin_iin.includes(clientDraft.bin_iin)).length > 0 && (
            <>
              {clients.filter(cl => cl.bin_iin.includes(clientDraft.bin_iin)).slice(0, 4).map(found => (
                <div className="ios-row" key={found.id} onClick={() => {
                  setClientDraft({ name: found.name, bin_iin: found.bin_iin, phone: found.phone || "", contact_name: found.contact_name || "" });
                  setSelectedCatalogClient(found);
                }} style={{ cursor: "pointer", background: "rgba(0,123,255,0.05)" }}>
                  <div className="ios-row-content">
                    <div className="ios-row-title">{found.name}</div>
                    <div className="ios-row-subtitle">{found.bin_iin}</div>
                  </div>
                </div>
              ))}
            </>
          )}
          <div className="form-field"><input placeholder="Название (ТОО / ИП)" value={clientDraft.name} onChange={(e) => setClientDraft((c) => ({ ...c, name: e.target.value }))} /></div>
          <div className="form-field"><input placeholder="Телефон (+7...)" value={clientDraft.phone} onChange={(e) => setClientDraft((c) => ({ ...c, phone: e.target.value }))} /></div>
        </div>
        {selectedCatalogClient && (
          <div style={{ padding: "24px 16px 8px" }}>
            <button className="destructive-btn" disabled={busy !== "idle"} onClick={deleteClient}>
              Удалить клиента
            </button>
          </div>
        )}
      </div>
    </>
  );

  /* Add Item — full page (matches ux/code.html exactly) */
  const addItemView = (
    <>
      <header className="nav-bar">
        <div className="nav-bar-detail">
          <button className="nav-bar-btn-circle" onClick={() => { setSubView(tab === "home" ? "invoiceForm" : null); setSelectedCatalogItem(null); }}>
            <Icon name="close" />
          </button>
          <span className="nav-bar-title-center">{selectedCatalogItem ? "Товар/Услуга" : "Добавить товар"}</span>
          <button className="nav-bar-btn-circle" onClick={createItem}>
            <Icon name="check" />
          </button>
        </div>
      </header>
      <div className="content-area">
        <div className="ios-group" style={{ marginTop: 16 }}>
          <div className="form-field">
            <input
              placeholder="Название (поиск или новое)"
              value={itemDraft.name}
              onChange={(e) => setItemDraft((c) => ({ ...c, name: e.target.value }))}
            />
          </div>
          {itemDraft.name && !items.find(i => i.name.toLowerCase() === itemDraft.name.trim().toLowerCase()) && items.filter(i => i.name.toLowerCase().includes(itemDraft.name.toLowerCase())).length > 0 && (
            <>
              {items.filter(i => i.name.toLowerCase().includes(itemDraft.name.toLowerCase())).slice(0, 4).map(it => (
                <div className="ios-row" key={it.id} onClick={() => {
                  setItemDraft({ name: it.name, unit: it.unit, price: String(it.price), sku: it.sku || "" });
                  setSelectedCatalogItem(it);
                }} style={{ cursor: "pointer", background: "rgba(0,123,255,0.05)" }}>
                  <div className="ios-row-content">
                    <div className="ios-row-title">{it.name}</div>
                    <div className="ios-row-subtitle">{formatMoney(it.price)} ₸ / {it.unit}</div>
                  </div>
                </div>
              ))}
            </>
          )}
          <div className="form-field"><input placeholder="Ед. изм. (час, шт., кг)" value={itemDraft.unit} onChange={(e) => setItemDraft((c) => ({ ...c, unit: e.target.value }))} /></div>
          <div className="form-field"><input placeholder="Цена (50 000)" type="number" value={itemDraft.price} onChange={(e) => setItemDraft((c) => ({ ...c, price: e.target.value }))} /></div>
          <div className="form-field"><input placeholder="Артикул (001)" value={itemDraft.sku} onChange={(e) => setItemDraft((c) => ({ ...c, sku: e.target.value }))} /></div>
        </div>
        {selectedCatalogItem && (
          <div style={{ padding: "24px 16px 8px" }}>
            <button className="destructive-btn" disabled={busy !== "idle"} onClick={deleteItem}>
              Удалить товар/услугу
            </button>
          </div>
        )}
      </div>
    </>
  );

  /* Edit Requisites — full page */
  const editRequisitesView = (
    <>
      <header className="nav-bar">
        <div className="nav-bar-detail">
          <button className="nav-bar-btn-circle" onClick={() => setSubView(null)}>
            <Icon name="close" />
          </button>
          <span className="nav-bar-title-center">Реквизиты</span>
          <button className="nav-bar-btn-circle" onClick={() => { saveProfile(); setSubView(null); }}>
            <Icon name="check" />
          </button>
        </div>
      </header>
      <div className="content-area">
        <div className="section-title" style={{ paddingTop: 8 }}>Реквизиты организации</div>
        <div className="ios-group">
          <div className="form-field"><input placeholder="БИН (12-значный номер)" value={profileDraft.company_iin} onChange={(e) => setProfileDraft((c) => ({ ...c, company_iin: e.target.value }))} /></div>
          <div className="form-field"><input placeholder="Название организации" value={profileDraft.company_name} onChange={(e) => setProfileDraft((c) => ({ ...c, company_name: e.target.value }))} /></div>
          <div className="form-field"><input placeholder="Адрес (Юридический адрес)" value={profileDraft.supplier_address} onChange={(e) => setProfileDraft((c) => ({ ...c, supplier_address: e.target.value }))} /></div>
          <div className="form-field"><input placeholder="ФИО (например, Иванов И.И.)" value={profileDraft.executor_name} onChange={(e) => setProfileDraft((c) => ({ ...c, executor_name: e.target.value }))} /></div>
          <div className="form-field"><input placeholder="Должность (например, Директор)" value={profileDraft.position} onChange={(e) => setProfileDraft((c) => ({ ...c, position: e.target.value }))} /></div>
        </div>
        <div className="section-title">Контакты</div>
        <div className="ios-group">
          <div className="form-field"><input placeholder="Телефон (+7...)" value={profileDraft.phone} onChange={(e) => setProfileDraft((c) => ({ ...c, phone: e.target.value }))} /></div>
          <div className="form-field"><input placeholder="Email (email@example.com)" value={profileDraft.email} onChange={(e) => setProfileDraft((c) => ({ ...c, email: e.target.value }))} /></div>
        </div>
        {profile.company_iin && (
          <div style={{ padding: "24px 16px 8px" }}>
            <button className="destructive-btn" disabled={busy !== "idle"} onClick={deleteRequisites}>
              Удалить реквизиты
            </button>
          </div>
        )}
      </div>
    </>
  );

  /* Add Bank Account — full page (matches _5/code.html exactly) */
  const addBankAccountView = (
    <>
      <header className="nav-bar">
        <div className="nav-bar-detail">
          <button className="nav-bar-btn-circle" onClick={() => setSubView(null)}>
            <Icon name="close" />
          </button>
          <span className="nav-bar-title-center">Добавить счет</span>
          <button className="nav-bar-btn-circle" onClick={() => { saveProfile(); setSubView(null); }}>
            <Icon name="check" />
          </button>
        </div>
      </header>
      <div className="content-area">
        <div className="section-title" style={{ paddingTop: 8 }}>Реквизиты счета</div>
        <div className="ios-group">
          <div className="form-field"><input placeholder="IBAN (Например, KZ...)" value={profileDraft.company_iic} onChange={(e) => setProfileDraft((c) => ({ ...c, company_iic: e.target.value }))} /></div>
          <div className="form-field"><input placeholder="БИК банка" value={profileDraft.company_bic} onChange={(e) => setProfileDraft((c) => ({ ...c, company_bic: e.target.value }))} /></div>
          <div className="form-field"><input placeholder="Название банка" value={profileDraft.beneficiary_bank} onChange={(e) => setProfileDraft((c) => ({ ...c, beneficiary_bank: e.target.value }))} /></div>
        </div>
        <div className="section-title">Состояние</div>
        <div className="ios-group">
          <div className="toggle-row">
            <span className="toggle-row-label">Сделать основным</span>
            <Toggle checked={true} onChange={() => { }} />
          </div>
        </div>
        <div className="form-hint">Этот счет будет использоваться по умолчанию для всех новых счетов-фактур.</div>
        {profile.company_iic && (
          <div style={{ padding: "24px 16px 8px" }}>
            <button className="destructive-btn" disabled={busy !== "idle"} onClick={deleteBankAccount}>
              Удалить счет
            </button>
          </div>
        )}
      </div>
    </>
  );

  /* View Document — full page with PDF preview */
  const selectedDoc = documents.find(d => d.id === selectedDocId);
  const viewDocumentView = (
    <>
      <header className="nav-bar">
        <div className="nav-bar-detail">
          <button className="nav-bar-back" onClick={() => setSubView(null)}><Icon name="chevron_left" /><span>Назад</span></button>
          <span className="nav-bar-title-center">{selectedDoc?.title.replace(/^Счет\s*(№|N)?\s*/i, "") || "Просмотр счета"}</span>
          <div className="nav-bar-right">
            <button className="nav-bar-btn" title="Редактировать" onClick={() => setSubView("invoiceForm")}>
              <Icon name="edit" />
            </button>
            <button className="nav-bar-btn" onClick={() => window.open(`${API_BASE_URL}/documents/${selectedDocId}/pdf`, '_blank')}>
              <Icon name="download" />
            </button>
          </div>
        </div>
      </header>
      <div className="content-area" style={{ paddingBottom: 0, height: "calc(100vh - 64px)", overflow: "hidden" }}>
        {selectedDocId && (
          <iframe
            src={`${API_BASE_URL}/documents/${selectedDocId}/pdf#toolbar=0&navpanes=0`}
            style={{ width: "100%", height: "100%", border: "none" }}
            title="PDF Preview"
          />
        )}
      </div>
    </>
  );



  /* ═══ MAIN RENDER ═══ */
  const tabIcons: Record<TabKey, string> = { home: "description", invoices: "description", clients: "group", items: "inventory_2", profile: "person" };
  const tabLabels: Record<TabKey, string> = { home: "Документы", invoices: "Документы", clients: "Клиенты", items: "Каталог", profile: "Профиль" };

  // Sub-view routing
  const subViewContent = subView === "invoiceForm" ? invoiceFormView
    : subView === "addClient" ? addClientView
      : subView === "addItem" ? addItemView
        : subView === "editRequisites" ? editRequisitesView
          : subView === "addBankAccount" ? addBankAccountView
            : subView === "viewDocument" ? viewDocumentView
              : null;

  return (
    <main className="app-shell">
      <div className={`status-banner${status ? " visible" : ""}`}>{status}</div>
      {subViewContent ? (
        subViewContent
      ) : (
        <>
          {tab === "home" && homeView}
          {tab === "invoices" && invoicesListView}
          {tab === "clients" && clientsView}
          {tab === "items" && itemsView}
          {tab === "profile" && profileView}
        </>
      )}
      {!subViewContent && (
        <nav className="tab-bar">
          <div className="tab-bar-inner">
            {(["home", "clients", "items", "profile"] as TabKey[]).map((t) => (
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

