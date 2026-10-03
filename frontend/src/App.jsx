import { useEffect, useState } from "react";

const EMPTY = {
  guest: false,
  ups_user_id: "",
  payment_type: "bill_shipper",
  billed_account: "9A4K2M",
  shipper_account: "9A4K2M",
  ship_from_postal: "400001",
  ship_from_country: "IN",
  ship_to_postal: "380001",
  ship_to_country: "IN",
  service: "ground",
  weight_kg: 7.5,
};

async function api(path, options) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Request failed (${response.status})`);
  }
  return response.json();
}

export default function App() {
  const [view, setView] = useState("book");
  const [scenarios, setScenarios] = useState([]);
  const [activeId, setActiveId] = useState(null);
  const [form, setForm] = useState(EMPTY);
  const [result, setResult] = useState(null);
  const [queue, setQueue] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    api("/v1/scenarios").then(setScenarios).catch((err) => setError(err.message));
    refreshQueue();
  }, []);

  async function refreshQueue() {
    const rows = await api("/v1/decisions");
    setQueue(rows);
  }

  function update(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  async function check(booking) {
    setLoading(true);
    setError("");
    const payload = {
      ...booking,
      weight_kg: Number(booking.weight_kg),
      guest: Boolean(booking.guest),
      ups_user_id: booking.guest ? null : booking.ups_user_id || null,
      billed_account: booking.payment_type === "card" ? null : booking.billed_account || null,
      shipper_account: booking.shipper_account || null,
    };
    try {
      const decision = await api("/v1/booking-risk", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      setResult(decision);
      await refreshQueue();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  function choose(scenario) {
    setActiveId(scenario.id);
    setForm({ ...EMPTY, ...scenario.booking, weight_kg: scenario.booking.weight_kg });
    check(scenario.booking);
  }

  async function resetDemo() {
    await api("/v1/reset", { method: "POST" });
    setResult(null);
    setActiveId(null);
    setQueue([]);
  }

  return (
    <div className="app">
      <header className="top">
        <div className="top-row">
          <div>
            <div className="kicker">CONFIRM GATE · PROTOTYPE</div>
            <h1>Check the booking before the label.</h1>
            <p className="lede">
              The risk call runs inside confirm, before payment is captured. Rules choose the action. XGBoost can hold a clean booking. It cannot block one.
            </p>
          </div>
          <div className="nav">
            <button className={view === "book" ? "active" : ""} onClick={() => setView("book")}>Check a booking</button>
            <button className={view === "queue" ? "active" : ""} onClick={() => setView("queue")}>Review queue</button>
            <button onClick={resetDemo}>Reset</button>
          </div>
        </div>
      </header>

      <main className="wrap">
        {error && <p className="error">{error}</p>}
        {view === "book" ? (
          <section className="layout">
            <div className="card">
              <h2>Try a case</h2>
              <div className="scenarios">
                {scenarios.map((scenario) => (
                  <button
                    key={scenario.id}
                    className={scenario.id === activeId ? "scenario active" : "scenario"}
                    onClick={() => choose(scenario)}
                  >
                    <strong>{scenario.label}</strong>
                    <span className={`expect ${scenario.expect}`}>Expect {scenario.expect}</span>
                    <span>{scenario.blurb}</span>
                  </button>
                ))}
              </div>

              <form
                className="form"
                onSubmit={(event) => {
                  event.preventDefault();
                  setActiveId(null);
                  check(form);
                }}
              >
                <label>
                  Payment
                  <select value={form.payment_type} onChange={(event) => update("payment_type", event.target.value)}>
                    <option value="bill_shipper">Bill shipper account</option>
                    <option value="bill_receiver">Bill receiver</option>
                    <option value="bill_third_party">Bill third party</option>
                    <option value="card">Card</option>
                  </select>
                </label>
                <label>
                  Billed account
                  <input value={form.billed_account || ""} onChange={(event) => update("billed_account", event.target.value.toUpperCase())} />
                </label>
                <label>
                  Shipper account
                  <input value={form.shipper_account || ""} onChange={(event) => update("shipper_account", event.target.value.toUpperCase())} />
                </label>
                <label>
                  UPS user
                  <input value={form.ups_user_id || ""} onChange={(event) => update("ups_user_id", event.target.value)} disabled={form.guest} />
                </label>
                <label>
                  From postal
                  <input value={form.ship_from_postal} onChange={(event) => update("ship_from_postal", event.target.value)} />
                </label>
                <label>
                  From country
                  <input value={form.ship_from_country} onChange={(event) => update("ship_from_country", event.target.value.toUpperCase())} />
                </label>
                <label>
                  To postal
                  <input value={form.ship_to_postal} onChange={(event) => update("ship_to_postal", event.target.value)} />
                </label>
                <label>
                  To country
                  <input value={form.ship_to_country} onChange={(event) => update("ship_to_country", event.target.value.toUpperCase())} />
                </label>
                <label>
                  Service
                  <select value={form.service} onChange={(event) => update("service", event.target.value)}>
                    <option value="ground">Ground</option>
                    <option value="express">Express</option>
                    <option value="international">International</option>
                  </select>
                </label>
                <label>
                  Weight (kg)
                  <input type="number" min="0.1" step="0.1" value={form.weight_kg} onChange={(event) => update("weight_kg", event.target.value)} />
                </label>
                <label className="check">
                  <input type="checkbox" checked={Boolean(form.guest)} onChange={(event) => update("guest", event.target.checked)} />
                  Guest session
                </label>
                <button className="primary span-2" disabled={loading} type="submit">
                  {loading ? "Checking…" : "Run confirm check"}
                </button>
              </form>
            </div>
            <Result result={result} loading={loading} />
          </section>
        ) : (
          <Queue rows={queue} />
        )}
      </main>
    </div>
  );
}

function Result({ result, loading }) {
  return (
    <aside className="card result">
      <div className="flow">
        <i>Ship from</i><i>Ship to</i><i>Package</i><i>Payer</i><i className="on">Confirm</i>
      </div>
      <h2>Decision</h2>
      {!result && <p className="empty">Pick a case. Allow is the only path that would print a label.</p>}
      {result && (
        <div>
          <div className={`decision ${result.decision}-bg`}>
            <b>{result.decision.toUpperCase()}</b>
            <div className="score" aria-hidden="true"><span style={{ width: `${Math.round(result.score * 100)}%` }} /></div>
            <p>Score {result.score.toFixed(2)} · {result.policy_version}</p>
          </div>
          <div className="codes">
            {(result.reason_codes.length ? result.reason_codes : ["NO_RULE_FIRED"]).map((code) => (
              <em key={code}>{code}</em>
            ))}
          </div>
          <p className="explain">{result.explanation}</p>
          <p className="meta">
            {result.tx_id} · note from {result.explanation_source === "llm" ? "the language model" : "the reason codes"}
            {loading ? " · updating" : ""}
          </p>
        </div>
      )}
    </aside>
  );
}

function Queue({ rows }) {
  if (!rows.length) {
    return <p className="empty">No bookings checked yet.</p>;
  }
  return (
    <div className="queue">
      {rows.map((row) => (
        <article key={row.tx_id} className="q">
          <div>
            <span className={`tag ${row.decision}-bg`}>{row.decision}</span>
          </div>
          <div>
            <strong>{row.billed_account || "Card"} · score {row.score.toFixed(2)}</strong>
            <div className="codes">
              {(row.reason_codes.length ? row.reason_codes : ["NO_RULE_FIRED"]).map((code) => (
                <em key={code}>{code}</em>
              ))}
            </div>
            <p>{row.explanation}</p>
            <p className="meta">{row.created_at} · {row.tx_id}</p>
          </div>
        </article>
      ))}
    </div>
  );
}
