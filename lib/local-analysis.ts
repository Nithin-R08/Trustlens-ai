import * as XLSX from "xlsx";
import type { TrustLensResult } from "./api";

type Row = Record<string, unknown>;

const SENSITIVE_KEYWORDS: Record<string, string[]> = {
  gender: ["gender", "sex"],
  age: ["age", "dob", "birth"],
  income: ["income", "salary", "wage", "earning"],
  region: ["region", "location", "state", "city", "country", "zipcode", "zip"],
  caste: ["caste", "ethnicity", "race", "community"]
};

const TARGET_CANDIDATES = [
  "target",
  "label",
  "outcome",
  "class",
  "approved",
  "default",
  "churn",
  "fraud",
  "hired",
  "selected",
  "status"
];

const POSITIVE_VALUES = new Set([
  "1",
  "true",
  "yes",
  "y",
  "approved",
  "accepted",
  "selected",
  "hired",
  "success",
  "positive",
  "pass",
  "churn"
]);

function normalizeColumn(value: string) {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, "_");
}

function cleanCell(value: unknown) {
  if (value === null || value === undefined) {
    return "";
  }
  return String(value).trim();
}

function toNumber(value: unknown) {
  const cleaned = cleanCell(value).replace(/,/g, "");
  if (!cleaned) {
    return null;
  }
  const parsed = Number(cleaned);
  return Number.isFinite(parsed) ? parsed : null;
}

function round(value: number) {
  return Number(value.toFixed(3));
}

async function readRows(file: File): Promise<Row[]> {
  const extension = file.name.split(".").pop()?.toLowerCase();
  const buffer = await file.arrayBuffer();
  const workbook =
    extension === "csv"
      ? XLSX.read(new TextDecoder().decode(buffer), { type: "string" })
      : XLSX.read(buffer, { type: "array" });

  const firstSheet = workbook.SheetNames[0];
  if (!firstSheet) {
    throw new Error("No worksheet found in this file.");
  }

  return XLSX.utils.sheet_to_json<Row>(workbook.Sheets[firstSheet], {
    defval: "",
    raw: false
  });
}

function getColumns(rows: Row[]) {
  return Array.from(new Set(rows.flatMap((row) => Object.keys(row))));
}

function detectSensitiveAttributes(columns: string[]) {
  return columns.filter((column) => {
    const normalized = normalizeColumn(column);
    return Object.values(SENSITIVE_KEYWORDS).some((keywords) =>
      keywords.some((keyword) => normalized.includes(keyword))
    );
  });
}

function inferTargetColumn(columns: string[]) {
  return columns.find((column) => {
    const normalized = normalizeColumn(column);
    return TARGET_CANDIDATES.some((candidate) => normalized.includes(candidate));
  });
}

function valueCounts(rows: Row[], column: string) {
  const counts = new Map<string, number>();
  rows.forEach((row) => {
    const value = cleanCell(row[column]) || "Missing";
    counts.set(value, (counts.get(value) ?? 0) + 1);
  });
  return counts;
}

function getPositiveRate(rows: Row[], targetColumn?: string) {
  if (!targetColumn || rows.length === 0) {
    return 0;
  }

  const positives = rows.filter((row) => {
    const raw = cleanCell(row[targetColumn]).toLowerCase();
    return POSITIVE_VALUES.has(raw) || Number(raw) === 1;
  }).length;

  return positives / rows.length;
}

function computeRepresentation(rows: Row[], sensitiveAttributes: string[]) {
  const underrepresented: Array<Record<string, string | number>> = [];
  const overrepresented: Array<Record<string, string | number>> = [];
  let maxSpread = 0;

  sensitiveAttributes.forEach((attribute) => {
    const counts = valueCounts(rows, attribute);
    const percentages = Array.from(counts.entries()).map(([group, count]) => ({
      group,
      percentage: rows.length ? (count / rows.length) * 100 : 0
    }));

    percentages.forEach(({ group, percentage }) => {
      if (percentage < 10) {
        underrepresented.push({ attribute, group, percentage: round(percentage) });
      }
      if (percentage > 60) {
        overrepresented.push({ attribute, group, percentage: round(percentage) });
      }
    });

    if (percentages.length > 1) {
      const values = percentages.map((item) => item.percentage / 100);
      maxSpread = Math.max(maxSpread, Math.max(...values) - Math.min(...values));
    }
  });

  return {
    underrepresented,
    overrepresented,
    representationImbalance: round(maxSpread)
  };
}

function computeGroupRates(rows: Row[], sensitiveAttributes: string[], targetColumn?: string) {
  const rates: number[] = [];

  sensitiveAttributes.forEach((attribute) => {
    valueCounts(rows, attribute).forEach((_count, group) => {
      const groupRows = rows.filter((row) => (cleanCell(row[attribute]) || "Missing") === group);
      if (groupRows.length >= 2) {
        rates.push(getPositiveRate(groupRows, targetColumn));
      }
    });
  });

  if (!rates.length) {
    return { demographicParityDifference: 0, disparateImpactRatio: 1, statisticalParity: 1 };
  }

  const minRate = Math.min(...rates);
  const maxRate = Math.max(...rates);
  const difference = maxRate - minRate;

  return {
    demographicParityDifference: round(difference),
    disparateImpactRatio: round(maxRate === 0 ? 1 : minRate / maxRate),
    statisticalParity: round(Math.max(0, 1 - difference))
  };
}

function numericSeries(rows: Row[], column: string) {
  return rows.map((row) => toNumber(row[column])).filter((value): value is number => value !== null);
}

function encodeSeries(rows: Row[], column: string) {
  const codes = new Map<string, number>();
  return rows.map((row) => {
    const value = cleanCell(row[column]) || "Missing";
    if (!codes.has(value)) {
      codes.set(value, codes.size + 1);
    }
    return codes.get(value) ?? 0;
  });
}

function correlation(left: number[], right: number[]) {
  if (left.length !== right.length || left.length < 3) {
    return 0;
  }

  const leftMean = left.reduce((sum, value) => sum + value, 0) / left.length;
  const rightMean = right.reduce((sum, value) => sum + value, 0) / right.length;
  let numerator = 0;
  let leftTotal = 0;
  let rightTotal = 0;

  left.forEach((value, index) => {
    const leftDelta = value - leftMean;
    const rightDelta = right[index] - rightMean;
    numerator += leftDelta * rightDelta;
    leftTotal += leftDelta ** 2;
    rightTotal += rightDelta ** 2;
  });

  const denominator = Math.sqrt(leftTotal * rightTotal);
  return denominator ? numerator / denominator : 0;
}

function detectProxyFeatures(rows: Row[], columns: string[], sensitiveAttributes: string[]) {
  const proxyFeatures = new Set<string>();

  sensitiveAttributes.forEach((attribute) => {
    const sensitiveSeries = encodeSeries(rows, attribute);
    columns
      .filter((column) => column !== attribute)
      .forEach((column) => {
        const numbers = numericSeries(rows, column);
        if (numbers.length !== rows.length) {
          return;
        }
        if (Math.abs(correlation(sensitiveSeries, numbers)) >= 0.6) {
          proxyFeatures.add(column);
        }
      });
  });

  return Array.from(proxyFeatures);
}

function computeClassBalance(rows: Row[], targetColumn?: string) {
  if (!targetColumn) {
    return 1;
  }

  const counts = Array.from(valueCounts(rows, targetColumn).values());
  if (counts.length < 2) {
    return 1;
  }

  return round(Math.min(...counts) / Math.max(...counts));
}

function riskFromScore(score: number): "High" | "Medium" | "Low" {
  if (score < 40) {
    return "High";
  }
  if (score < 70) {
    return "Medium";
  }
  return "Low";
}

export async function analyzeDatasetLocally(file: File): Promise<TrustLensResult> {
  const rows = await readRows(file);
  if (rows.length < 2) {
    throw new Error("Upload at least two rows so TrustLens can compare groups.");
  }

  const columns = getColumns(rows);
  const sensitiveAttributes = detectSensitiveAttributes(columns);
  const targetColumn = inferTargetColumn(columns);
  const representation = computeRepresentation(rows, sensitiveAttributes);
  const groupRates = computeGroupRates(rows, sensitiveAttributes, targetColumn);
  const proxyFeatures = detectProxyFeatures(rows, columns, sensitiveAttributes);
  const classBalanceRatio = computeClassBalance(rows, targetColumn);

  const penalty =
    groupRates.demographicParityDifference * 30 +
    representation.representationImbalance * 25 +
    proxyFeatures.length * 5 +
    (1 - classBalanceRatio) * 20;
  const trustScore = Math.max(0, Math.min(100, Math.round(100 - penalty)));
  const biasRisk = riskFromScore(trustScore);

  const insights = [
    `TrustLens analyzed ${rows.length} rows and ${columns.length} columns directly in the browser.`,
    sensitiveAttributes.length
      ? `Sensitive attributes detected: ${sensitiveAttributes.join(", ")}.`
      : "No common sensitive attributes were detected from the column names.",
    targetColumn
      ? `The target-like column used for parity checks was "${targetColumn}".`
      : "No target-like column was detected, so the score focuses on representation and proxy risk.",
    `The dataset is currently assessed as ${biasRisk} risk with a trust score of ${trustScore}.`
  ].join(" ");

  const recommendations = [
    representation.underrepresented.length
      ? "Add or rebalance underrepresented groups before model training."
      : "Keep monitoring group representation as new rows are added.",
    proxyFeatures.length
      ? `Review possible proxy feature(s): ${proxyFeatures.slice(0, 5).join(", ")}.`
      : "No strong numeric proxy features were detected above the current threshold.",
    classBalanceRatio < 0.7
      ? "Use resampling or class weighting to reduce target imbalance."
      : "Class balance does not show a severe warning from this quick scan."
  ];

  return {
    id: crypto.randomUUID(),
    created_at_utc: new Date().toISOString(),
    dataset_name: file.name,
    bias_risk: biasRisk,
    trust_score: trustScore,
    sensitive_attributes: sensitiveAttributes,
    metrics: {
      demographic_parity_difference: groupRates.demographicParityDifference,
      disparate_impact_ratio: groupRates.disparateImpactRatio,
      statistical_parity: groupRates.statisticalParity,
      representation_imbalance_score: representation.representationImbalance,
      class_balance_ratio: classBalanceRatio,
      proxy_feature_count: proxyFeatures.length
    },
    insights,
    recommendations,
    details: {
      execution_mode: "browser_fallback",
      rows: rows.length,
      columns,
      target_column: targetColumn ?? null,
      underrepresented_groups: representation.underrepresented,
      overrepresented_groups: representation.overrepresented,
      proxy_features: proxyFeatures
    }
  };
}
