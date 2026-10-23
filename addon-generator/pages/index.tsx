import { useState } from "react";
import axios from "axios";

export default function Home() {
  const [query, setQuery] = useState("");
  const [result, setResult] = useState<null | any>(null);
  const [theme, setTheme] = useState("Star Wars");
  const [mc, setMc] = useState("28.0");

  const search = async () => {
    try {
      const r = await axios.post("/api/search", { query });
      setResult(r.data);
    } catch (e) {
      setResult({ error: e.message });
    }
  };

  const create = async () => {
    if (!result) return;
    await axios.post("/api/create", { theme, mc_version: mc, text: result.extract });
    alert("Addon generation requested (stub)!" );
  };

  return (
    <div style={{ padding: 20 }}>
      <h1>Addon Generator</h1>
      <input
        placeholder="Search query"
        value={query}
        onChange={e => setQuery(e.target.value)}
        style={{ width: "100%", marginBottom: 10 }}
      />
      <button onClick={search} style={{ marginRight: 10 }}>Get Wikipedia snippet</button>
      <button onClick={create} disabled={!result}>Generate Addon</button>
      <div style={{ marginTop: 10 }}>
        <label>Theme: {' '}
          <select value={theme} onChange={e => setTheme(e.target.value)}>
            <option>Star Wars</option>
            <option>Lord of the Rings</option>
            <option>Harry Potter</option>
            <option>Attack on Titan</option>
          </select>
        </label>
        <label style={{ marginLeft: 20 }}>MC Version: {' '}
          <input value={mc} onChange={e => setMc(e.target.value)} style={{ width: 60 }} />
        </label>
      </div>
      {result && (
        <div style={{ marginTop: 20 }}>
          <h3>{result.title}</h3>
          <p>{result.extract}</p>
        </div>
      )}
    </div>
  );
}
