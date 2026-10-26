// 東証上場 ETF 一覧サイトの共通ユーティリティ。

const fmt = (v, d = 2) => (v === null || v === undefined || Number.isNaN(v)) ? "—" : Number(v).toLocaleString("ja-JP", { minimumFractionDigits: d, maximumFractionDigits: d });

const signed = (v) => {
  if (v === null || v === undefined || Number.isNaN(v)) return { t: "—", c: "" };
  const n = Number(v);
  const t = (n > 0 ? "+" : "") + n.toFixed(2);
  const c = n > 0 ? "up" : n < 0 ? "down" : "";
  return { t, c };
};

const pctFmt = (v) => {
  if (v === null || v === undefined || Number.isNaN(v)) return "—";
  const n = Number(v);
  return (n * 100).toFixed(2) + "%";
};

// xlsx のセル値（数値、"99（注1）"、"0.26%"、"-" 等の文字列）を数値に正規化する。
const toNum = (v) => {
  if (v === null || v === undefined || Number.isNaN(v)) return null;
  if (typeof v === "number") return v;
  const m = String(v).replace(/（注[^）]*）/g, "").replace(/,/g, "").trim().match(/-?[\d.]+/);
  return m ? parseFloat(m[0]) : null;
};

// 総経費率は浮動小数は小数表記（0.0026）、"0.26%" 表記の文字列は百分率なので小数に揃える。
const toFee = (v) => {
  if (v === null || v === undefined || Number.isNaN(v)) return null;
  if (typeof v === "string" && v.includes("%")) {
    const n = toNum(v);
    return n === null ? null : n / 100;
  }
  return toNum(v);
};

// 総経費率セルの表示: "-"(xlsx の未公表プレースホルダー) は「未公表」、
// 空白は「—」、それ以外は toFee/pctFmt で百分率表示。
const feeCell = (v) => {
  if (typeof v === "string" && v.trim() === "-") return "未公表";
  return pctFmt(toFee(v));
};
