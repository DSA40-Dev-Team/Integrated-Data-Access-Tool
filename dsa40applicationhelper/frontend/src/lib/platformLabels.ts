export function formatPlatformLabel(
  text: string,
  platformNames: string[],
): string {
  if (!text.includes("<PLATFORM_NAME>")) return text;
  const replacement =
    platformNames.length === 1 ? platformNames[0]! : "the platforms";
  return text.replaceAll("<PLATFORM_NAME>", replacement);
}

export function platformNamesForIds(
  platformIds: string[],
  platforms: { id: string; name: string }[],
): string[] {
  return platformIds
    .map((id) => platforms.find((p) => p.id === id)?.name ?? id)
    .filter(Boolean);
}
