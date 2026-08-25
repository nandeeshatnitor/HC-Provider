const COLOR_BY_ROLE = {
  physician: "var(--physician)",
  nurse: "var(--nurse)",
  assistant: "var(--assistant)",
  specialist: "var(--specialist)",
};

const ICON_BY_ROLE = {
  physician: "MD",
  nurse: "RN",
  assistant: "NA",
  specialist: "SP",
};

export function roleColor(roleId) {
  return COLOR_BY_ROLE[roleId] || "var(--accent)";
}

export function roleIcon(roleId, displayName) {
  return ICON_BY_ROLE[roleId] || displayName.slice(0, 2).toUpperCase();
}
