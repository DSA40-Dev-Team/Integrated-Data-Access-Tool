<script lang="ts">
  import SchemaFieldInput from "$lib/SchemaFieldInput.svelte";
  import { Badge } from "$lib/components/ui/badge/index.js";
  import { isVisible, type ConditionsMap } from "$lib/conditions";
  import { COMPOSITE_GATE_FIELDS, type FieldSchema, type SchemaField } from "$lib/structured";

  type PlatformRef = { id: string; name: string };

  type Props = {
    id: string;
    config?: Record<string, unknown> | null;
    value?: string;
    validation?: string | string[] | null;
    conditions?: ConditionsMap;
    formValues?: Record<string, string | undefined>;
    platforms?: PlatformRef[];
    requiredFieldIds?: Set<string>;
  };

  let {
    id,
    config = null,
    value = $bindable("{}"),
    validation = null,
    conditions = {},
    formValues = {},
    platforms = [],
    requiredFieldIds = new Set<string>(),
  }: Props = $props();

  let fields = $state<SchemaField[]>([]);
  let item = $state<Record<string, unknown>>({});
  let activePlatformTab = $state<Record<string, string>>({});

  const schemaName = $derived(String(config?.schema ?? ""));

  const validationErrors = $derived(
    Array.isArray(validation) ? validation : validation ? [validation] : [],
  );

  function syncOut() {
    value = JSON.stringify(item);
  }

  function loadFromValue() {
    if (!value?.trim()) {
      item = {};
      return;
    }
    try {
      const parsed = JSON.parse(value);
      item = parsed && typeof parsed === "object" && !Array.isArray(parsed) ? parsed : {};
    } catch {
      item = {};
    }
  }

  function isPlatformField(field: SchemaField): boolean {
    return (
      field.granularity === "platform_specific" &&
      Array.isArray(field.scoped_platforms) &&
      field.scoped_platforms.length > 0
    );
  }

  function showPlatformTabs(field: SchemaField): boolean {
    return isPlatformField(field) && (field.scoped_platforms?.length ?? 0) > 1;
  }

  function shouldShowPlatformPanel(field: SchemaField, platformId: string): boolean {
    if (field.id === "prev-experience-detail") {
      return platformFieldValue("prev-experience", platformId) === "Yes";
    }
    const scopedKey = `${field.id}__${platformId}`;
    if (conditions[scopedKey]?.length) {
      return isVisible(scopedKey, conditions, formValues);
    }
    return true;
  }

  function isGateField(field: SchemaField): boolean {
    return (COMPOSITE_GATE_FIELDS[schemaName] ?? []).includes(field.id);
  }

  function isFieldVisible(field: SchemaField): boolean {
    if (isGateField(field)) {
      return true;
    }
    if (!isPlatformField(field)) {
      return isVisible(field.id, conditions, formValues);
    }
    return (field.scoped_platforms ?? []).some((platformId) =>
      shouldShowPlatformPanel(field, platformId),
    );
  }

  function platformLabel(platformId: string): string {
    return platforms.find((p) => p.id === platformId)?.name ?? platformId;
  }

  function fieldHelp(field: SchemaField, platformId?: string): string | null {
    if (platformId && field.platform_help?.[platformId]) {
      return field.platform_help[platformId] ?? null;
    }
    return field.help ?? null;
  }

  function activeTabFor(field: SchemaField): string {
    const scoped = field.scoped_platforms ?? [];
    return activePlatformTab[field.id] ?? scoped[0] ?? "";
  }

  function setActiveTab(fieldId: string, platformId: string) {
    activePlatformTab = { ...activePlatformTab, [fieldId]: platformId };
  }

  function fieldValue(fieldId: string): string {
    const raw = item[fieldId];
    if (raw && typeof raw === "object" && !Array.isArray(raw)) return "";
    return String(raw ?? "");
  }

  function platformFieldValue(fieldId: string, platformId: string): string {
    const raw = item[fieldId];
    if (raw && typeof raw === "object" && !Array.isArray(raw)) {
      return String((raw as Record<string, unknown>)[platformId] ?? "");
    }
    if (typeof raw === "string") return raw;
    return "";
  }

  function setField(fieldId: string, fieldValue: string) {
    item = { ...item, [fieldId]: fieldValue };
    syncOut();
  }

  function setPlatformField(fieldId: string, platformId: string, fieldValue: string) {
    const raw = item[fieldId];
    const dict: Record<string, string> =
      raw && typeof raw === "object" && !Array.isArray(raw)
        ? Object.fromEntries(
            Object.entries(raw as Record<string, unknown>).map(([k, v]) => [k, String(v ?? "")]),
          )
        : typeof raw === "string" && raw.trim()
          ? { _: raw }
          : {};
    dict[platformId] = fieldValue;
    item = { ...item, [fieldId]: dict };
    syncOut();
  }

  async function loadSchemaFields() {
    loadFromValue();
    if (!schemaName) {
      fields = [];
      return;
    }
    const params = new URLSearchParams();
    for (const platform of platforms) {
      params.append("vlopse", platform.id);
    }
    const query = params.toString();
    const res = await fetch(`/api/schemas/${schemaName}${query ? `?${query}` : ""}`);
    if (!res.ok) {
      fields = [];
      return;
    }
    const schemaData = (await res.json()) as FieldSchema;
    fields = schemaData.fields ?? [];
    for (const field of fields) {
      if (isPlatformField(field) && field.scoped_platforms?.[0]) {
        activePlatformTab[field.id] = field.scoped_platforms[0];
      }
    }
  }

  $effect(() => {
    const platformKey = platforms.map((platform) => platform.id).join(",");
    void platformKey;
    void schemaName;
    void loadSchemaFields();
  });

  $effect(() => {
    if (value && value !== JSON.stringify(item)) {
      loadFromValue();
    }
  });
</script>

<div class="flex flex-col gap-1">
  {#each fields as field (field.id)}
    {#if isFieldVisible(field)}
      <label
        class="mb-1 mt-2 block text-sm {isGateField(field)
          ? 'font-medium text-card-foreground'
          : 'text-[0.8125rem] text-muted-foreground'}"
        for={`${id}-${field.id}`}
      >
        {field.text_en}
        {#if requiredFieldIds.has(field.id)}
          <Badge variant="required" class="ml-1.5">Required</Badge>
        {/if}
      </label>
      {#if isPlatformField(field)}
        {#if showPlatformTabs(field)}
          <div class="mb-2 flex flex-wrap gap-1" role="tablist" aria-label="{field.text_en} platforms">
            {#each field.scoped_platforms ?? [] as platformId (platformId)}
              <button
                type="button"
                role="tab"
                aria-selected={activeTabFor(field) === platformId}
                class:platform-tab-active={activeTabFor(field) === platformId}
                class="platform-tab"
                onclick={() => setActiveTab(field.id, platformId)}
              >
                {platformLabel(platformId)}
              </button>
            {/each}
          </div>
          {#each field.scoped_platforms ?? [] as platformId (platformId)}
            {#if activeTabFor(field) === platformId && shouldShowPlatformPanel(field, platformId)}
              <div role="tabpanel" class="mb-1">
                {#if fieldHelp(field, platformId)}
                  <p class="mb-1 text-xs text-field-hint">{fieldHelp(field, platformId)}</p>
                {/if}
                <SchemaFieldInput
                  id={`${id}-${field.id}-${platformId}`}
                  {field}
                  value={platformFieldValue(field.id, platformId)}
                  onchange={(v) => setPlatformField(field.id, platformId, v)}
                />
              </div>
            {/if}
          {/each}
        {:else}
          {@const platformId = field.scoped_platforms?.[0] ?? ""}
          {#if platformId && shouldShowPlatformPanel(field, platformId)}
            {#if fieldHelp(field, platformId)}
              <p class="mb-1 text-xs text-field-hint">{fieldHelp(field, platformId)}</p>
            {/if}
            <SchemaFieldInput
              id={`${id}-${field.id}-${platformId}`}
              {field}
              value={platformFieldValue(field.id, platformId)}
              onchange={(v) => setPlatformField(field.id, platformId, v)}
            />
          {/if}
        {/if}
      {:else}
        {#if fieldHelp(field)}
          <p class="mb-1 text-xs text-field-hint">{fieldHelp(field)}</p>
        {/if}
        <SchemaFieldInput
          id={`${id}-${field.id}`}
          {field}
          value={fieldValue(field.id)}
          onchange={(v) => setField(field.id, v)}
        />
      {/if}
    {/if}
  {/each}

  {#if validationErrors.length > 0}
    <ul class="mt-2 list-none p-0 text-sm text-destructive" role="alert">
      {#each validationErrors as err}
        <li>{err}</li>
      {/each}
    </ul>
  {/if}
</div>
